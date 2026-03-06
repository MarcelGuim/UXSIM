"""
build_map_from_files.py
=======================

Rebuilds the dual-tree corridor map and recomputes coverage statistics
from the post-ILP modified files:

  ILP/data/nodes_inbound.json
  ILP/data/nodes_outbound.json
  ILP/data/edges_inbound.json
  ILP/data/edges_outbound.json
  ILP/data/final_routes_inbound.json
  ILP/data/final_routes_outbound.json
  edge_coverage_directed.pkl

Outputs
-------
  dual_tree_corridors_ilp.html   — interactive Folium map
  corridor_summary_ilp.json      — coverage statistics

Usage
-----
  python build_map_from_files.py

  Optionally override paths at the bottom of this file.
"""

import json
import pickle
from collections import defaultdict
from pathlib import Path

import networkx as nx
import folium
from folium import FeatureGroup, LayerControl


# =============================================================================
# LOADERS
# =============================================================================

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_nodes(path):
    """Returns dict  node_id (str) → attr dict."""
    return load_json(path)


def load_edges(path):
    """Returns dict  edge_id (str) → attr dict."""
    return load_json(path)


def load_routes(path):
    """Returns list of routes; each route is a list of node-id strings."""
    return load_json(path)


def load_coverage(path):
    """Returns edge_coverage dict  (u, v) → set of covered node ids."""
    with open(path, "rb") as f:
        return pickle.load(f)


# =============================================================================
# BUILD LIGHTWEIGHT GRAPH FROM NODE / EDGE FILES
# =============================================================================

def build_graph_from_files(nodes_dict, edges_dict):
    """
    Construct a DiGraph purely from the surviving nodes and edges.

    Edge connectivity is inferred from the 'incoming_edges' and
    'outgoing_edges' fields stored on each edge record:
      - incoming_edges  → the node that feeds into this edge (tail)
      - outgoing_edges  → the node this edge leads into (head)

    Node positions are taken from nodes_dict (keys 'x', 'y').
    """
    G = nx.DiGraph()

    for nid, attr in nodes_dict.items():
        G.add_node(nid, **attr)

    for eid, attr in edges_dict.items():
        u = str(attr.get("incoming_edges", ""))
        v = str(attr.get("outgoing_edges", ""))
        if u and v and u in nodes_dict and v in nodes_dict:
            G.add_edge(u, v, edge_id=eid, **attr)

    return G


# =============================================================================
# DERIVE CORRIDOR EDGES & TIER INFO FROM ROUTES + EDGE DICTS
# =============================================================================

def routes_to_corridor_sets(routes, edges_dict, nodes_dict):
    """
    Walk every route (list of node ids) and collect the directed edges
    (u, v) that are present in edges_dict.

    Because routes store node sequences and edges_dict keys are edge ids
    (not node pairs), we derive edges from consecutive node pairs in the
    route and match against the graph topology encoded in edges_dict.

    Returns
    -------
    corridor_edges  : set of (u, v) tuples
    tier_edges      : dict  tier → set of (u, v)
    corridor_nodes  : set of node id strings
    leaf_nodes      : set  (out_degree == 0 in corridor subgraph)
    root_nodes      : set  (in_degree  == 0 in corridor subgraph)
    """
    # Build a fast lookup:  (incoming_node, outgoing_node) → edge record
    pair_to_edge = {}
    for eid, attr in edges_dict.items():
        u = str(attr.get("incoming_edges", ""))
        v = str(attr.get("outgoing_edges", ""))
        if u and v:
            pair_to_edge[(u, v)] = attr

    corridor_edges = set()
    tier_map = {}   # (u,v) → tier from node data (will be resolved later)

    for route in routes:
        for i in range(len(route) - 1):
            u, v = str(route[i]), str(route[i + 1])
            if (u, v) in pair_to_edge:
                corridor_edges.add((u, v))

    corridor_nodes = set()
    for u, v in corridor_edges:
        corridor_nodes.add(u)
        corridor_nodes.add(v)

    # Leaf / root detection on corridor subgraph
    sub = nx.DiGraph()
    sub.add_edges_from(corridor_edges)
    leaf_nodes = {n for n in sub.nodes() if sub.out_degree(n) == 0}
    root_nodes = {n for n in sub.nodes() if sub.in_degree(n) == 0}

    return corridor_edges, corridor_nodes, leaf_nodes, root_nodes


