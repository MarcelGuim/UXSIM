from graph_creator import *
import configparser
from pathlib import Path
import math
import heapq
import networkx as nx
import folium
from collections import defaultdict

config = configparser.ConfigParser()

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "parameters.ini"

config = configparser.ConfigParser()
config.read(CONFIG_PATH)

zone = config["BASIC"]["zone"]
sim_num = int(config["BASIC"]["sim_num"])
lat = None
lon = None
zoom = None
ambulance_lat = None
ambulance_lon = None

if zone == "eixample":
    lat = config["MAP_EIXAMPLE"]["center_lat"]
    lon = config["MAP_EIXAMPLE"]["center_lon"]
    zoom = config["MAP_EIXAMPLE"]["zoom"]
    ambulance_lat = config["MAP_EIXAMPLE"]["ambulance_lat"]
    ambulance_lon = config["MAP_EIXAMPLE"]["ambulance_lon"]
elif zone == "hospital_clinic":
    lat = config["MAP_CLINIC"]["center_lat"]
    lon = config["MAP_CLINIC"]["center_lon"]
    zoom = config["MAP_CLINIC"]["zoom"]
elif zone == "hospital_del_mar":
    lat = config["MAP_HOSPITAL_DEL_MAR"]["center_lat"]
    lon = config["MAP_HOSPITAL_DEL_MAR"]["center_lon"]
    zoom = config["MAP_HOSPITAL_DEL_MAR"]["zoom"]
elif zone == "hospital_san_pau":
    lat = config["MAP_HOSPITAL_SAN_PAU"]["center_lat"]
    lon = config["MAP_HOSPITAL_SAN_PAU"]["center_lon"]
    zoom = config["MAP_HOSPITAL_SAN_PAU"]["zoom"]
elif zone == "barcelona_completa":
    lat = config["MAP_BARCELONA_COMPLETA"]["center_lat"]
    lon = config["MAP_BARCELONA_COMPLETA"]["center_lon"]
    zoom = config["MAP_BARCELONA_COMPLETA"]["zoom"]
    ambulance_lat = config["MAP_BARCELONA_COMPLETA"]["ambulance_lat"]
    ambulance_lon = config["MAP_BARCELONA_COMPLETA"]["ambulance_lon"]

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

def compute_edge_coverage(G, R):
    """
    Computes which nodes are covered by each edge.
    A node is covered if it's within R meters of the edge.
    """
    edge_coverage = {}
    
    for u, v, data in G.edges(data=True):
        covered_nodes = set()
        
        # Get edge endpoints
        x1, y1 = G.nodes[u]["x"], G.nodes[u]["y"]
        x2, y2 = G.nodes[v]["x"], G.nodes[v]["y"]
        
        # Check distance from each node to this edge
        for node, node_data in G.nodes(data=True):
            px, py = node_data["x"], node_data["y"]
            
            # Calculate perpendicular distance from point to line segment
            dist = point_to_segment_distance(px, py, x1, y1, x2, y2)
            
            # Convert to meters (approximate)
            dist_meters = dist * 111000  # rough conversion for lat/lon to meters
            
            if dist_meters <= R:
                covered_nodes.add(node)
        
        edge_coverage[(u, v)] = covered_nodes
        edge_coverage[(v, u)] = covered_nodes  # undirected
    
    return edge_coverage

def point_to_segment_distance(px, py, x1, y1, x2, y2):
    """Calculate minimum distance from point (px, py) to line segment (x1,y1)-(x2,y2)."""
    dx = x2 - x1
    dy = y2 - y1
    
    if dx == 0 and dy == 0:
        # Segment is a point
        return math.sqrt((px - x1)**2 + (py - y1)**2)
    
    # Parameter t of closest point on infinite line
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    
    # Closest point on segment
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)

