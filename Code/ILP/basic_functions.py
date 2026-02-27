import json
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from graph_creator import *
from file_parser import *
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

origin_nodes = [
    "30237873",
    "30295271",
    "876375351",
    "1295283770"
]

def get_emergency_path():
    edges = []
    nodes = []

    with open("ILP/data/emergency_corridors/edges_in_emergency_path_directed_2.json", "r", encoding="utf-8") as f:
        edges = json.load(f)

    with open("emergency_corridors/nodes_in_emergency_path_directed_2.json", "r", encoding="utf-8") as f:
        nodes = json.load(f)
    return edges, nodes

def convert_to_dict(edges, nodes):
    edges_dict = {e['id']: EdgeClass(**{k:v for k,v in e.items() if k != "density"})for e in edges}
    nodes_dict = {n['id']: JunctionClass(**n) for n in nodes}
    return edges_dict, nodes_dict

def get_edge_nodes(edges, nodes):
    edges_dict, nodes_dict = convert_to_dict(edges, nodes)
    G, pos, colors, edges_2, junctions = create_graph(edges_dict, nodes_dict)
    nodes_edge = [n for n, d in G.degree() if d == 1]
    for node in nodes_dict.values():
        if len(node.incoming) == 2:
            print(node.incoming)

    return nodes_edge

def get_emergency_map(edges, nodes):
    edges_dict, nodes_dict = convert_to_dict(edges, nodes)
    G, pos, colors, edges_2, junctions = create_graph(edges_dict, nodes_dict)
    outgoing_nodes = [
        n for n in G.nodes()
        if G.out_degree(n) == 1 and G.in_degree(n) == 0 
    ]
    incoming_nodes = [
        n for n in G.nodes()
        if G.out_degree(n) == 0 and G.in_degree(n) == 1 
    ]
    m = folium.Map(location=[41.40355953397279, 2.170929234395508], zoom_start=12)
    for e in edges:
        node_1 = nodes_dict[e["outgoing_edges"]]
        node_2 = nodes_dict[e["incoming_edges"]]
        popup_html = f"""
            <b>Edge ID:</b> {e.get("id")}<br>
            <b>Lanes:</b> {e.get("lanes")}<br>
            <b>Length:</b> {e.get("length")} m<br>
            <b>Speed:</b> {e.get("speed")} m/s<br>
            <b>Vehicles:</b> {e.get("number_of_vehicles")}<br>
            <b>Density:</b> {e.get("density")}
            """
        folium.PolyLine(
            locations=[[node_1.y, node_1.x], [node_2.y, node_2.x]],
            color="black",
            weight="2",
            opacity="1",
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    for n in outgoing_nodes:
        node = nodes_dict[n]
        folium.CircleMarker(
            location=(node.y, node.x),
            radius=5,
            color="red",
            fill=True,
            fill_color="red",
            fill_opacity=1,
        ).add_to(m)
    for n in incoming_nodes:
        node = nodes_dict[n]
        folium.CircleMarker(
            location=(node.y, node.x),
            radius=5,
            color="green",
            fill=True,
            fill_color="green",
            fill_opacity=1,
        ).add_to(m)
    m.save("test_map_5.html")

def get_emergency_routes(edges, nodes):
    edges_dict, nodes_dict = convert_to_dict(edges, nodes)
    G, pos, colors, edges_2, junctions = create_graph(edges_dict, nodes_dict)
    nodes_deg1 = get_edge_nodes(edges, nodes)
    print(len(nodes_deg1))
    routes = []
    for n in nodes_deg1:
        combinations = []
        for o in origin_nodes:
            combinations.append([n,o])
            combinations.append([o,n])
        path2 = None
        for c in combinations:
            if nx.has_path(G, c[0], c[1]):
                path = nx.shortest_path(G, c[0], c[1])
                if path2 == None or len(path2) > len(path):
                    path2 = path
        if path2 == None:
            ikkl = 2
        routes.append(path2)
    return routes

def build_map_from_routes(routes, edges, nodes):
    edges_dict, nodes_dict = convert_to_dict(edges, nodes)
    G, pos, colors, edges_2, junctions = create_graph(edges_dict, nodes_dict)
    G = G.to_undirected()
    nodes_deg1 = [n for n, d in G.degree() if d == 1]
    m = folium.Map(location=[41.40355953397279, 2.170929234395508], zoom_start=12)
    num_routes = len(routes)
    colormap = plt.cm.get_cmap("hsv", num_routes)

    route_colors = [mcolors.to_hex(colormap(i)) for i in range(num_routes)]
    outgoing_hospital = []
    for r in routes:
        if r[0] not in origin_nodes:
            outgoing_hospital.append(r[0])
    for route_idx, route in enumerate(routes):
        color = route_colors[route_idx]

        # Create a layer for this route
        fg = folium.FeatureGroup(name=f"Route {route_idx+1}")

        edge_ids = [
            G[u][v]["id"] for u, v in zip(route[:-1], route[1:])
        ]

        for e in edge_ids:
            edge = edges_dict[e]
            node_1 = nodes_dict[edge.outgoing_edges]
            node_2 = nodes_dict[edge.incoming_edges]

            popup_html = f"""
                <b>Edge ID:</b> {edge.id}<br>
                <b>Lanes:</b> {edge.lanes}<br>
                <b>Length:</b> {edge.length} m<br>
                <b>Speed:</b> {edge.speed} m/s<br>
                <b>Vehicles:</b> {edge.number_of_vehicles}<br>
                <b>Density:</b> {edge.density}
            """

            folium.PolyLine(
                locations=[[node_1.y, node_1.x], [node_2.y, node_2.x]],
                color=color,
                weight=3,
                opacity=0.8,
                popup=folium.Popup(popup_html, max_width=300)
            ).add_to(fg)
        fg.add_to(m)

    for n in nodes_deg1:
        c = "blue"
        if n not in outgoing_hospital:
            c = "red"
        elif n in outgoing_hospital:
            c = "green"
        node = nodes_dict[n]
        folium.CircleMarker(
            location=(node.y, node.x),
            radius=5,
            color= c,
            fill=True,
            fill_color="red",
            fill_opacity=1,
        ).add_to(m)
    m.save("test_map_6.html")

if __name__ == "__main__":
    #edges, nodes = get_emergency_path()
    #routes = get_emergency_routes(edges, nodes)
    #get_emergency_map(edges, nodes)
    #build_map_from_routes(routes, edges, nodes)

    print("done")