def classify_edge_tiers(corridor_edges, nodes_dict_src, nodes_dict_dst):
    """
    Assign a tier to each corridor edge using the tier stored on the
    SOURCE node (u).  Falls back to destination node, then 'tertiary'.

    Returns dict  (u, v) → tier string
    """
    tier_order = {"backbone": 0, "primary": 1, "secondary": 2, "tertiary": 3}
    edge_tier = {}
    for (u, v) in corridor_edges:
        t_u = nodes_dict_src.get(str(u), {}).get("tier", None) or \
              nodes_dict_dst.get(str(u), {}).get("tier", None)
        t_v = nodes_dict_src.get(str(v), {}).get("tier", None) or \
              nodes_dict_dst.get(str(v), {}).get("tier", None)
        candidates = [t for t in [t_u, t_v] if t in tier_order]
        if candidates:
            edge_tier[(u, v)] = min(candidates, key=lambda t: tier_order[t])
        else:
            edge_tier[(u, v)] = "tertiary"
    return edge_tier


# =============================================================================
# COVERAGE RECOMPUTATION
# =============================================================================

def recompute_coverage(corridor_edges, edge_coverage):
    """
    Return the set of all node ids covered by at least one corridor edge,
    using the cached edge_coverage lookup.

    edge_coverage keys may be tuples of ints or strings — handle both.
    """
    covered = set()

    # Normalise coverage keys to strings once
    str_coverage = {}
    for key, val in edge_coverage.items():
        sk = (str(key[0]), str(key[1]))
        str_coverage[sk] = {str(x) for x in val}

    for edge in corridor_edges:
        se = (str(edge[0]), str(edge[1]))
        if se in str_coverage:
            covered |= str_coverage[se]
        # symmetric fallback (coverage is symmetric in the original code)
        rev = (se[1], se[0])
        if rev in str_coverage:
            covered |= str_coverage[rev]

    return covered


# =============================================================================
# FOLIUM MAP
# =============================================================================

def get_xy(nodes_all, nid):
    """Return (lat, lon) = (y, x) for a node id."""
    n = nodes_all.get(str(nid), {})
    return float(n.get("y", 0)), float(n.get("x", 0))