def build_hierarchical_emergency_corridors(G, start_node, coverage_radius=200, target_coverage=0.95):
    """
    Builds emergency corridors in a 3-tier hierarchical system:
    1. PRIMARY: Main arteries directly from hospital (8 directions, far-reaching)
    2. SECONDARY: Branch from primary corridors to reach distant areas
    3. TERTIARY: Branch from secondary to fill coverage gaps
    
    All paths maintain shortest route to hospital (no loops).
    
    Args:
        G: NetworkX undirected graph
        start_node: Hospital node
        coverage_radius: Coverage radius in meters
        target_coverage: Target coverage ratio
    
    Returns:
        corridor_edges: Set of edges in corridors
        covered_nodes: Set of nodes covered
        tier_info: Dict with tier classifications
    """
    corridor_edges = set()
    covered_nodes = set()
    primary_nodes = set()
    secondary_nodes = set()
    tertiary_nodes = set()
    
    total_nodes = G.number_of_nodes()
    
    # Precompute shortest paths and distances from hospital
    print("Computing shortest paths from hospital...")
    shortest_paths = nx.single_source_dijkstra_path(G, start_node, weight="length")
    distances = nx.single_source_dijkstra_path_length(G, start_node, weight="length")
    
    # Compute edge coverage
    print(f"Computing edge coverage (R={coverage_radius}m)...")
    edge_coverage = compute_edge_coverage(G, coverage_radius)
    
    # ===== TIER 1: PRIMARY CORRIDORS =====
    print("\n=== TIER 1: Building primary arteries ===")
    
    # Find nodes in 8 main directions (N, NE, E, SE, S, SW, W, NW)
    # and at various distance bands
    primary_targets = []
    
    # Group nodes by direction (8 sectors)
    nodes_by_sector = {i: [] for i in range(8)}
    
    for node, dist in distances.items():
        if dist < 1000:  # Skip very close nodes for primaries
            continue
        
        dx = G.nodes[node]["x"] - G.nodes[start_node]["x"]
        dy = G.nodes[node]["y"] - G.nodes[start_node]["y"]
        
        # Calculate angle (0 = East, 90 = North)
        angle = math.degrees(math.atan2(dy, dx))
        if angle < 0:
            angle += 360
        
        # Assign to sector (0-7)
        sector = int((angle + 22.5) / 45) % 8
        nodes_by_sector[sector].append((node, dist))
    
    # Select 2-3 targets per sector (at different distances)
    for sector in range(8):
        sector_nodes = sorted(nodes_by_sector[sector], key=lambda x: x[1], reverse=True)
        
        # Take 1-3 targets per sector depending on how many nodes are there
        targets_to_add = min(3, len(sector_nodes))
        
        if targets_to_add > 0:
            # Take the farthest node
            primary_targets.append(sector_nodes[0][0])
            
            # If there are more, take one at 50% and 75% distance
            if targets_to_add >= 2 and len(sector_nodes) > len(sector_nodes) // 2:
                primary_targets.append(sector_nodes[len(sector_nodes) // 2][0])
            if targets_to_add >= 3 and len(sector_nodes) > 2 * len(sector_nodes) // 3:
                primary_targets.append(sector_nodes[2 * len(sector_nodes) // 3][0])
    
    print(f"Selected {len(primary_targets)} primary targets across 8 directions")
    
    # Add paths to primary targets
    for target in primary_targets:
        path = shortest_paths[target]
        for i in range(len(path) - 1):
            u, v = path[i], path[i + 1]
            corridor_edges.add((u, v))
            corridor_edges.add((v, u))
            primary_nodes.add(u)
            primary_nodes.add(v)
            
            # Update coverage
            if (u, v) in edge_coverage:
                covered_nodes |= edge_coverage[(u, v)]
    
    print(f"Primary corridors: {len(covered_nodes)}/{total_nodes} nodes covered "
          f"({len(covered_nodes)/total_nodes*100:.1f}%), {len(primary_nodes)} corridor nodes")
    
    # ===== TIER 2: SECONDARY CORRIDORS =====
    print("\n=== TIER 2: Building secondary branches ===")
    
    iteration = 0
    max_iterations = 500
    
    # Secondary branches: connect from primary corridors to reach far uncovered areas
    while len(covered_nodes) / total_nodes < 0.80 and iteration < max_iterations:
        iteration += 1
        
        best_path = None
        best_score = -1
        best_new_coverage = set()
        
        # Find uncovered nodes far from hospital
        uncovered_distant = [(n, distances[n]) for n in distances 
                            if n not in covered_nodes and distances[n] > 500]
        uncovered_distant.sort(key=lambda x: x[1], reverse=True)
        
        # Try to connect top 50 farthest uncovered nodes to primary corridors
        for target_node, _ in uncovered_distant[:50]:
            if target_node not in shortest_paths:
                continue
            
            path = shortest_paths[target_node]
            
            # Find where this path first intersects with primary corridor
            connection_point = None
            for node in path:
                if node in primary_nodes or node in secondary_nodes:
                    connection_point = node
                    break
            
            if connection_point is None:
                continue
            
            # Calculate coverage of the new path segment
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
                    path_length += G[u][v]["length"]
            
            new_coverage = path_coverage - covered_nodes
            
            if len(new_coverage) == 0:
                continue
            
            # Score: prioritize far nodes with good coverage per distance
            score = len(new_coverage) / max(path_length, 1)
            
            if score > best_score:
                best_score = score
                best_path = path
                best_new_coverage = new_coverage
        
        if best_path is None:
            print("No more beneficial secondary branches")
            break
        
        # Add the path
        for i in range(len(best_path) - 1):
            u, v = best_path[i], best_path[i + 1]
            corridor_edges.add((u, v))
            corridor_edges.add((v, u))
            secondary_nodes.add(u)
            secondary_nodes.add(v)
        
        covered_nodes |= best_new_coverage
        
        if iteration % 25 == 0:
            print(f"Secondary iteration {iteration}: {len(covered_nodes)}/{total_nodes} covered "
                  f"({len(covered_nodes)/total_nodes*100:.1f}%)")
    
    print(f"Secondary corridors: {len(covered_nodes)}/{total_nodes} nodes covered "
          f"({len(covered_nodes)/total_nodes*100:.1f}%), {len(secondary_nodes)} corridor nodes")
    
    # ===== TIER 3: TERTIARY CORRIDORS =====
    print("\n=== TIER 3: Adding tertiary streets for full coverage ===")
    
    iteration = 0
    max_iterations = 1000
    
    all_corridor_nodes = primary_nodes | secondary_nodes
    
    while len(covered_nodes) / total_nodes < target_coverage and iteration < max_iterations:
        iteration += 1
        
        # Find the best edge to add
        best_edge = None
        best_score = -1
        best_new_coverage = set()
        
        for corridor_node in all_corridor_nodes:
            for neighbor in G.neighbors(corridor_node):
                if neighbor not in distances:
                    continue
                
                # Only add edges that move away from hospital (no loops back)
                if distances[neighbor] < distances[corridor_node] - 10:
                    continue
                
                edge = (corridor_node, neighbor)
                reverse_edge = (neighbor, corridor_node)
                
                if edge in corridor_edges or reverse_edge in corridor_edges:
                    continue
                
                # Calculate new coverage
                new_coverage = edge_coverage.get(edge, set()) - covered_nodes
                
                if len(new_coverage) == 0:
                    continue
                
                # Score: coverage per meter
                edge_length = G[corridor_node][neighbor]["length"]
                score = len(new_coverage) / max(edge_length, 1)
                
                if score > best_score:
                    best_score = score
                    best_edge = edge
                    best_new_coverage = new_coverage
        
        if best_edge is None:
            print("No more beneficial tertiary edges")
            break
        
        # Add the best edge
        u, v = best_edge
        corridor_edges.add((u, v))
        corridor_edges.add((v, u))
        tertiary_nodes.add(u)
        tertiary_nodes.add(v)
        all_corridor_nodes.add(u)
        all_corridor_nodes.add(v)
        covered_nodes |= best_new_coverage
        
        if iteration % 50 == 0:
            print(f"Tertiary iteration {iteration}: {len(covered_nodes)}/{total_nodes} covered "
                  f"({len(covered_nodes)/total_nodes*100:.1f}%)")
    
    print(f"\n=== FINAL RESULTS ===")
    print(f"Total coverage: {len(covered_nodes) / total_nodes * 100:.1f}%")
    print(f"Primary corridor nodes: {len(primary_nodes)}")
    print(f"Secondary corridor nodes: {len(secondary_nodes)}")
    print(f"Tertiary corridor nodes: {len(tertiary_nodes)}")
    print(f"Total corridor edges: {len(corridor_edges)//2}")
    
    tier_info = {
        'primary': primary_nodes,
        'secondary': secondary_nodes,
        'tertiary': tertiary_nodes
    }
    
    return corridor_edges, covered_nodes, tier_info

def plot_emergency_corridors_hierarchical(
    G,
    corridor_edges,
    tier_info,
    start_node=None,
    zoom_start=13
):
    """
    Visualize the hierarchical emergency corridor network with color coding.
    """
    # Center map
    if start_node is not None:
        center = (G.nodes[start_node]["y"], G.nodes[start_node]["x"])
    else:
        n0 = list(G.nodes)[0]
        center = (G.nodes[n0]["y"], G.nodes[n0]["x"])

    m = folium.Map(location=center, zoom_start=zoom_start)

    corridor_edges = set(corridor_edges)
    
    primary_nodes = tier_info['primary']
    secondary_nodes = tier_info['secondary']
    tertiary_nodes = tier_info['tertiary']

    # Draw all edges with tier-based coloring
    for u, v, data in G.edges(data=True):
        latlon = [
            (G.nodes[u]["y"], G.nodes[u]["x"]),
            (G.nodes[v]["y"], G.nodes[v]["x"]),
        ]

        if (u, v) in corridor_edges or (v, u) in corridor_edges:
            # Determine tier based on both nodes
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
        else:
            color = "lightgray"
            weight = 1
            opacity = 0.15

        folium.PolyLine(
            latlon,
            color=color,
            weight=weight,
            opacity=opacity,
        ).add_to(m)

    # Mark hospital
    if start_node is not None:
        folium.CircleMarker(
            location=(G.nodes[start_node]["y"], G.nodes[start_node]["x"]),
            radius=12,
            color="blue",
            fill=True,
            fill_color="blue",
            fill_opacity=1,
            tooltip="Hospital",
        ).add_to(m)

    return m


# Main execution
if __name__ == "__main__":
    print("Loading graph...")
    edges, junctions = get_points_in_area(
        zone+"/"+zone+".kml", 
        "Code/osm.net_BARCELONA.xml"
    )
    G, pos, colors, edges, junctions = create_graph(edges, junctions)

    print(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    # Convert to undirected
    UG = G.to_undirected()

    # Coverage radius in meters
    R = 200

    print(f"Finding nearest node to hospital coordinates...")
    start_node = nearest_node(UG, ambulance_lon, ambulance_lat)
    print(f"Hospital node: {start_node}")

    print("\nBuilding hierarchical emergency corridors...")
    corridor_edges, covered_nodes, tier_info = build_hierarchical_emergency_corridors(
        UG, start_node, coverage_radius=R, target_coverage=0.95
    )

    print("\nGenerating map...")
    m = plot_emergency_corridors_hierarchical(
        G,
        corridor_edges,
        tier_info,
        start_node=start_node,
        zoom_start=13
    )

    output_file = "barcelona_emergency_corridors_hierarchical.html"
    m.save(output_file)
    print(f"\nMap saved to {output_file}")
    
    # Save corridor edges to file
    edges_file = "emergency_corridor_edges_hierarchical.txt"
    with open(edges_file, 'w') as f:
        f.write("# Emergency Corridor Edges (node_id_1, node_id_2, tier)\n")
        # Remove duplicates by only saving one direction per edge
        saved_edges = set()
        
        primary_edges = []
        secondary_edges = []
        tertiary_edges = []
        
        for u, v in corridor_edges:
            edge = tuple(sorted([u, v]))
            if edge not in saved_edges:
                # Determine tier
                if u in tier_info['primary'] and v in tier_info['primary']:
                    tier = 'primary'
                    primary_edges.append(edge)
                elif u in tier_info['secondary'] or v in tier_info['secondary']:
                    tier = 'secondary'
                    secondary_edges.append(edge)
                else:
                    tier = 'tertiary'
                    tertiary_edges.append(edge)
                
                f.write(f"{edge[0]},{edge[1]},{tier}\n")
                saved_edges.add(edge)
    
    print(f"Corridor edges saved to {edges_file}")
    print(f"  Primary edges: {len(primary_edges)}")
    print(f"  Secondary edges: {len(secondary_edges)}")
    print(f"  Tertiary edges: {len(tertiary_edges)}")
    print(f"  Total unique edges: {len(saved_edges)}")
    
    print("\nHierarchical emergency corridors complete!")
    print("Color coding: Dark Red = Primary, Orange Red = Secondary, Orange = Tertiary")