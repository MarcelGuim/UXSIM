import math
import networkx as nx
from collections import defaultdict
import json
import pickle


# =============================================================================
# EDGE COVERAGE UTILITIES
# =============================================================================

def point_to_segment_distance(px, py, x1, y1, x2, y2):
    """Calculate minimum distance from point to line segment."""
    dx = x2 - x1
    dy = y2 - y1

    if dx == 0 and dy == 0:
        return math.sqrt((px - x1) ** 2 + (py - y1) ** 2)

    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))

    closest_x = x1 + t * dx
    closest_y = y1 + t * dy

    return math.sqrt((px - closest_x) ** 2 + (py - closest_y) ** 2)


def compute_edge_coverage(G, R):
    """
    Computes which nodes are covered by each edge.
    A node is covered if it's within R meters of the edge.
    """
    edge_coverage = {}

    for u, v, data in G.edges(data=True):
        covered_nodes = set()

        x1, y1 = G.nodes[u]["x"], G.nodes[u]["y"]
        x2, y2 = G.nodes[v]["x"], G.nodes[v]["y"]

        for node, node_data in G.nodes(data=True):
            px, py = node_data["x"], node_data["y"]

            dist = point_to_segment_distance(px, py, x1, y1, x2, y2)
            dist_meters = dist * 111000

            if dist_meters <= R:
                covered_nodes.add(node)

        edge_coverage[(u, v)] = covered_nodes
        edge_coverage[(v, u)] = covered_nodes

    with open("edge_coverage_directed.pkl", "wb") as f:
        pickle.dump(edge_coverage, f)

    return edge_coverage


# =============================================================================
# PATH UTILITIES
# =============================================================================

def get_reuse_weighted_path(G, source, target, used_edges, reuse_discount=0.3):
    """
    Find shortest path but discount the weight of already-used edges to
    encourage reuse/sharing of corridor segments.

    Args:
        G:              NetworkX graph
        source:         Source node
        target:         Target node
        used_edges:     Set of (u, v) tuples that are already in the corridor
        reuse_discount: Weight multiplier for already-used edges.
                        0.3 means a used edge appears 70% cheaper, so
                        Dijkstra prefers routing through it.

    Returns:
        (path, length) or (None, None) if no path exists
    """
    G_temp = G.copy()
    for (u, v) in used_edges:
        if G_temp.has_edge(u, v):
            G_temp[u][v]["length"] = G_temp[u][v]["length"] * reuse_discount
        if G_temp.has_edge(v, u):
            G_temp[v][u]["length"] = G_temp[v][u]["length"] * reuse_discount

    try:
        path = nx.shortest_path(G_temp, source, target, weight="length")
        length = nx.shortest_path_length(G_temp, source, target, weight="length")
        return path, length
    except nx.NetworkXNoPath:
        return None, None