def plot_map(
    nodes_out, nodes_in,
    out_edges, in_edges,
    out_edge_tier, in_edge_tier,
    out_leaves, out_roots,
    in_leaves, in_roots,
    origin_nodes,
    out_covered, in_covered,
    zoom_start=13,
    output_file="dual_tree_corridors_ilp.html",
):
    """
    Render both trees as separate toggleable layers.

    Tier colours
    ────────────
    Outbound (warm):  backbone #8B0000 | primary #e60000 | secondary #ff4500 | tertiary #ff9900
    Inbound  (cool):  backbone #00008B | primary #1a6ef5 | secondary #4682b4 | tertiary #87ceeb
    """
    nodes_all = {**nodes_out, **nodes_in}

    # Determine map centre from first origin
    first_origin = origin_nodes[0] if origin_nodes else list(nodes_all.keys())[0]
    center = get_xy(nodes_all, first_origin)
    m = folium.Map(location=center, zoom_start=zoom_start,
                   tiles="CartoDB positron")

    def line(fg, u, v, color, weight, opacity=0.9):
        a = get_xy(nodes_all, u)
        b = get_xy(nodes_all, v)
        if a == (0, 0) or b == (0, 0):
            return
        folium.PolyLine([a, b], color=color, weight=weight,
                        opacity=opacity).add_to(fg)

    out_color = {
        "backbone":  ("#8B0000", 7, 1.0),
        "primary":   ("#e60000", 5, 0.9),
        "secondary": ("#ff4500", 3, 0.9),
        "tertiary":  ("#ff9900", 2, 0.85),
    }
    in_color = {
        "backbone":  ("#00008B", 7, 1.0),
        "primary":   ("#1a6ef5", 5, 0.9),
        "secondary": ("#4682b4", 3, 0.9),
        "tertiary":  ("#87ceeb", 2, 0.85),
    }

    # ── Outbound layers ──────────────────────────────────────────────────────
    fg_out = {t: FeatureGroup(name=f"Outbound — {t.capitalize()}", show=True)
              for t in ("backbone", "primary", "secondary", "tertiary")}
    fg_out_ep  = FeatureGroup(name="Outbound — Endpoints",  show=True)
    fg_out_rts = FeatureGroup(name="Outbound — Routes",     show=False)

    for (u, v), tier in out_edge_tier.items():
        c, w, op = out_color.get(tier, ("#ff9900", 2, 0.85))
        line(fg_out[tier], u, v, c, w, op)

    for node in out_leaves:
        loc = get_xy(nodes_all, node)
        if loc == (0, 0):
            continue
        folium.CircleMarker(
            location=loc, radius=6, color="#8B0000", fill=True,
            fill_color="#e60000", fill_opacity=0.9,
            tooltip=f"Outbound endpoint: {node}",
        ).add_to(fg_out_ep)

    for fg in list(fg_out.values()) + [fg_out_ep, fg_out_rts]:
        fg.add_to(m)

    # ── Inbound layers ───────────────────────────────────────────────────────
    fg_in = {t: FeatureGroup(name=f"Inbound — {t.capitalize()}", show=True)
             for t in ("backbone", "primary", "secondary", "tertiary")}
    fg_in_ep  = FeatureGroup(name="Inbound — Entry points", show=True)
    fg_in_rts = FeatureGroup(name="Inbound — Routes",       show=False)

    for (u, v), tier in in_edge_tier.items():
        c, w, op = in_color.get(tier, ("#87ceeb", 2, 0.85))
        line(fg_in[tier], u, v, c, w, op)

    for node in in_roots:
        loc = get_xy(nodes_all, node)
        if loc == (0, 0):
            continue
        folium.CircleMarker(
            location=loc, radius=6, color="#00008B", fill=True,
            fill_color="#1a6ef5", fill_opacity=0.9,
            tooltip=f"Inbound entry point: {node}",
        ).add_to(fg_in_ep)

    for fg in list(fg_in.values()) + [fg_in_ep, fg_in_rts]:
        fg.add_to(m)

    # ── Uncovered nodes (hidden by default) ──────────────────────────────────
    all_node_ids = set(nodes_all.keys())
    uncovered = all_node_ids - (out_covered | in_covered)
    fg_unc = FeatureGroup(name="Uncovered nodes", show=False)
    for nid in uncovered:
        loc = get_xy(nodes_all, nid)
        if loc == (0, 0):
            continue
        folium.CircleMarker(
            location=loc, radius=3, color="#cc0000", fill=True,
            fill_color="#cc0000", fill_opacity=0.6, weight=0,
            tooltip=f"Not covered: {nid}",
        ).add_to(fg_unc)
    fg_unc.add_to(m)

    # ── Hospitals ─────────────────────────────────────────────────────────────
    fg_hosp = FeatureGroup(name="Hospitals", show=True)
    for idx, origin in enumerate(origin_nodes):
        loc = get_xy(nodes_all, origin)
        folium.CircleMarker(
            location=loc, radius=12, color="purple", fill=True,
            fill_color="purple", fill_opacity=1.0,
            tooltip=f"Hospital {idx + 1}: {origin}",
        ).add_to(fg_hosp)
        folium.Marker(
            location=loc,
            icon=folium.DivIcon(
                html=(f'<div style="font-size:11pt;color:purple;'
                      f'font-weight:bold;white-space:nowrap;">H{idx+1}</div>')
            ),
        ).add_to(fg_hosp)
    fg_hosp.add_to(m)

    LayerControl(collapsed=False, position="topright").add_to(m)
    m.save(output_file)
    print(f"  Map saved → {output_file}")
    return m


# =============================================================================
# MAIN
# =============================================================================

