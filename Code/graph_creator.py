from shapely.geometry import Point, Polygon
from pykml import parser
import pandas as pd
import matplotlib.pyplot as plt
from file_parser import *
import folium

def create_graph(edges, junctions):
    #This function will create a NetworkX Digrapg with the edges and functions given as parameters.
    #The returned parameters will be the graph, the position of the nodes, a color for reference and the
    #given edges and junctions
    G = nx.DiGraph()
    for j in junctions.values():
        if j.has_tls == 1:
            G.add_node(j.id, color='red', has_tls=True, x=j.x, y=j.y)
        else:
            G.add_node(j.id, color='green', has_tls=False, x=j.x, y=j.y)
    for e in edges.values():
        if G.has_node(e.incoming_edges) and G.has_node(e.outgoing_edges):
            G.add_edge(e.incoming_edges, e.outgoing_edges, **e.as_dict())
        else:
            print("Not found") 
    pos = {j.id: (float(j.x), float(j.y)) for j in junctions.values()}
    colors = [d["color"] for _, d in G.nodes(data=True)]
    return G, pos, colors, edges, junctions

def create_graph_lists(edges, junctions):
    #This function will create a NetworkX Digrapg with the edges and functions given as parameters.
    #The returned parameters will be the graph, the position of the nodes, a color for reference and the
    #given edges and junctions
    G = nx.DiGraph()
    for j in junctions:
        if j["has_tls"] == 1:
            G.add_node(j["id"], color='red', has_tls=True, x=j["x"], y=j["y"])
        else:
            G.add_node(j["id"], color='green', has_tls=True, x=j["x"], y=j["y"])
    for e in edges:
        if G.has_node(e["incoming_edges"]) and G.has_node(e["outgoing_edges"]):
            G.add_edge(e["incoming_edges"], e["outgoing_edges"], **e)
        else:
            print("Not found") 
    #region Deprecated
    """
    #This part of the code removes nodes that have just one incoming and 
    #one outgoing edges, they are the nodes that SUMO enters to representschanges 
    #in between roads or other reasons. They would appear as two separete roads when 
    #they are just one, to avoid problems, they are removed
    
    #ATENTION!!!!!!!!!!!!!!!!
    #This does not remove the nodes that have bidirectional edges just one of each, it would be the 
    #same scenario as before, but these can't be eliminated
    candidates = [n for n in G.nodes if G.in_degree(n) == 1 and G.out_degree(n) == 1]
    removed = []
    for n in candidates:
        preds = list(G.predecessors(n))
        succs = list(G.successors(n))
        if preds and succs:
            u = preds[0]
            v = succs[0]
            if u != v:
                G.add_edge(u, v)
        G.remove_node(n)
        removed.append(n)


    #This part of the code removes the nodes that have just one incoming edge but no outgoing edge 
    # the ones at represent a dead end)  this is so that the future model avoids dead ends.
    nodes_to_remove = [n for n, d in G.nodes(data=True) if len(list(G.neighbors(n))) == 0]
    G.remove_nodes_from(nodes_to_remove)
    """
    #endregion
    pos = {j["id"]: (float(j["x"]), float(j["y"])) for j in junctions}
    colors = [d["color"] for _, d in G.nodes(data=True)]
    return G, pos, colors, edges, junctions

def draw_graph(G, pos, colors, filename):
    #This function will draw the graph and save it in a .png file with the name filename
    plt.figure(figsize=(10, 8))
    nx.draw(
        G, pos,
        with_labels=True,
        node_size=50,
        font_size=6,
        arrows=True,
        node_color=colors
    )
    edge_labels = {
    (u, v): f"id={d.get('id', '')}, len={d.get('length', '')}, spd={d.get('speed', '')}, lanes={d.get('lanes', '')}, veh_speed={d.get('vehicle_speed','')}, dens={d.get('density', '')}"
        for u, v, d in G.edges(data=True)
    }
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=6)
    plt.savefig(f"{filename}.png", dpi=300, bbox_inches="tight")
    plt.close()

def show_graph_in_map(G, pos, filename):
    mapa = folium.Map(
        location=[41.38246354510279, 2.1472665793524985],
        zoom_start=14
    )
    for u, v, data in G.edges(data=True):
        edge_id = data.get("id")
        if edge_id is None:
            continue
        node_u = G.nodes[u]
        node_v = G.nodes[v]
        folium.PolyLine(
            locations=[
                [node_u["y"], node_u["x"]],  # lat, lon
                [node_v["y"], node_v["x"]],
            ],
            color="#000000",
        ).add_to(mapa)
    mapa.save(filename)


"""
edges, junctions = get_points_in_area(
    "hospital_clinic/hospital_clinic.kml", 
    "hospital_clinic/osm.net_BARCELONA.xml"
)

G, pos, colors, edges, junctions = create_graph(edges, junctions)

#draw_graph(G, pos, colors, "hospital_clinic_graph")

show_graph_in_map(G, pos, "mapa_clinic")
"""