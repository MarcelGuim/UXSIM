import math
import networkx as nx
from collections import defaultdict
import json
def build_multi_origin_emergency_corridors(
    G, 
    origin_nodes, 
    coverage_radius=200, 
    target_coverage=0.95,
    backbone_weight=2.0
):
    """
    Builds emergency corridors from multiple origins (hospitals/stations) with:
    1. BACKBONE: Connects all origins together via shortest paths
    2. PRIMARY: Main arteries from each origin (8 directions per origin)
    3. SECONDARY: Branches from primary corridors to reach distant areas
    4. TERTIARY: Fill remaining coverage gaps
    
    Args:
        G: NetworkX undirected graph
        origin_nodes: List of origin node IDs (hospitals/stations)
        coverage_radius: Coverage radius in meters
        target_coverage: Target coverage ratio (0-1)
        backbone_weight: Multiplier for backbone importance (higher = thicker backbone)
    
    Returns:
        corridor_edges: Set of edges in corridors
        covered_nodes: Set of nodes covered
        tier_info: Dict with tier classifications
        backbone_edges: Set of edges in the backbone network
    """
    corridor_edges = set()
    covered_nodes = set()
    backbone_nodes = set()
    primary_nodes = set()
    secondary_nodes = set()
    tertiary_nodes = set()
    backbone_edges = set()
    
    total_nodes = G.number_of_nodes()
    
    print(f"\n{'='*60}")
    print(f"Building multi-origin emergency corridors")
    print(f"Origins: {len(origin_nodes)}")
    print(f"Total nodes: {total_nodes}")
    print(f"{'='*60}\n")
    
    # Compute edge coverage
    """
    print(f"Computing edge coverage (R={coverage_radius}m)...")
    edge_coverage=None
    try:
        with open("edge_coverage.pkl", "rb") as f:
            edge_coverage = pickle.load(f)
    except:
        edge_coverage = compute_edge_coverage(G, coverage_radius)
    """
    print(f"Computing edge coverage (R={coverage_radius}m)...")
    edge_coverage=None
    try:
        with open("edge_coverage_directed.pkl", "rb") as f:
            edge_coverage = pickle.load(f)
    except:
        edge_coverage = compute_edge_coverage(G, coverage_radius)
        
    # ===== STEP 1: BUILD BACKBONE CONNECTING ALL ORIGINS =====
    print("\n=== STEP 1: Building backbone network ===")
    """
    # Create a minimum spanning tree connecting all origins
    # Using shortest path distances between origins
    origin_distances = {}
    origin_paths = {}
    combinations = []
    for o in origin_nodes:
        for ori in origin_nodes:
            if o != ori:
                 combinations.append([o, ori])
    for c in combinations:
        try:
            path = nx.shortest_path(G, c[0], c[1], weight="length")
            length = nx.shortest_path_length(G, c[0], c[1], weight="length")
            origin_distances[(c[0], c[1])] = length
            origin_paths[(c[0], c[1])] = path
        except nx.NetworkXNoPath:
            print(f"Warning: No path between {c[0]} and {c[1]}")
    for i, origin_a in enumerate(origin_nodes):
        for origin_b in origin_nodes[i+1:]:
            combinations.append([origin_a, origin_b])
            try:
                path = nx.shortest_path(G, origin_a, origin_b, weight="length")
                length = nx.shortest_path_length(G, origin_a, origin_b, weight="length")
                origin_distances[(origin_a, origin_b)] = length
                origin_paths[(origin_a, origin_b)] = path
            except nx.NetworkXNoPath:
                print(f"Warning: No path between {origin_a} and {origin_b}")
    # Build MST of origins
    if len(origin_nodes) > 1:
        # Create a graph of just the origins
        origin_graph = nx.Graph()
        for (a, b), dist in origin_distances.items():
            origin_graph.add_edge(a, b, weight=dist)
        
        # Get MST
        mst = nx.minimum_spanning_tree(origin_graph)
        
        # Add MST paths to backbone
        for origin_a, origin_b in mst.edges():
            path_key = (origin_a, origin_b) if (origin_a, origin_b) in origin_paths else (origin_b, origin_a)
            path = origin_paths[path_key]
            
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                corridor_edges.add((u, v))
                corridor_edges.add((v, u))
                backbone_edges.add((u, v))
                backbone_edges.add((v, u))
                backbone_nodes.add(u)
                backbone_nodes.add(v)
                
                # Update coverage
                if (u, v) in edge_coverage:
                    covered_nodes |= edge_coverage[(u, v)]
        
        print(f"Backbone: Connected {len(origin_nodes)} origins with {len(backbone_edges)//2} edges")
        print(f"Initial coverage: {len(covered_nodes)}/{total_nodes} nodes ({len(covered_nodes)/total_nodes*100:.1f}%)")
    else:
        print("Single origin - no backbone needed")
    """
        # ===== STEP 1: BUILD BACKBONE CONNECTING ALL ORIGINS =====

    origin_distances = {}
    origin_paths = {}

    # Compute paths between ALL ordered pairs (a→b AND b→a)
    for i, origin_a in enumerate(origin_nodes):
        for j, origin_b in enumerate(origin_nodes):
            if origin_a == origin_b:
                continue
            try:
                path = nx.shortest_path(G, origin_a, origin_b, weight="length")
                length = nx.shortest_path_length(G, origin_a, origin_b, weight="length")
                origin_distances[(origin_a, origin_b)] = length
                origin_paths[(origin_a, origin_b)] = path
            except nx.NetworkXNoPath:
                print(f"Warning: No path between {origin_a} and {origin_b}")

    # Add ALL pairwise paths directly to the backbone (no MST pruning)
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

    print(f"Backbone: Connected {len(origin_nodes)} origins with {len(backbone_edges)//2} unique edges")
    print(f"Pairs computed: {len(origin_paths)} directed paths")
    print(f"Initial coverage: {len(covered_nodes)}/{total_nodes} nodes ({len(covered_nodes)/total_nodes*100:.1f}%)")
    
    # ===== STEP 2: PRECOMPUTE SHORTEST PATHS FROM ALL ORIGINS =====
    print("\n=== STEP 2: Computing shortest paths from all origins ===")
    
    # For each node, find which origin is closest
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
    
    # ===== STEP 3: BUILD PRIMARY CORRIDORS FROM EACH ORIGIN =====
    print("\n=== STEP 3: Building primary arteries from each origin ===")
    for origin_idx, origin in enumerate(origin_nodes):
        print(f"\nOrigin {origin_idx + 1}/{len(origin_nodes)}: node {origin}")
        
        # Find nodes in 8 main directions from this origin
        nodes_by_sector = {i: [] for i in range(8)}
        
        # Get distances for this origin
        origin_distances = nx.single_source_dijkstra_path_length(G, origin, weight="length")
        
        for node, dist in origin_distances.items():
            if node == origin:
                continue
            
            # Only include nodes that are closest to this origin
            if node_to_closest_origin.get(node) != origin:
                continue
            
            if dist < 500:  # Skip very close nodes
                continue
            
            dx = G.nodes[node]["x"] - G.nodes[origin]["x"]
            dy = G.nodes[node]["y"] - G.nodes[origin]["y"]
            
            angle = math.degrees(math.atan2(dy, dx))
            if angle < 0:
                angle += 360
            
            sector = int((angle + 22.5) / 45) % 8
            nodes_by_sector[sector].append((node, dist))
        
        # Select targets per sector
        primary_targets = []
        for sector in range(8):
            sector_nodes = sorted(nodes_by_sector[sector], key=lambda x: x[1], reverse=True)
            
            if len(sector_nodes) > 0:
                # Take farthest node
                primary_targets.append(sector_nodes[0][0])
                
                # Add intermediate targets if sector is large enough
                if len(sector_nodes) > 5:
                    primary_targets.append(sector_nodes[len(sector_nodes) // 2][0])
        
        print(f"  Selected {len(primary_targets)} primary targets")
        
        # Add paths to primary targets
        for target in primary_targets:
            path = all_shortest_paths[origin][target]
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                
                # Skip if already in backbone
                if (u, v) in backbone_edges:
                    continue
                
                corridor_edges.add((u, v))
                corridor_edges.add((v, u))
                primary_nodes.add(u)
                primary_nodes.add(v)
                
                if (u, v) in edge_coverage:
                    covered_nodes |= edge_coverage[(u, v)]

    print(f"\nPrimary corridors complete: {len(covered_nodes)}/{total_nodes} nodes covered "
          f"({len(covered_nodes)/total_nodes*100:.1f}%)")
    
    # ===== STEP 4: BUILD SECONDARY CORRIDORS =====
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
        
        # Find uncovered nodes far from their nearest origin
        uncovered_distant = [(n, node_distances[n], node_to_closest_origin[n]) 
                            for n in node_distances 
                            if n not in covered_nodes and node_distances[n] > 300]
        uncovered_distant.sort(key=lambda x: x[1], reverse=True)
        
        # Try top candidates
        for target_node, _, origin in uncovered_distant[:50]:
            path = all_shortest_paths[origin][target_node]
            
            # Find connection point to existing corridors
            connection_point = None
            for node in path:
                if node in all_corridor_nodes:
                    connection_point = node
                    break
            
            if connection_point is None:
                continue
            
            # Calculate coverage of new segment
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
            
            score = len(new_coverage) / max(path_length, 1)
            
            if score > best_score:
                best_score = score
                best_path = path
                best_new_coverage = new_coverage
                best_origin = origin
        
        if best_path is None:
            break
        
        # Add the path
        for i in range(len(best_path) - 1):
            u, v = best_path[i], best_path[i + 1]
            corridor_edges.add((u, v))
            corridor_edges.add((v, u))
            secondary_nodes.add(u)
            secondary_nodes.add(v)
            all_corridor_nodes.add(u)
            all_corridor_nodes.add(v)
        
        covered_nodes |= best_new_coverage
        
        if iteration % 25 == 0:
            print(f"Secondary iteration {iteration}: {len(covered_nodes)}/{total_nodes} "
                  f"({len(covered_nodes)/total_nodes*100:.1f}%)")
    
    print(f"Secondary corridors complete: {len(covered_nodes)}/{total_nodes} nodes covered "
          f"({len(covered_nodes)/total_nodes*100:.1f}%)")
    
    # ===== STEP 5: BUILD TERTIARY CORRIDORS =====
    print("\n=== STEP 5: Adding tertiary streets for full coverage ===")
    
    iteration = 0
    max_iterations = 1000
    
    all_corridor_nodes = backbone_nodes | primary_nodes | secondary_nodes
    
    while len(covered_nodes) / total_nodes < target_coverage and iteration < max_iterations:
        iteration += 1
        
        best_edge = None
        best_score = -1
        best_new_coverage = set()
        
        for corridor_node in all_corridor_nodes:
            for neighbor in G.neighbors(corridor_node):
                if neighbor not in node_distances:
                    continue
                
                # Only expand away from nearest origin
                closest_origin = node_to_closest_origin.get(corridor_node)
                if closest_origin and neighbor in node_distances:
                    if node_distances[neighbor] < node_distances.get(corridor_node, float('inf')) - 10:
                        continue
                
                edge = (corridor_node, neighbor)
                if edge in corridor_edges or (neighbor, corridor_node) in corridor_edges:
                    continue
                
                new_coverage = edge_coverage.get(edge, set()) - covered_nodes
                
                if len(new_coverage) == 0:
                    continue
                
                edge_length = G[corridor_node][neighbor]["length"]
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
            print(f"Tertiary iteration {iteration}: {len(covered_nodes)}/{total_nodes} "
                  f"({len(covered_nodes)/total_nodes*100:.1f}%)")
    
    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}")
    print(f"Total coverage: {len(covered_nodes) / total_nodes * 100:.1f}%")
    print(f"Backbone nodes: {len(backbone_nodes)}")
    print(f"Primary corridor nodes: {len(primary_nodes)}")
    print(f"Secondary corridor nodes: {len(secondary_nodes)}")
    print(f"Tertiary corridor nodes: {len(tertiary_nodes)}")
    print(f"Total corridor edges: {len(corridor_edges)//2}")
    print(f"{'='*60}\n")
    
    tier_info = {
        'backbone': backbone_nodes,
        'primary': primary_nodes,
        'secondary': secondary_nodes,
        'tertiary': tertiary_nodes
    }
    
    return corridor_edges, covered_nodes, tier_info, backbone_edges

import pickle

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


def point_to_segment_distance(px, py, x1, y1, x2, y2):
    """Calculate minimum distance from point to line segment."""
    dx = x2 - x1
    dy = y2 - y1
    
    if dx == 0 and dy == 0:
        return math.sqrt((px - x1)**2 + (py - y1)**2)
    
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    return math.sqrt((px - closest_x)**2 + (py - closest_y)**2)


def plot_multi_origin_corridors(
    G,
    corridor_edges,
    tier_info,
    origin_nodes,
    backbone_edges,
    zoom_start=13
):
    """
    Visualize the multi-origin emergency corridor network with color coding.
    
    Color scheme:
    - Purple: Backbone connecting origins
    - Dark Red: Primary corridors
    - Orange Red: Secondary corridors
    - Orange: Tertiary corridors
    - Light Gray: Non-corridor streets
    """
    import folium
    
    # Center map on first origin
    if origin_nodes:
        center = (G.nodes[origin_nodes[0]]["y"], G.nodes[origin_nodes[0]]["x"])
    else:
        n0 = list(G.nodes)[0]
        center = (G.nodes[n0]["y"], G.nodes[n0]["x"])

    m = folium.Map(location=center, zoom_start=zoom_start)

    corridor_edges = set(corridor_edges)
    backbone_edges = set(backbone_edges)
    
    backbone_nodes = tier_info['backbone']
    primary_nodes = tier_info['primary']
    secondary_nodes = tier_info['secondary']
    tertiary_nodes = tier_info['tertiary']
    # Draw all edges with tier-based coloring
    edge_id = []
    for u, v, data in G.edges(data=True):
        latlon = [
            (G.nodes[u]["y"], G.nodes[u]["x"]),
            (G.nodes[v]["y"], G.nodes[v]["x"]),
        ]

        # Determine color and weight based on tier
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
        folium.PolyLine(
            latlon,
            color=color,
            weight=weight,
            opacity=opacity,
        ).add_to(m)


    with open("edges_final.json", "w", encoding="utf-8") as f:
        json.dump(edge_id, f, indent=4)
    # Mark all origins
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
        
        # Add label
        folium.Marker(
            location=(G.nodes[origin]["y"], G.nodes[origin]["x"]),
            icon=folium.DivIcon(html=f'<div style="font-size: 12pt; color: blue; font-weight: bold;">{idx+1}</div>')
        ).add_to(m)

    return m