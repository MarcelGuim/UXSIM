from graph_creator import *
from multi_origin_corridors import (
    build_multi_origin_emergency_corridors,
    plot_multi_origin_corridors
)
import configparser
from pathlib import Path
import json

# Load configuration
config = configparser.ConfigParser()
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "parameters.ini"
config.read(CONFIG_PATH)

zone = config["BASIC"]["zone"]

# Get map parameters based on zone
if zone == "eixample":
    lat = config["MAP_EIXAMPLE"]["center_lat"]
    lon = config["MAP_EIXAMPLE"]["center_lon"]
    zoom = config["MAP_EIXAMPLE"]["zoom"]
elif zone == "barcelona_completa":
    lat = config["MAP_BARCELONA_COMPLETA"]["center_lat"]
    lon = config["MAP_BARCELONA_COMPLETA"]["center_lon"]
    zoom = config["MAP_BARCELONA_COMPLETA"]["zoom"]
else:
    # Default
    lat = 41.3851
    lon = 2.1734
    zoom = 13


def nearest_node(G, x, y):
    """Finds the closest node to the given coordinates."""
    best_node = None
    best_dist = float("inf")

    for n, d in G.nodes(data=True):
        dx = d["x"] - float(x)
        dy = d["y"] - float(y)
        dist = dx*dx + dy*dy
        if dist < best_dist:
            best_dist = dist
            best_node = n

    return best_node


if __name__ == "__main__":
    print("Loading graph...")
    edges, junctions = get_points_in_area(
        zone + "/" + zone + ".kml", 
        "Code/osm.net_BARCELONA.xml"
    )
    G, pos, colors, edges, junctions = create_graph(edges, junctions)

    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Convert to undirected
    #UG = G.to_undirected()
    UG = G
    # ===== DEFINE MULTIPLE ORIGINS =====
    # Example: Multiple hospitals/emergency stations in Barcelona
    
    origin_coordinates = [
        # (longitude, latitude, name)
        (2.1539471460882837,41.38902661612551, "Hospital Clinic"),      # Hospital Clinic
        (2.1746345998135195, 41.416019562159505, "Hospital Sant Pau"),    # Hospital Sant Pau
        (2.194270345996985, 41.38586076739082, "Hospital del Mar"),     # Hospital del Mar
        (2.1428412773627437, 41.42673883887742, "Hospital Vall d'Hebron"),  # Hospital Sant Joan de Déu
        # Add more as needed
    ]
    
    # Find nearest nodes for all origins
    print(f"\nFinding nearest nodes for {len(origin_coordinates)} origins...")
    origin_nodes = []
    
    for lon, lat, name in origin_coordinates:
        node = nearest_node(UG, lon, lat)
        origin_nodes.append(node)
        print(f"  {name}: node {node} at ({lat:.4f}, {lon:.4f})")
    
    # ===== BUILD MULTI-ORIGIN CORRIDORS =====
    print("\n" + "="*60)
    print("Building multi-origin emergency corridors...")
    print("="*60)
    
    coverage_radius = 200  # meters
    target_coverage = 0.95  # 95% coverage goal
    
    corridor_edges, covered_nodes, tier_info, backbone_edges = \
        build_multi_origin_emergency_corridors(
            UG, 
            origin_nodes, 
            coverage_radius=coverage_radius,
            target_coverage=target_coverage
        )
    
    # ===== GENERATE VISUALIZATION =====
    print("\nGenerating map...")
    m = plot_multi_origin_corridors(
        G,
        corridor_edges,
        tier_info,
        origin_nodes,
        backbone_edges,
        zoom_start=int(zoom)
    )

    output_file = "barcelona_multi_origin_corridors_directed_with_all_combinations_second_try.html"
    m.save(output_file)
    print(f"\nMap saved to {output_file}")
    
    # ===== SAVE CORRIDOR DATA =====
    edges_file = "multi_origin_corridor_edges_directed.txt"
    with open(edges_file, 'w') as f:
        f.write("# Multi-Origin Emergency Corridor Edges\n")
        f.write(f"# Origins: {len(origin_nodes)}\n")
        f.write("# Format: node_id_1,node_id_2,tier\n")
        f.write("#\n")
        
        saved_edges = set()
        
        backbone_list = []
        primary_list = []
        secondary_list = []
        tertiary_list = []
        
        for u, v in corridor_edges:
            edge = tuple(sorted([u, v]))
            if edge in saved_edges:
                continue
            
            # Determine tier
            if (u, v) in backbone_edges or (v, u) in backbone_edges:
                tier = 'backbone'
                backbone_list.append(edge)
            elif u in tier_info['primary'] and v in tier_info['primary']:
                tier = 'primary'
                primary_list.append(edge)
            elif u in tier_info['secondary'] or v in tier_info['secondary']:
                tier = 'secondary'
                secondary_list.append(edge)
            else:
                tier = 'tertiary'
                tertiary_list.append(edge)
            
            f.write(f"{edge[0]},{edge[1]},{tier}\n")
            saved_edges.add(edge)
    
    print(f"\nCorridor edges saved to {edges_file}")
    print(f"  Backbone edges: {len(backbone_list)}")
    print(f"  Primary edges: {len(primary_list)}")
    print(f"  Secondary edges: {len(secondary_list)}")
    print(f"  Tertiary edges: {len(tertiary_list)}")
    print(f"  Total unique edges: {len(saved_edges)}")

    # ===== SAVE ORIGIN INFORMATION =====
    origins_file = "emergency_origins.txt"
    with open(origins_file, 'w') as f:
        f.write("# Emergency Service Origins\n")
        f.write("# Format: node_id,latitude,longitude,name\n")
        for idx, (node_id, (lon, lat, name)) in enumerate(zip(origin_nodes, origin_coordinates)):
            f.write(f"{node_id},{lat},{lon},{name}\n")
    
    print(f"\nOrigin information saved to {origins_file}")
    
    # ===== STATISTICS =====
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    print(f"Number of origins: {len(origin_nodes)}")
    print(f"Coverage radius: {coverage_radius}m")
    print(f"Target coverage: {target_coverage*100:.1f}%")
    print(f"Achieved coverage: {len(covered_nodes)/UG.number_of_nodes()*100:.1f}%")
    print(f"Total corridor edges: {len(corridor_edges)//2}")
    print(f"\nColor coding:")
    print(f"  Purple    = Backbone (connecting origins)")
    print(f"  Dark Red  = Primary corridors")
    print(f"  Orange Red = Secondary corridors")
    print(f"  Orange    = Tertiary corridors")
    print("="*60)
    
    print("\nMulti-origin emergency corridors complete!")