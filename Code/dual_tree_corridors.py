"""
dual_tree_corridors.py
======================

Builds TWO separate directed corridor trees on a directed road graph:

  OUTBOUND TREE  — Hospital → Patient
      Follows edge direction outward from each hospital.
      Used when ambulances depart to reach a patient.

  INBOUND TREE   — Patient → Hospital
      Follows edge direction inward toward each hospital.
      Used when ambulances bring a patient back.

Both trees are built with the same tiered logic (backbone → primary →
secondary → tertiary) but on complementary directions of the graph.

Key design principle — TWO separate weights
-------------------------------------------
  REAL distance (metres) via weight="length":
    * Voronoi assignment (which origin owns which node)
    * 500 m primary threshold
    * 300 m secondary threshold

  COST weight = length / (lanes × speed):
    * All Dijkstra pathfinding (prefers wide, fast roads)
    * Reuse discount applied on top (already-used edges × reuse_discount)

Keeping these separate was the critical bug in the previous version:
the cost graph produced values like 12.3 instead of 800 metres, so the
500 m threshold filtered out every node and primary targets = 0.

Outputs (per tree)
------------------
  {prefix}_edges.json   — corridor edges with full edge data + tier
  {prefix}_nodes.json   — corridor nodes with junction data + tier + flags
  {prefix}_leaves.json  — leaf / root endpoint nodes
  corridor_summary.json — combined statistics
"""

import json
import math
import pickle
from collections import defaultdict
from pathlib import Path

import networkx as nx


# =============================================================================
# COST FUNCTION
# =============================================================================

def edge_cost(G, u, v, discount=1.0):
    """
    Routing cost for edge (u→v).  Lower = more preferred by Dijkstra.

        cost = (length / (lanes × speed)) × discount

    A 4-lane 50 km/h road is 8× cheaper than a 1-lane 25 km/h road of
    the same physical length, so Dijkstra naturally prefers wider, faster
    roads.  Falls back gracefully if attributes are missing.
    """
    data   = G[u][v]
    length = max(float(data.get("length", 1.0)), 0.1)
    lanes  = max(float(data.get("lanes",  1.0)), 1.0)
    speed  = max(float(data.get("speed",  1.0)), 1.0)
    return (length / (lanes * speed)) * discount


def assign_cost_weights(G, used_edges=None, reuse_discount=0.3):
    """
    Return a new DiGraph with a 'weight' attribute on every edge equal to
    edge_cost(), with already-used edges multiplied by reuse_discount
    (making them cheaper and therefore preferred by Dijkstra).
    """
    H = nx.DiGraph()
    H.add_nodes_from(G.nodes(data=True))
    for u, v, data in G.edges(data=True):
        disc = reuse_discount if (used_edges and (u, v) in used_edges) else 1.0
        H.add_edge(u, v, weight=edge_cost(G, u, v, discount=disc), **data)
    return H


# =============================================================================
# EDGE COVERAGE
# =============================================================================