def add_path_with_return(
    path,
    G,
    corridor_edges,
    node_set,
    all_corridor_nodes,
    edge_coverage,
    covered_nodes,
    origin,
    used_edges,
    reuse_discount=0.4,
    skip_edges=None,
):
    """
    Adds a forward path to the corridor network and then computes + adds an
    optimised return path back to the origin.  The return path uses
    get_reuse_weighted_path so it prefers already-added corridor edges,
    keeping the network compact.

    Args:
        path:               List of nodes (forward direction, ending at target)
        G:                  NetworkX graph
        corridor_edges:     Master set of corridor edges (mutated in-place)
        node_set:           Tier-specific node set (primary/secondary/tertiary)
        all_corridor_nodes: Combined set of all corridor nodes (mutated)
        edge_coverage:      Dict mapping (u,v) -> set of covered nodes
        covered_nodes:      Master set of covered nodes (mutated)
        origin:             The origin node to return to
        used_edges:         Set tracking already-used edges for reuse weighting
        reuse_discount:     Weight multiplier for reuse (lower = more reuse)
        skip_edges:         Edges to skip when adding (e.g. already in backbone)
    """
    skip_edges = skip_edges or set()

    # ---- Forward path ----
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if (u, v) in skip_edges and (v, u) in skip_edges:
            continue
        corridor_edges.add((u, v))
        corridor_edges.add((v, u))
        node_set.add(u)
        node_set.add(v)
        if all_corridor_nodes is not None:
            all_corridor_nodes.add(u)
            all_corridor_nodes.add(v)
        used_edges.add((u, v))
        used_edges.add((v, u))
        if (u, v) in edge_coverage:
            covered_nodes |= edge_coverage[(u, v)]

    # ---- Return path: from end of forward path back to origin ----
    target = path[-1]
    if target == origin:
        return  # Already at origin — no return needed

    return_path, _ = get_reuse_weighted_path(
        G,
        target,
        origin,
        used_edges,
        reuse_discount=reuse_discount,
    )

    if return_path is None:
        # Fallback: simply reverse the forward path
        return_path = list(reversed(path))

    for i in range(len(return_path) - 1):
        u, v = return_path[i], return_path[i + 1]
        corridor_edges.add((u, v))
        corridor_edges.add((v, u))
        node_set.add(u)
        node_set.add(v)
        if all_corridor_nodes is not None:
            all_corridor_nodes.add(u)
            all_corridor_nodes.add(v)
        used_edges.add((u, v))
        used_edges.add((v, u))
        if (u, v) in edge_coverage:
            covered_nodes |= edge_coverage[(u, v)]


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def build_multi_origin_emergency_corridors(
    G,
    origin_nodes,
    coverage_radius=200,
    target_coverage=0.95,
    backbone_weight=2.0,
    backbone_reuse_discount=0.3,
    primary_reuse_discount=0.4,
    secondary_reuse_discount=0.4,
):
    """
    Builds emergency corridors from multiple origins (hospitals/stations) with:

    1. BACKBONE : Connects all origins together.  Paths are computed in
                  order of increasing straight-line distance so nearby
                  origins share segments first.  A reuse discount makes
                  Dijkstra prefer already-added edges, consolidating routes.
                  Both the forward (A→B) and return (B→A) paths are added
                  explicitly so the directed graph supports travel in both
                  directions.

    2. PRIMARY  : Main arteries from each origin (8 directions × 2 targets).
                  Each artery also gets an optimised return path.

    3. SECONDARY: Branches that fill coverage up to 80 %.
                  Each branch gets a return path back to its origin.

    4. TERTIARY : Single-edge greedy fill to reach target_coverage.
                  (No explicit return paths needed — the network is dense
                  enough by this stage.)

    Args:
        G                    : NetworkX graph (directed or undirected)
        origin_nodes         : List of origin node IDs
        coverage_radius      : Coverage radius in metres
        target_coverage      : Target coverage ratio (0–1)
        backbone_weight      : (legacy, kept for API compatibility)
        backbone_reuse_discount : Weight multiplier for reused backbone edges
        primary_reuse_discount  : Weight multiplier for reused primary edges
        secondary_reuse_discount: Weight multiplier for reused secondary edges

    Returns:
        corridor_edges : Set of (u, v) edge tuples in the corridor network
        covered_nodes  : Set of nodes within coverage_radius of any corridor edge
        tier_info      : Dict mapping tier name → set of nodes
        backbone_edges : Set of (u, v) edge tuples in the backbone sub-network
    """

    corridor_edges = set()
    covered_nodes = set()
    backbone_nodes = set()
    primary_nodes = set()
    secondary_nodes = set()
    tertiary_nodes = set()
    backbone_edges = set()

    # Shared tracking of edges that have already been added — used by
    # get_reuse_weighted_path to discount their cost.
    used_edges = set()

    total_nodes = G.number_of_nodes()

    print(f"\n{'=' * 60}")
    print(f"Building multi-origin emergency corridors")
    print(f"Origins   : {len(origin_nodes)}")
    print(f"Total nodes: {total_nodes}")
    print(f"{'=' * 60}\n")

    # ------------------------------------------------------------------
    # Load or compute edge coverage
    # ------------------------------------------------------------------
    print(f"Computing edge coverage (R={coverage_radius}m)...")
    edge_coverage = None
    try:
        with open("edge_coverage_directed.pkl", "rb") as f:
            edge_coverage = pickle.load(f)
        print("  Loaded cached edge coverage.")
    except FileNotFoundError:
        edge_coverage = compute_edge_coverage(G, coverage_radius)

    # ==========================================================================
    # STEP 1 – BACKBONE: connect all origins, reusing edges where possible
    # ==========================================================================
    print("\n=== STEP 1: Building backbone network ===")

    def euclidean(a, b):
        dx = G.nodes[a]["x"] - G.nodes[b]["x"]
        dy = G.nodes[a]["y"] - G.nodes[b]["y"]
        return math.sqrt(dx * dx + dy * dy)

    # All ordered pairs (a→b AND b→a), sorted by straight-line distance so
    # shorter connections are established first and become shared trunks.
    all_pairs = [
        (oa, ob)
        for i, oa in enumerate(origin_nodes)
        for j, ob in enumerate(origin_nodes)
        if oa != ob
    ]
    all_pairs.sort(key=lambda pair: euclidean(pair[0], pair[1]))

    origin_paths = {}

    for origin_a, origin_b in all_pairs:
        path, length = get_reuse_weighted_path(
            G,
            origin_a,
            origin_b,
            used_edges,
            reuse_discount=backbone_reuse_discount,
        )
        if path is None:
            print(f"  Warning: No path between {origin_a} and {origin_b}")
            continue

        origin_paths[(origin_a, origin_b)] = path

        # Register edges immediately so the next pair can reuse them
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            used_edges.add((u, v))
            used_edges.add((v, u))

    # Add all computed backbone paths (forward + reverse already included via
    # all_pairs containing both directions) to the corridor.
    for (origin_a, origin_b), path in origin_paths.items():
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            corridor_edges.add((u, v))
            corridor_edges.add((v, u))
            backbone_edges.add((u, v))
            backbone_edges.add((v, u))
            backbone_nodes.add(u)
            backbone_nodes.add(v)

            if (u, v) in edge_coverage:
                covered_nodes |= edge_coverage[(u, v)]

    print(f"  Backbone: {len(backbone_edges) // 2} unique edges, "
          f"{len(origin_paths)} directed paths")
    print(f"  Initial coverage: {len(covered_nodes)}/{total_nodes} nodes "
          f"({len(covered_nodes) / total_nodes * 100:.1f}%)")

    # ==========================================================================
    # STEP 2 – Precompute shortest paths from every origin
    # ==========================================================================
    print("\n=== STEP 2: Computing shortest paths from all origins ===")

    node_to_closest_origin = {}
    node_distances = {}
    all_shortest_paths = {}

    for origin in origin_nodes:
        paths = nx.single_source_dijkstra_path(G, origin, weight="length")
        distances = nx.single_source_dijkstra_path_length(G, origin, weight="length")
        all_shortest_paths[origin] = paths

        for node, dist in distances.items():
            if node not in node_distances or dist < node_distances[node]:
                node_distances[node] = dist
                node_to_closest_origin[node] = origin

    # ==========================================================================
    # STEP 3 – PRIMARY corridors: 8-direction arteries from each origin
    # ==========================================================================
    print("\n=== STEP 3: Building primary arteries from each origin ===")

    all_corridor_nodes = backbone_nodes.copy()

    for origin_idx, origin in enumerate(origin_nodes):
        print(f"\n  Origin {origin_idx + 1}/{len(origin_nodes)}: node {origin}")

        nodes_by_sector = {i: [] for i in range(8)}
        origin_dists = nx.single_source_dijkstra_path_length(G, origin, weight="length")

        for node, dist in origin_dists.items():
            if node == origin:
                continue
            if node_to_closest_origin.get(node) != origin:
                continue
            if dist < 500:
                continue

            dx = G.nodes[node]["x"] - G.nodes[origin]["x"]
            dy = G.nodes[node]["y"] - G.nodes[origin]["y"]
            angle = math.degrees(math.atan2(dy, dx))
            if angle < 0:
                angle += 360
            sector = int((angle + 22.5) / 45) % 8
            nodes_by_sector[sector].append((node, dist))

        primary_targets = []
        for sector in range(8):
            sector_nodes = sorted(nodes_by_sector[sector], key=lambda x: x[1], reverse=True)
            if sector_nodes:
                primary_targets.append(sector_nodes[0][0])
                if len(sector_nodes) > 5:
                    primary_targets.append(sector_nodes[len(sector_nodes) // 2][0])

        print(f"  Selected {len(primary_targets)} primary targets")

        for target in primary_targets:
            if target not in all_shortest_paths[origin]:
                continue
            path = all_shortest_paths[origin][target]
            add_path_with_return(
                path=path,
                G=G,
                corridor_edges=corridor_edges,
                node_set=primary_nodes,
                all_corridor_nodes=all_corridor_nodes,
                edge_coverage=edge_coverage,
                covered_nodes=covered_nodes,
                origin=origin,
                used_edges=used_edges,
                reuse_discount=primary_reuse_discount,
                skip_edges=backbone_edges,
            )

    print(f"\n  Primary corridors complete: {len(covered_nodes)}/{total_nodes} nodes "
          f"({len(covered_nodes) / total_nodes * 100:.1f}%)")

    # ==========================================================================
    # STEP 4 – SECONDARY corridors: greedy branches to reach 80 % coverage
    # ==========================================================================
    print("\n=== STEP 4: Building secondary branches ===")

    iteration = 0
    max_iterations = 500

    all_corridor_nodes = backbone_nodes | primary_nodes

    while len(covered_nodes) / total_nodes < 0.80 and iteration < max_iterations:
        iteration += 1

        best_path = None
        best_score = -1
        best_new_coverage = set()
        best_origin = None

        # Candidates: uncovered nodes that are far from their nearest origin
        uncovered_distant = [
            (n, node_distances[n], node_to_closest_origin[n])
            for n in node_distances
            if n not in covered_nodes and node_distances[n] > 300
        ]
        uncovered_distant.sort(key=lambda x: x[1], reverse=True)

        for target_node, _, origin in uncovered_distant[:50]:
            if target_node not in all_shortest_paths.get(origin, {}):
                continue

            path = all_shortest_paths[origin][target_node]

            # Find the deepest point on the path that already exists in the
            # corridor — we only add from there onward.
            connection_point = None
            for node in path:
                if node in all_corridor_nodes:
                    connection_point = node

            if connection_point is None:
                continue

            path_coverage = set()
            path_length = 0
            start_adding = False

            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                if u == connection_point:
                    start_adding = True
                if start_adding:
                    if (u, v) in edge_coverage:
                        path_coverage |= edge_coverage[(u, v)]
                    path_length += G[u][v].get("length", 1)

            new_coverage = path_coverage - covered_nodes
            if not new_coverage:
                continue

            score = len(new_coverage) / max(path_length, 1)
            if score > best_score:
                best_score = score
                best_path = path
                best_new_coverage = new_coverage
                best_origin = origin

        if best_path is None:
            break

        add_path_with_return(
            path=best_path,
            G=G,
            corridor_edges=corridor_edges,
            node_set=secondary_nodes,
            all_corridor_nodes=all_corridor_nodes,
            edge_coverage=edge_coverage,
            covered_nodes=covered_nodes,
            origin=best_origin,
            used_edges=used_edges,
            reuse_discount=secondary_reuse_discount,
        )

        if iteration % 25 == 0:
            print(f"  Secondary iteration {iteration}: {len(covered_nodes)}/{total_nodes} "
                  f"({len(covered_nodes) / total_nodes * 100:.1f}%)")

    print(f"  Secondary corridors complete: {len(covered_nodes)}/{total_nodes} nodes "
          f"({len(covered_nodes) / total_nodes * 100:.1f}%)")

    # ==========================================================================
    # STEP 5 – TERTIARY corridors: single-edge greedy fill to target coverage
    # ==========================================================================
    print("\n=== STEP 5: Adding tertiary streets for full coverage ===")

    iteration = 0
    max_iterations = 1000

    all_corridor_nodes = backbone_nodes | primary_nodes | secondary_nodes

    while len(covered_nodes) / total_nodes < target_coverage and iteration < max_iterations:
        iteration += 1

        best_edge = None
        best_score = -1
        best_new_coverage = set()

        for corridor_node in list(all_corridor_nodes):
            for neighbor in G.neighbors(corridor_node):
                if neighbor not in node_distances:
                    continue

                # Only expand outward from the nearest origin
                closest_origin = node_to_closest_origin.get(corridor_node)
                if closest_origin and neighbor in node_distances:
                    if node_distances[neighbor] < node_distances.get(corridor_node, float("inf")) - 10:
                        continue

                edge = (corridor_node, neighbor)
                if edge in corridor_edges or (neighbor, corridor_node) in corridor_edges:
                    continue

                new_coverage = edge_coverage.get(edge, set()) - covered_nodes
                if not new_coverage:
                    continue

                edge_length = G[corridor_node][neighbor].get("length", 1)
                score = len(new_coverage) / max(edge_length, 1)

                if score > best_score:
                    best_score = score
                    best_edge = edge
                    best_new_coverage = new_coverage

        if best_edge is None:
            break

        u, v = best_edge
        corridor_edges.add((u, v))
        corridor_edges.add((v, u))
        tertiary_nodes.add(u)
        tertiary_nodes.add(v)
        all_corridor_nodes.add(u)
        all_corridor_nodes.add(v)
        covered_nodes |= best_new_coverage

        if iteration % 50 == 0:
            print(f"  Tertiary iteration {iteration}: {len(covered_nodes)}/{total_nodes} "
                  f"({len(covered_nodes) / total_nodes * 100:.1f}%)")

    # ==========================================================================
    # Summary
    # ==========================================================================
    print(f"\n{'=' * 60}")
    print("FINAL RESULTS")
    print(f"{'=' * 60}")
    print(f"Total coverage         : {len(covered_nodes) / total_nodes * 100:.1f}%")
    print(f"Backbone nodes         : {len(backbone_nodes)}")
    print(f"Primary corridor nodes : {len(primary_nodes)}")
    print(f"Secondary corridor nodes: {len(secondary_nodes)}")
    print(f"Tertiary corridor nodes : {len(tertiary_nodes)}")
    print(f"Total corridor edges   : {len(corridor_edges) // 2}")
    print(f"{'=' * 60}\n")

    tier_info = {
        "backbone": backbone_nodes,
        "primary": primary_nodes,
        "secondary": secondary_nodes,
        "tertiary": tertiary_nodes,
    }

    return corridor_edges, covered_nodes, tier_info, backbone_edges


# =============================================================================
# VISUALISATION
# =============================================================================

def plot_multi_origin_corridors(
    G,
    corridor_edges,
    tier_info,
    origin_nodes,
    backbone_edges,
    zoom_start=13,
):
    """
    Visualise the multi-origin emergency corridor network with colour coding.

    Colour scheme
    -------------
    Purple   – Backbone connecting origins
    Dark Red – Primary corridors
    OrangeRed– Secondary corridors
    Orange   – Tertiary corridors
    LightGray– Non-corridor streets
    """
    import folium

    if origin_nodes:
        center = (G.nodes[origin_nodes[0]]["y"], G.nodes[origin_nodes[0]]["x"])
    else:
        n0 = list(G.nodes)[0]
        center = (G.nodes[n0]["y"], G.nodes[n0]["x"])

    m = folium.Map(location=center, zoom_start=zoom_start)

    corridor_edges = set(corridor_edges)
    backbone_edges = set(backbone_edges)

    backbone_nodes = tier_info["backbone"]
    primary_nodes = tier_info["primary"]
    secondary_nodes = tier_info["secondary"]
    tertiary_nodes = tier_info["tertiary"]

    edge_id = []

    for u, v, data in G.edges(data=True):
        latlon = [
            (G.nodes[u]["y"], G.nodes[u]["x"]),
            (G.nodes[v]["y"], G.nodes[v]["x"]),
        ]

        if (u, v) in backbone_edges or (v, u) in backbone_edges:
            color = "purple"
            weight = 7
            opacity = 1.0
            edge_id.append(data)
        elif (u, v) in corridor_edges or (v, u) in corridor_edges:
            if u in primary_nodes and v in primary_nodes:
                color = "darkred"
                weight = 6
                opacity = 1.0
            elif u in secondary_nodes or v in secondary_nodes:
                color = "orangered"
                weight = 4
                opacity = 0.9
            else:
                color = "orange"
                weight = 3
                opacity = 0.8
            edge_id.append(data)
        else:
            color = "lightgray"
            weight = 0.5
            opacity = 0.15

        folium.PolyLine(latlon, color=color, weight=weight, opacity=opacity).add_to(m)

    with open("edges_final.json", "w", encoding="utf-8") as f:
        json.dump(edge_id, f, indent=4)

    for idx, origin in enumerate(origin_nodes):
        folium.CircleMarker(
            location=(G.nodes[origin]["y"], G.nodes[origin]["x"]),
            radius=12,
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=1,
            tooltip=f"Origin {idx + 1}",
        ).add_to(m)

        folium.Marker(
            location=(G.nodes[origin]["y"], G.nodes[origin]["x"]),
            icon=folium.DivIcon(
                html=f'<div style="font-size:12pt;color:blue;font-weight:bold;">{idx + 1}</div>'
            ),
        ).add_to(m)

    return m