"""
main.py
=======
Entry point for the dual-tree emergency corridor system.
Builds an OUTBOUND tree (hospital→patient) and an INBOUND tree
(patient→hospital) separately, respecting traffic direction throughout.
"""

from graph_creator import get_points_in_area, create_graph
from dual_tree_corridors import build_dual_tree_corridors

import configparser
from pathlib import Path


# =============================================================================
# CONFIG
# =============================================================================

config   = configparser.ConfigParser()
BASE_DIR = Path(__file__).resolve().parent
config.read(BASE_DIR / "parameters.ini")

zone = config["BASIC"]["zone"]

if zone == "eixample":
    lat  = float(config["MAP_EIXAMPLE"]["center_lat"])
    lon  = float(config["MAP_EIXAMPLE"]["center_lon"])
    zoom = int(config["MAP_EIXAMPLE"]["zoom"])
elif zone == "barcelona_completa":
    lat  = float(config["MAP_BARCELONA_COMPLETA"]["center_lat"])
    lon  = float(config["MAP_BARCELONA_COMPLETA"]["center_lon"])
    zoom = int(config["MAP_BARCELONA_COMPLETA"]["zoom"])
else:
    lat, lon, zoom = 41.3851, 2.1734, 13


# =============================================================================
# HELPERS
# =============================================================================

def nearest_node(G, x, y):
    """Return the graph node closest to (x=longitude, y=latitude)."""
    best_node = None
    best_dist = float("inf")
    for n, d in G.nodes(data=True):
        dx   = float(d["x"]) - float(x)
        dy   = float(d["y"]) - float(y)
        dist = dx * dx + dy * dy
        if dist < best_dist:
            best_dist = dist
            best_node = n
    return best_node


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":

    # ---- Load graph ----
    print("Loading graph...")
    edges, junctions = get_points_in_area(
        zone + "/" + zone + ".kml",
        "Code/osm.net_BARCELONA.xml",
    )
    G, pos, colors, edges, junctions = create_graph(edges, junctions)
    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # ---- Hospital origins ----
    # (longitude, latitude, name)
    origin_coordinates = [
        (2.1539471460882837, 41.38902661612551,  "Hospital Clinic"),
        (2.1746345998135195, 41.416019562159505, "Hospital Sant Pau"),
        (2.194270345996985,  41.38586076739082,  "Hospital del Mar"),
        (2.1428412773627437, 41.42673883887742,  "Hospital Vall d'Hebron"),
    ]

    print(f"\nFinding nearest nodes for {len(origin_coordinates)} hospitals...")
    origin_nodes = []
    for lon_h, lat_h, name in origin_coordinates:
        node = nearest_node(G, lon_h, lat_h)
        origin_nodes.append(node)
        print(f"  {name}: node {node}")

    # ---- Build dual-tree corridors ----
    print("\n" + "=" * 60)
    print("Building dual-tree emergency corridors...")
    print("  OUTBOUND = Hospital → Patient  (warm colours on map)")
    print("  INBOUND  = Patient  → Hospital (cool colours on map)")
    print("=" * 60)

    results = build_dual_tree_corridors(
        G,
        origin_nodes,
        coverage_radius=200,
        target_coverage=0.95,
        backbone_reuse_discount=0.3,
        primary_reuse_discount=0.4,
        secondary_reuse_discount=0.4,
        output_dir="result_emergency_routes",
        output_prefix_outbound="outbound",
        output_prefix_inbound="inbound",
        map_output_file=f"{zone}_dual_tree_corridors.html",
    )

    # ---- Final summary ----
    total = G.number_of_nodes()
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"Outbound edges  : {len(results['outbound_edges'])}")
    print(f"Outbound leaves : {len(results['outbound_leaves'])}  "
          f"(endpoints ambulances reach patients from)")
    print(f"Outbound roots  : {len(results['outbound_roots'])}   "
          f"(should be the hospitals)")
    print()
    print(f"Inbound edges   : {len(results['inbound_edges'])}")
    print(f"Inbound leaves  : {len(results['inbound_leaves'])}  "
          f"(hospitals — final destinations)")
    print(f"Inbound roots   : {len(results['inbound_roots'])}   "
          f"(patient pick-up entry points)")
    print()
    print(f"Outbound coverage : {len(results['outbound_covered'])/total*100:.1f}%")
    print(f"Inbound coverage  : {len(results['inbound_covered'])/total*100:.1f}%")
    print(f"Fully covered     : {len(results['fully_covered'])/total*100:.1f}%  "
          f"(both reachable from AND can reach a hospital)")
    print("=" * 60)
    print("\nOutput files:")
    print("  outbound_edges.json   — outbound corridor edges with tier + edge data")
    print("  outbound_nodes.json   — outbound corridor nodes with tier + node data")
    print("  outbound_leaves.json  — outbound leaf/root endpoints")
    print("  inbound_edges.json    — inbound corridor edges")
    print("  inbound_nodes.json    — inbound corridor nodes")
    print("  inbound_leaves.json   — inbound leaf/root endpoints")
    print("  corridor_summary.json — combined statistics")
    print(f"  {zone}_dual_tree_corridors.html — interactive map")
    print("\nDone.")