def point_to_segment_distance(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    return math.sqrt((px - (x1 + t * dx)) ** 2 + (py - (y1 + t * dy)) ** 2)


def compute_edge_coverage(G, R, cache_path="edge_coverage_directed.pkl"):
    """
    For every directed edge (u,v) compute the set of graph nodes within R
    metres of the edge's line segment.  Result is cached to disk.
    """
    cache = Path(cache_path)
    if cache.exists():
        print(f"  Loading cached edge coverage from {cache_path}...")
        with open(cache, "rb") as f:
            return pickle.load(f)

    print(f"  Computing edge coverage (R={R}m)...")
    nodes_xy = {n: (float(d["x"]), float(d["y"])) for n, d in G.nodes(data=True)}
    edge_coverage = {}

    for u, v in G.edges():
        x1, y1 = nodes_xy[u]
        x2, y2 = nodes_xy[v]
        covered = set()
        for node, (px, py) in nodes_xy.items():
            if point_to_segment_distance(px, py, x1, y1, x2, y2) * 111_000 <= R:
                covered.add(node)
        edge_coverage[(u, v)] = covered
        edge_coverage[(v, u)] = covered   # proximity is symmetric

    with open(cache, "wb") as f:
        pickle.dump(edge_coverage, f)
    print(f"  Cached → {cache_path}")
    return edge_coverage


# =============================================================================
# PATH HELPERS
# =============================================================================

def get_cost_path(G_cost, source, target):
    """Shortest path on a pre-weighted graph (weight='weight')."""
    if source == target:
        return [source], 0.0
    try:
        path = nx.shortest_path(G_cost, source, target, weight="weight")
        cost = nx.shortest_path_length(G_cost, source, target, weight="weight")
        return path, cost
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return None, None


def add_directed_path(path, G, corridor_edges, node_set,
                      all_corridor_nodes, edge_coverage, covered_nodes, used_edges,
                      edge_set=None):
    """
    Add every directed edge along path that actually exists in G.
    Never adds (v,u) just because (u,v) was in the path — direction is
    always respected.
    edge_set: optional set to also track which edges belong to this tier.
    """
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if not G.has_edge(u, v):
            continue
        corridor_edges.add((u, v))
        if edge_set is not None:
            edge_set.add((u, v))
        node_set.add(u)
        node_set.add(v)
        if all_corridor_nodes is not None:
            all_corridor_nodes.add(u)
            all_corridor_nodes.add(v)
        used_edges.add((u, v))
        if (u, v) in edge_coverage:
            covered_nodes |= edge_coverage[(u, v)]


# =============================================================================
# LEAF DETECTION
# =============================================================================

def find_leaves(corridor_edges):
    """
    In the directed subgraph built from corridor_edges:
      leaves — out_degree == 0  (nowhere to go — ambulance endpoint)
      roots  — in_degree  == 0  (nothing leads here — ambulance start)
    """
    sub    = nx.DiGraph()
    sub.add_edges_from(corridor_edges)
    nodes  = set(sub.nodes())
    leaves = {n for n in nodes if sub.out_degree(n) == 0}
    roots  = {n for n in nodes if sub.in_degree(n)  == 0}
    return leaves, roots, sub


# =============================================================================
# SINGLE-TREE BUILDER
# =============================================================================

def build_single_tree(
    G,
    origin_nodes,
    edge_coverage,
    direction,
    initial_used_edges=None,
    coverage_radius=200,
    target_coverage=0.95,
    backbone_reuse_discount=0.3,
    primary_reuse_discount=0.4,
    secondary_reuse_discount=0.4,
):
    """
    Build one directed corridor tree.

    direction = "outbound"  →  Dijkstra on G as-is  (hospital → patient)
    direction = "inbound"   →  Dijkstra on G.reverse() then paths are
                               reversed before adding, so every edge added
                               is a valid G edge flowing toward the hospital.

    The Voronoi assignment (node_to_closest_origin) and ALL distance
    thresholds use real metres on G regardless of direction.  Only
    pathfinding uses the cost graph.
    """

    print(f"\n{'=' * 60}")
    print(f"  Building {direction.upper()} tree")
    print(f"{'=' * 60}")

    G_work = G.reverse(copy=True) if direction == "inbound" else G

    corridor_edges  = set()
    covered_nodes   = set()
    backbone_nodes  = set()
    primary_nodes   = set()
    secondary_nodes = set()
    tertiary_nodes  = set()
    backbone_edges  = set()
    primary_edges   = set()   # track edges (not just nodes) per tier
    secondary_edges = set()
    used_edges      = set(initial_used_edges) if initial_used_edges else set()

    total_nodes = G.number_of_nodes()

    # ------------------------------------------------------------------
    # Pre-step: real metric distances on G for Voronoi + thresholds
    # ------------------------------------------------------------------
    print("\n  [Pre-step] Real metric distances (metres) for Voronoi assignment")
    node_to_closest_origin = {}
    node_real_distances    = {}

    for origin in origin_nodes:
        try:
            dists = nx.single_source_dijkstra_path_length(
                G, origin, weight="length")
        except Exception:
            dists = {}
        for node, dist in dists.items():
            if node not in node_real_distances or dist < node_real_distances[node]:
                node_real_distances[node] = dist
                node_to_closest_origin[node] = origin

    print(f"    Voronoi mapped {len(node_real_distances)} nodes to {len(origin_nodes)} origins")

    # -----------------------------------------------------------------------
    # STEP 1 — BACKBONE
    # -----------------------------------------------------------------------
    print("\n  [Step 1] Backbone")

    def euclidean(a, b):
        dx = G.nodes[a]["x"] - G.nodes[b]["x"]
        dy = G.nodes[a]["y"] - G.nodes[b]["y"]
        return math.sqrt(dx * dx + dy * dy)

    all_pairs = [
        (oa, ob) for oa in origin_nodes for ob in origin_nodes if oa != ob
    ]
    all_pairs.sort(key=lambda p: euclidean(p[0], p[1]))

    origin_work_paths = {}   # paths on G_work (may be reversed vs G)

    for origin_a, origin_b in all_pairs:
        G_cost = assign_cost_weights(G_work, used_edges=used_edges,
                                     reuse_discount=backbone_reuse_discount)
        path, _ = get_cost_path(G_cost, origin_a, origin_b)
        if path is None:
            print(f"    Warning: no {direction} path {origin_a}→{origin_b}")
            continue
        origin_work_paths[(origin_a, origin_b)] = path
        for i in range(len(path) - 1):
            used_edges.add((path[i], path[i + 1]))

    for (oa, ob), work_path in origin_work_paths.items():
        actual = list(reversed(work_path)) if direction == "inbound" else work_path
        for i in range(len(actual) - 1):
            u, v = actual[i], actual[i + 1]
            if not G.has_edge(u, v):
                continue
            corridor_edges.add((u, v))
            backbone_edges.add((u, v))
            backbone_nodes.add(u)
            backbone_nodes.add(v)
            used_edges.add((u, v))
            if (u, v) in edge_coverage:
                covered_nodes |= edge_coverage[(u, v)]

    print(f"    {len(backbone_edges)} backbone edges | "
          f"{len(covered_nodes)}/{total_nodes} covered "
          f"({len(covered_nodes)/total_nodes*100:.1f}%)")

    # -----------------------------------------------------------------------
    # STEP 2 — Precompute cost paths from every origin on G_work
    # -----------------------------------------------------------------------
    print("\n  [Step 2] Precomputing cost paths from all origins")

    G_cost_pri = assign_cost_weights(G_work, used_edges=used_edges,
                                     reuse_discount=primary_reuse_discount)
    all_cost_paths = {}

    for origin in origin_nodes:
        try:
            paths = nx.single_source_dijkstra_path(
                G_cost_pri, origin, weight="weight")
        except Exception:
            paths = {}
        all_cost_paths[origin] = paths
        print(f"    Origin {origin}: {len(paths)} reachable nodes on {direction} graph")

    # -----------------------------------------------------------------------
    # STEP 3 — PRIMARY: 8-direction arteries
    # -----------------------------------------------------------------------
    print("\n  [Step 3] Primary arteries")

    all_corridor_nodes = backbone_nodes.copy()

    for origin_idx, origin in enumerate(origin_nodes):
        nodes_by_sector = defaultdict(list)

        for node, real_dist in node_real_distances.items():
            if node == origin:
                continue
            # Only nodes whose closest origin (real metres) is this one
            if node_to_closest_origin.get(node) != origin:
                continue
            # Must be reachable on the working graph
            if node not in all_cost_paths[origin]:
                continue
            # *** REAL METRES threshold — this was the critical bug fix ***
            if real_dist < 500:
                continue

            dx     = G.nodes[node]["x"] - G.nodes[origin]["x"]
            dy     = G.nodes[node]["y"] - G.nodes[origin]["y"]
            angle  = math.degrees(math.atan2(dy, dx)) % 360
            sector = int((angle + 22.5) / 45) % 8
            nodes_by_sector[sector].append((node, real_dist))

        primary_targets = []
        for sector in range(8):
            s_nodes = sorted(nodes_by_sector[sector],
                             key=lambda x: x[1], reverse=True)
            if s_nodes:
                primary_targets.append(s_nodes[0][0])
                if len(s_nodes) > 5:
                    primary_targets.append(s_nodes[len(s_nodes) // 2][0])

        print(f"    Origin {origin_idx+1}: {len(primary_targets)} primary targets")

        for target in primary_targets:
            work_path = all_cost_paths[origin].get(target)
            if work_path is None:
                continue
            actual = list(reversed(work_path)) if direction == "inbound" else work_path
            add_directed_path(actual, G, corridor_edges, primary_nodes,
                              all_corridor_nodes, edge_coverage, covered_nodes, used_edges,
                              edge_set=primary_edges)

    print(f"    Primary complete: {len(covered_nodes)}/{total_nodes} "
          f"({len(covered_nodes)/total_nodes*100:.1f}%)")

    # -----------------------------------------------------------------------
    # STEP 4 — SECONDARY: greedy branches to 80 %
    # -----------------------------------------------------------------------
    print("\n  [Step 4] Secondary branches")

    all_corridor_nodes = backbone_nodes | primary_nodes
    iteration = 0

    while len(covered_nodes) / total_nodes < 0.80 and iteration < 500:
        iteration += 1

        # *** REAL METRES threshold — second critical bug fix ***
        uncovered = [
            (n, node_real_distances[n], node_to_closest_origin[n])
            for n in node_real_distances
            if n not in covered_nodes and node_real_distances[n] > 300
        ]
        uncovered.sort(key=lambda x: x[1], reverse=True)

        best_path   = None
        best_score  = -1
        best_origin = None

        G_cost_sec = assign_cost_weights(G_work, used_edges=used_edges,
                                         reuse_discount=secondary_reuse_discount)

        for target_node, _, origin in uncovered[:50]:
            try:
                work_path = nx.shortest_path(
                    G_cost_sec, origin, target_node, weight="weight")
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue

            actual = list(reversed(work_path)) if direction == "inbound" else work_path

            connection_point = None
            for node in actual:
                if node in all_corridor_nodes:
                    connection_point = node
            if connection_point is None:
                continue

            path_cov    = set()
            path_length = 0.0
            adding      = False

            for i in range(len(actual) - 1):
                u, v = actual[i], actual[i + 1]
                if u == connection_point:
                    adding = True
                if adding and G.has_edge(u, v):
                    path_cov    |= edge_coverage.get((u, v), set())
                    path_length += float(G[u][v].get("length", 1))

            new_cov = path_cov - covered_nodes
            if not new_cov:
                continue

            score = len(new_cov) / max(path_length, 1)
            if score > best_score:
                best_score  = score
                best_path   = actual
                best_origin = origin

        if best_path is None:
            break

        add_directed_path(best_path, G, corridor_edges, secondary_nodes,
                          all_corridor_nodes, edge_coverage, covered_nodes, used_edges,
                          edge_set=secondary_edges)

        if iteration % 25 == 0:
            print(f"    Iteration {iteration}: {len(covered_nodes)}/{total_nodes} "
                  f"({len(covered_nodes)/total_nodes*100:.1f}%)")

    print(f"    Secondary complete: {len(covered_nodes)}/{total_nodes} "
          f"({len(covered_nodes)/total_nodes*100:.1f}%)")

    # -----------------------------------------------------------------------
    # STEP 5 — TERTIARY: single-edge greedy fill
    # -----------------------------------------------------------------------
    print("\n  [Step 5] Tertiary fill")

    all_corridor_nodes = backbone_nodes | primary_nodes | secondary_nodes
    iteration = 0

    while len(covered_nodes) / total_nodes < target_coverage and iteration < 2000:
        iteration += 1
        best_edge    = None
        best_score   = -1
        best_new_cov = set()

        for corridor_node in list(all_corridor_nodes):
            for neighbor in G_work.successors(corridor_node):
                # Translate G_work successor to a real G edge
                u, v = (neighbor, corridor_node) if direction == "inbound" \
                       else (corridor_node, neighbor)
                if not G.has_edge(u, v):
                    continue
                if (u, v) in corridor_edges:
                    continue
                new_cov = edge_coverage.get((u, v), set()) - covered_nodes
                if not new_cov:
                    continue
                lanes  = max(float(G[u][v].get("lanes",  1)), 1)
                speed  = max(float(G[u][v].get("speed",  1)), 1)
                length = max(float(G[u][v].get("length", 1)), 1)
                score  = (len(new_cov) * lanes * speed) / length
                if score > best_score:
                    best_score   = score
                    best_edge    = (u, v)
                    best_new_cov = new_cov

        if best_edge is None:
            break

        u, v = best_edge
        corridor_edges.add((u, v))
        tertiary_nodes.add(u)
        tertiary_nodes.add(v)
        all_corridor_nodes.add(u)
        all_corridor_nodes.add(v)
        used_edges.add((u, v))
        covered_nodes |= best_new_cov

        if iteration % 100 == 0:
            print(f"    Iteration {iteration}: {len(covered_nodes)}/{total_nodes} "
                  f"({len(covered_nodes)/total_nodes*100:.1f}%)")

    print(f"    Tertiary complete: {len(covered_nodes)}/{total_nodes} "
          f"({len(covered_nodes)/total_nodes*100:.1f}%)")

    # -----------------------------------------------------------------------
    # STEP 6 — Leaf detection
    # -----------------------------------------------------------------------
    leaf_nodes, root_nodes, _ = find_leaves(corridor_edges)

    print(f"\n  Tree summary:")
    print(f"    Corridor edges   : {len(corridor_edges)}")
    print(f"    Backbone nodes   : {len(backbone_nodes)}")
    print(f"    Primary nodes    : {len(primary_nodes)}")
    print(f"    Secondary nodes  : {len(secondary_nodes)}")
    print(f"    Tertiary nodes   : {len(tertiary_nodes)}")
    print(f"    Leaf nodes       : {len(leaf_nodes)}")
    print(f"    Root nodes       : {len(root_nodes)}")
    print(f"    Final coverage   : {len(covered_nodes)/total_nodes*100:.1f}%")

    tier_info = {
        "backbone"        : backbone_nodes,
        "primary"         : primary_nodes,
        "secondary"       : secondary_nodes,
        "tertiary"        : tertiary_nodes,
        "backbone_edges"  : backbone_edges,
        "primary_edges"   : primary_edges,
        "secondary_edges" : secondary_edges,
    }

    return (corridor_edges, covered_nodes, tier_info, backbone_edges,
            leaf_nodes, root_nodes, used_edges)


# =============================================================================
# JSON OUTPUT
# =============================================================================

def _node_record(G, node):
    d = dict(G.nodes[node])
    d["id"] = node
    return d


def _edge_record(G, u, v):
    d = dict(G[u][v])
    d["from"] = u
    d["to"]   = v
    return d


def save_tree_outputs(G, corridor_edges, tier_info, backbone_edges,
                      leaf_nodes, root_nodes, covered_nodes,
                      origin_nodes, direction, prefix=None, output_dir=None):
    """
    Write three JSON files for one tree into output_dir (default: cwd).
    Uses edge sets from tier_info for accurate tier classification.
    """
    prefix = prefix or direction

    out_dir = Path(output_dir) if output_dir else Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    backbone_set  = set(backbone_edges)
    pri_edges     = tier_info.get("primary_edges",   set())
    sec_edges     = tier_info.get("secondary_edges", set())

    edges_out = []
    for (u, v) in corridor_edges:
        if not G.has_edge(u, v):
            continue
        rec = _edge_record(G, u, v)
        if (u, v) in backbone_set:
            rec["tier"] = "backbone"
        elif (u, v) in pri_edges:
            rec["tier"] = "primary"
        elif (u, v) in sec_edges:
            rec["tier"] = "secondary"
        else:
            rec["tier"] = "tertiary"
        edges_out.append(rec)

    ef = out_dir / f"{prefix}_edges.json"
    with open(ef, "w", encoding="utf-8") as f:
        json.dump(edges_out, f, indent=2, default=str)
    print(f"  {len(edges_out)} edges → {ef}")

    corridor_nodes = {u for (u, v) in corridor_edges} | {v for (u, v) in corridor_edges}

    def node_tier(n):
        for tier in ("backbone", "primary", "secondary", "tertiary"):
            if n in tier_info[tier]:
                return tier
        return "unknown"

    nodes_out = []
    for node in corridor_nodes:
        if not G.has_node(node):
            continue
        rec              = _node_record(G, node)
        rec["tier"]      = node_tier(node)
        rec["is_origin"] = node in origin_nodes
        rec["is_leaf"]   = node in leaf_nodes
        rec["is_root"]   = node in root_nodes
        rec["covered"]   = node in covered_nodes
        nodes_out.append(rec)

    nf = out_dir / f"{prefix}_nodes.json"
    with open(nf, "w", encoding="utf-8") as f:
        json.dump(nodes_out, f, indent=2, default=str)
    print(f"  {len(nodes_out)} nodes → {nf}")

    leaves_out = {
        "direction"        : direction,
        "description": {
            "dead_end_leaves" : "Nodes with out_degree=0 (ambulance endpoint / hospital for inbound)",
            "entry_root_nodes": "Nodes with in_degree=0 (route start — patient pickup for inbound)",
        },
        "dead_end_leaves"  : [_node_record(G, n) for n in leaf_nodes  if G.has_node(n)],
        "entry_root_nodes" : [_node_record(G, n) for n in root_nodes  if G.has_node(n)],
        "origin_nodes"     : [_node_record(G, n) for n in origin_nodes if G.has_node(n)],
    }

    lf = out_dir / f"{prefix}_leaves.json"
    with open(lf, "w", encoding="utf-8") as f:
        json.dump(leaves_out, f, indent=2, default=str)
    print(f"  {len(leaf_nodes)} leaves + {len(root_nodes)} roots → {lf}")

    return str(ef), str(nf), str(lf)


# =============================================================================
# VISUALISATION
# =============================================================================

def plot_dual_trees(G, outbound_edges, inbound_edges,
                    outbound_tier, inbound_tier,
                    outbound_backbone, inbound_backbone,
                    outbound_leaves, inbound_leaves,
                    outbound_roots, inbound_roots,
                    origin_nodes,
                    out_covered=None,
                    in_covered=None,
                    zoom_start=13,
                    output_file="dual_tree_corridors.html"):
    """
    Renders both trees as SEPARATE TOGGLEABLE LAYERS using Folium's
    LayerControl.  Open the HTML and use the layer panel (top-right) to
    show/hide each layer independently.

    Tier coloring uses edge sets (not node sets) so every edge is
    correctly classified regardless of which tier its endpoint nodes
    belong to.

    Inbound "leaf nodes" layer shows the ROOTS (in_degree==0) which are
    the actual patient pick-up entry points, not the hospitals.

    Layers
    ------
    Base streets              — light gray background
    Outbound — Backbone       — dark red,   thick
    Outbound — Primary        — red,        medium
    Outbound — Secondary      — orange-red, thin
    Outbound — Tertiary       — orange,     thin
    Outbound — Endpoints      — red circles (where ambulance reaches patient)
    Inbound  — Backbone       — dark blue,  thick
    Inbound  — Primary        — blue,       medium
    Inbound  — Secondary      — steel blue, thin
    Inbound  — Tertiary       — light blue, thin
    Inbound  — Entry points   — blue circles (where patient enters return route)
    Hospitals                 — purple markers
    Uncovered nodes           — small red dots (hidden by default)
    """
    import folium
    from folium import FeatureGroup, LayerControl

    center = (G.nodes[origin_nodes[0]]["y"], G.nodes[origin_nodes[0]]["x"])
    m      = folium.Map(location=center, zoom_start=zoom_start,
                        tiles="CartoDB positron")

    # --- Pull edge sets out of tier_info for accurate classification ---
    out_bb_edges  = set(outbound_backbone)
    out_pri_edges = outbound_tier.get("primary_edges",   set())
    out_sec_edges = outbound_tier.get("secondary_edges", set())
    out_all       = set(outbound_edges)

    in_bb_edges   = set(inbound_backbone)
    in_pri_edges  = inbound_tier.get("primary_edges",   set())
    in_sec_edges  = inbound_tier.get("secondary_edges", set())
    in_all        = set(inbound_edges)

    def line(fg, u, v, color, weight, opacity=0.9):
        ll = [(G.nodes[u]["y"], G.nodes[u]["x"]),
              (G.nodes[v]["y"], G.nodes[v]["x"])]
        folium.PolyLine(ll, color=color, weight=weight,
                        opacity=opacity).add_to(fg)

    # ------------------------------------------------------------------
    # Base streets
    # ------------------------------------------------------------------
    fg_base = FeatureGroup(name="Base streets", show=True)
    for u, v in G.edges():
        if (u, v) not in out_all and (u, v) not in in_all:
            line(fg_base, u, v, "#cccccc", 0.6, opacity=0.18)
    fg_base.add_to(m)

    # ------------------------------------------------------------------
    # Outbound layers  (warm — red family)
    # ------------------------------------------------------------------
    fg_out_bb  = FeatureGroup(name="Outbound — Backbone",   show=True)
    fg_out_pri = FeatureGroup(name="Outbound — Primary",    show=True)
    fg_out_sec = FeatureGroup(name="Outbound — Secondary",  show=True)
    fg_out_ter = FeatureGroup(name="Outbound — Tertiary",   show=True)
    fg_out_ep  = FeatureGroup(name="Outbound — Endpoints",  show=True)

    for u, v in out_all:
        if not G.has_node(u) or not G.has_node(v):
            continue
        if (u, v) in out_bb_edges:
            line(fg_out_bb,  u, v, "#8B0000", 7, opacity=1.0)
        elif (u, v) in out_pri_edges:
            line(fg_out_pri, u, v, "#e60000", 5)
        elif (u, v) in out_sec_edges:
            line(fg_out_sec, u, v, "#ff4500", 3)
        else:
            line(fg_out_ter, u, v, "#ff9900", 2)

    # Outbound leaves = nodes with out_degree 0 = where ambulance arrives
    for node in outbound_leaves:
        if not G.has_node(node):
            continue
        folium.CircleMarker(
            location=(G.nodes[node]["y"], G.nodes[node]["x"]),
            radius=6, color="#8B0000", fill=True,
            fill_color="#e60000", fill_opacity=0.9,
            tooltip=f"Outbound endpoint (patient location): {node}",
        ).add_to(fg_out_ep)

    for fg in (fg_out_bb, fg_out_pri, fg_out_sec, fg_out_ter, fg_out_ep):
        fg.add_to(m)

    # ------------------------------------------------------------------
    # Inbound layers  (cool — blue family)
    # ------------------------------------------------------------------
    fg_in_bb  = FeatureGroup(name="Inbound — Backbone",     show=True)
    fg_in_pri = FeatureGroup(name="Inbound — Primary",      show=True)
    fg_in_sec = FeatureGroup(name="Inbound — Secondary",    show=True)
    fg_in_ter = FeatureGroup(name="Inbound — Tertiary",     show=True)
    fg_in_ep  = FeatureGroup(name="Inbound — Entry points", show=True)

    for u, v in in_all:
        if not G.has_node(u) or not G.has_node(v):
            continue
        if (u, v) in in_bb_edges:
            line(fg_in_bb,  u, v, "#00008B", 7, opacity=1.0)
        elif (u, v) in in_pri_edges:
            line(fg_in_pri, u, v, "#1a6ef5", 5)
        elif (u, v) in in_sec_edges:
            line(fg_in_sec, u, v, "#4682b4", 3)
        else:
            line(fg_in_ter, u, v, "#87ceeb", 2)

    # Inbound ROOTS = nodes with in_degree 0 = patient pick-up entry points
    # (inbound leaves = hospitals, which are already shown as purple markers)
    for node in inbound_roots:
        if not G.has_node(node):
            continue
        folium.CircleMarker(
            location=(G.nodes[node]["y"], G.nodes[node]["x"]),
            radius=6, color="#00008B", fill=True,
            fill_color="#1a6ef5", fill_opacity=0.9,
            tooltip=f"Inbound entry point (patient pick-up): {node}",
        ).add_to(fg_in_ep)

    for fg in (fg_in_bb, fg_in_pri, fg_in_sec, fg_in_ter, fg_in_ep):
        fg.add_to(m)

    # ------------------------------------------------------------------
    # Uncovered nodes (hidden by default)
    # ------------------------------------------------------------------
    if out_covered is not None and in_covered is not None:
        all_nodes = set(G.nodes())
        uncovered = all_nodes - (out_covered | in_covered)
        fg_unc = FeatureGroup(name="Uncovered nodes", show=False)
        for node in uncovered:
            folium.CircleMarker(
                location=(G.nodes[node]["y"], G.nodes[node]["x"]),
                radius=3, color="#cc0000", fill=True,
                fill_color="#cc0000", fill_opacity=0.6, weight=0,
                tooltip=f"Not covered: {node}",
            ).add_to(fg_unc)
        fg_unc.add_to(m)

    # ------------------------------------------------------------------
    # Hospitals
    # ------------------------------------------------------------------
    fg_hosp = FeatureGroup(name="Hospitals", show=True)
    for idx, origin in enumerate(origin_nodes):
        loc = (G.nodes[origin]["y"], G.nodes[origin]["x"])
        folium.CircleMarker(
            location=loc, radius=12,
            color="purple", fill=True,
            fill_color="purple", fill_opacity=1.0,
            tooltip=f"Hospital {idx + 1}: node {origin}",
        ).add_to(fg_hosp)
        folium.Marker(
            location=loc,
            icon=folium.DivIcon(
                html=(f'<div style="font-size:11pt;color:purple;'
                      f'font-weight:bold;white-space:nowrap;">H{idx+1}</div>')
            ),
        ).add_to(fg_hosp)
    fg_hosp.add_to(m)

    # ------------------------------------------------------------------
    # Layer control
    # ------------------------------------------------------------------
    LayerControl(collapsed=False, position="topright").add_to(m)

    m.save(output_file)
    print(f"  Map → {output_file}")
    return m


# =============================================================================
# MAIN PIPELINE
# =============================================================================

def build_dual_tree_corridors(
    G,
    origin_nodes,
    coverage_radius=200,
    target_coverage=0.95,
    backbone_reuse_discount=0.3,
    primary_reuse_discount=0.4,
    secondary_reuse_discount=0.4,
    output_prefix_outbound="outbound",
    output_prefix_inbound="inbound",
    output_dir="result_emergency_routes",
    map_output_file="dual_tree_corridors.html",
):
    """
    Full pipeline. All output files are written into output_dir.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    total_nodes = G.number_of_nodes()
    print(f"\nGraph: {total_nodes} nodes, {G.number_of_edges()} edges")
    print(f"Origins: {len(origin_nodes)}")
    print(f"Output folder: {out_path.resolve()}")

    edge_coverage = compute_edge_coverage(G, coverage_radius)

    # ---- Outbound tree ----
    (out_edges, out_covered, out_tier, out_backbone,
     out_leaves, out_roots, out_used) = build_single_tree(
        G, origin_nodes, edge_coverage,
        direction="outbound",
        coverage_radius=coverage_radius,
        target_coverage=target_coverage,
        backbone_reuse_discount=backbone_reuse_discount,
        primary_reuse_discount=primary_reuse_discount,
        secondary_reuse_discount=secondary_reuse_discount,
    )

    # ---- Inbound tree — seeded with outbound used_edges for cross-reuse ----
    (in_edges, in_covered, in_tier, in_backbone,
     in_leaves, in_roots, in_used) = build_single_tree(
        G, origin_nodes, edge_coverage,
        direction="inbound",
        initial_used_edges=out_used,
        coverage_radius=coverage_radius,
        target_coverage=target_coverage,
        backbone_reuse_discount=backbone_reuse_discount,
        primary_reuse_discount=primary_reuse_discount,
        secondary_reuse_discount=secondary_reuse_discount,
    )

    fully_covered = out_covered & in_covered
    print(f"\nCombined fully-covered: {len(fully_covered)}/{total_nodes} "
          f"({len(fully_covered)/total_nodes*100:.1f}%)")

    print(f"\n{'=' * 60}")
    print(f"Saving outputs to {output_dir}/...")

    out_ef, out_nf, out_lf = save_tree_outputs(
        G, out_edges, out_tier, out_backbone, out_leaves, out_roots,
        out_covered, origin_nodes, "outbound",
        prefix=output_prefix_outbound, output_dir=output_dir,
    )
    in_ef, in_nf, in_lf = save_tree_outputs(
        G, in_edges, in_tier, in_backbone, in_leaves, in_roots,
        in_covered, origin_nodes, "inbound",
        prefix=output_prefix_inbound, output_dir=output_dir,
    )

    summary = {
        "graph"            : {"total_nodes": total_nodes, "total_edges": G.number_of_edges()},
        "origins"          : origin_nodes,
        "coverage_radius_m": coverage_radius,
        "target_coverage"  : target_coverage,
        "outbound": {
            "description"    : "Hospital → Patient (ambulance departs)",
            "corridor_edges" : len(out_edges),
            "coverage_pct"   : round(len(out_covered) / total_nodes * 100, 2),
            "leaf_nodes"     : len(out_leaves),
            "root_nodes"     : len(out_roots),
            "files"          : {"edges": out_ef, "nodes": out_nf, "leaves": out_lf},
        },
        "inbound": {
            "description"    : "Patient → Hospital (ambulance returns)",
            "corridor_edges" : len(in_edges),
            "coverage_pct"   : round(len(in_covered) / total_nodes * 100, 2),
            "leaf_nodes"     : len(in_leaves),
            "root_nodes"     : len(in_roots),
            "files"          : {"edges": in_ef, "nodes": in_nf, "leaves": in_lf},
        },
        "combined": {
            "fully_covered_nodes": len(fully_covered),
            "fully_covered_pct"  : round(len(fully_covered) / total_nodes * 100, 2),
            "note": "nodes reachable FROM a hospital AND that can reach a hospital",
        },
    }

    sf = out_path / "corridor_summary.json"
    with open(sf, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"  Summary → {sf}")

    map_path = out_path / map_output_file
    print("\nGenerating map...")
    plot_dual_trees(
        G, out_edges, in_edges, out_tier, in_tier,
        out_backbone, in_backbone,
        out_leaves, in_leaves,
        out_roots, in_roots,
        origin_nodes,
        out_covered=out_covered,
        in_covered=in_covered,
        output_file=str(map_path),
    )

    print(f"\nAll files saved to: {out_path.resolve()}/")
    print(f"  {output_prefix_outbound}_edges.json")
    print(f"  {output_prefix_outbound}_nodes.json")
    print(f"  {output_prefix_outbound}_leaves.json")
    print(f"  {output_prefix_inbound}_edges.json")
    print(f"  {output_prefix_inbound}_nodes.json")
    print(f"  {output_prefix_inbound}_leaves.json")
    print(f"  corridor_summary.json")
    print(f"  {map_output_file}")

    return {
        "outbound_edges"   : out_edges,
        "outbound_covered" : out_covered,
        "outbound_tier"    : out_tier,
        "outbound_backbone": out_backbone,
        "outbound_leaves"  : out_leaves,
        "outbound_roots"   : out_roots,
        "inbound_edges"    : in_edges,
        "inbound_covered"  : in_covered,
        "inbound_tier"     : in_tier,
        "inbound_backbone" : in_backbone,
        "inbound_leaves"   : in_leaves,
        "inbound_roots"    : in_roots,
        "fully_covered"    : fully_covered,
        "output_dir"       : str(out_path.resolve()),
    }