def main(
    data_dir="ILP/data",
    coverage_pkl="edge_coverage_directed.pkl",
    map_output="dual_tree_corridors_ilp_2.html",
    summary_output="corridor_summary_ilp_2.json",
):
    data_dir = Path(data_dir)
    print("Loading files...")

    nodes_out   = load_nodes(data_dir / "nodes_outbound_have_to_modify.json")
    nodes_in    = load_nodes(data_dir / "nodes_inbound_have_to_modify.json")
    edges_out   = load_edges(data_dir / "edges_outbound.json")
    edges_in    = load_edges(data_dir / "edges_inbound.json")
    routes_out  = load_routes(data_dir / "final_routes_outbound_deprecated.json")
    routes_in   = load_routes(data_dir / "final_routes_inbound_deprecated.json")

    print(f"  Outbound: {len(nodes_out)} nodes, {len(edges_out)} edges, "
          f"{len(routes_out)} routes")
    print(f"  Inbound:  {len(nodes_in)} nodes, {len(edges_in)} edges, "
          f"{len(routes_in)} routes")

    print("\nLoading edge coverage cache...")
    edge_coverage = load_coverage(coverage_pkl)
    print(f"  {len(edge_coverage)} coverage entries loaded")

    # ── Derive corridor edges from routes ────────────────────────────────────
    print("\nDeriving corridor edges from routes...")

    out_corridor, out_cnodes, out_leaves, out_roots = routes_to_corridor_sets(
        routes_out, edges_out, nodes_out)
    in_corridor, in_cnodes, in_leaves, in_roots = routes_to_corridor_sets(
        routes_in, edges_in, nodes_in)

    print(f"  Outbound corridor: {len(out_corridor)} edges, "
          f"{len(out_leaves)} leaves, {len(out_roots)} roots")
    print(f"  Inbound  corridor: {len(in_corridor)} edges, "
          f"{len(in_leaves)} leaves, {len(in_roots)} roots")

    # ── Tier classification ───────────────────────────────────────────────────
    out_edge_tier = classify_edge_tiers(out_corridor, nodes_out, nodes_in)
    in_edge_tier  = classify_edge_tiers(in_corridor,  nodes_in, nodes_out)

    tier_counts = lambda d: {t: sum(1 for v in d.values() if v == t)
                             for t in ("backbone","primary","secondary","tertiary")}
    print(f"\n  Outbound tier counts: {tier_counts(out_edge_tier)}")
    print(f"  Inbound  tier counts: {tier_counts(in_edge_tier)}")

    # ── Recompute coverage ────────────────────────────────────────────────────
    print("\nRecomputing coverage...")
    out_covered = recompute_coverage(out_corridor, edge_coverage)
    in_covered  = recompute_coverage(in_corridor,  edge_coverage)

    all_nodes = set(nodes_out.keys()) | set(nodes_in.keys())
    total     = len(all_nodes)
    fully     = out_covered & in_covered

    print(f"  Outbound coverage : {len(out_covered)}/{total} "
          f"({len(out_covered)/total*100:.1f}%)")
    print(f"  Inbound  coverage : {len(in_covered)}/{total} "
          f"({len(in_covered)/total*100:.1f}%)")
    print(f"  Fully covered     : {len(fully)}/{total} "
          f"({len(fully)/total*100:.1f}%)")

    # ── Detect origin nodes ───────────────────────────────────────────────────
    origin_nodes = [nid for nid, attr in {**nodes_out, **nodes_in}.items()
                    if attr.get("is_origin", False)]
    print(f"\n  Origin (hospital) nodes: {origin_nodes}")

    # ── Build map ─────────────────────────────────────────────────────────────
    print("\nBuilding map...")
    plot_map(
        nodes_out, nodes_in,
        out_corridor, in_corridor,
        out_edge_tier, in_edge_tier,
        out_leaves, out_roots,
        in_leaves, in_roots,
        origin_nodes,
        out_covered, in_covered,
        output_file=map_output,
    )

    # ── Summary JSON ──────────────────────────────────────────────────────────
    summary = {
        "total_nodes": total,
        "outbound": {
            "corridor_edges": len(out_corridor),
            "covered_nodes" : len(out_covered),
            "coverage_pct"  : round(len(out_covered) / total * 100, 2),
            "leaf_nodes"    : len(out_leaves),
            "root_nodes"    : len(out_roots),
            "tier_counts"   : tier_counts(out_edge_tier),
        },
        "inbound": {
            "corridor_edges": len(in_corridor),
            "covered_nodes" : len(in_covered),
            "coverage_pct"  : round(len(in_covered) / total * 100, 2),
            "leaf_nodes"    : len(in_leaves),
            "root_nodes"    : len(in_roots),
            "tier_counts"   : tier_counts(in_edge_tier),
        },
        "combined": {
            "fully_covered_nodes": len(fully),
            "fully_covered_pct"  : round(len(fully) / total * 100, 2),
            "note": "nodes reachable FROM a hospital AND that can reach a hospital",
        },
    }

    with open(summary_output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"  Summary saved → {summary_output}")

    return summary


if __name__ == "__main__":
    # ── Configure paths here ──────────────────────────────────────────────────
    main(
        data_dir       = "ILP/data",
        coverage_pkl   = "edge_coverage_directed.pkl",
        map_output     = "dual_tree_corridors_ilp_2.html",
        summary_output = "corridor_summary_ilp.json",
    )