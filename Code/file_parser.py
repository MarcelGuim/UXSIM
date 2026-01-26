import xml.etree.ElementTree as ET
import networkx as nx
import matplotlib.pyplot as plt
import time
import random
import numpy as np
import matplotlib as mpl
import sumolib
from pykml import parser
from shapely.geometry import Point, Polygon


class EdgeClass:
    def __init__(self,id, lanes, length, speed, outgoing_edges, incoming_edges, vehicle_speed, number_of_vehicles=0):
        self.id = id
        self.lanes = lanes
        self.length = length
        self.speed = speed
        self.outgoing_edges = outgoing_edges
        self.incoming_edges = incoming_edges
        self._vehicle_speed = vehicle_speed
        self._number_of_vehicles = number_of_vehicles
        self._density = self._update_density()

    @property
    def number_of_vehicles(self):
        return self._number_of_vehicles

    @number_of_vehicles.setter
    def number_of_vehicles(self, value):
        self._number_of_vehicles = value
        self._density = self._update_density()

    @property
    def vehicle_speed(self):
        return self._vehicle_speed

    @vehicle_speed.setter
    def vehicle_speed(self, value):
        self._vehicle_speed = value

    @property
    def density(self):
        return self._density

    def _update_density(self):
        return float(self._number_of_vehicles)/(float(self.lanes)*float(self.length)*3.5) if float(self.lanes)*float(self.length)*3.5 != 0 else 0

    def as_dict(self):
        return {"id": self.id, "lanes": self.lanes, "length": self.length, "speed": self.speed, "outgoing_edges": self.outgoing_edges, "incoming_edges": self.incoming_edges, "vehicle_speed": self.vehicle_speed, "number_of_vehicles": self._number_of_vehicles, "density": self._density}
    
    def get_data(self):
        return [self.lanes, self.length, self.speed, self.outgoing_edges, self.incoming_edges, self.vehicle_speed, self._number_of_vehicles, self._density]    

class JunctionClass:
    def __init__(self,id, incoming, has_tls, x, y):
        self.id = id
        self.incoming = incoming
        self.has_tls = has_tls
        self.x = x
        self.y = y
    def get_data(self):
        return [self.id, self.incoming, self.has_tls, self.x, self.y]

def edges_junctions_getter(filename):
    #This function obtains all the edges and junctions from an hmtl file parsed as a SUMO file.
    net = sumolib.net.readNet(filename)
    
    tree = ET.parse(filename)
    root = tree.getroot()
    root.tag
    root.attrib

    edges = {}
    for edge in root.findall('edge'):
        try:
            function =  edge.attrib['function']
        except KeyError:
            edge_data = edge.attrib.copy()
            lane_data = []
            i = 0
            for lane in edge.findall('lane'):
                lane_data = lane.attrib.copy()
                i += 1
            
            edge = EdgeClass(edge_data['id'], i, lane_data['length'], lane_data['speed'], edge_data['to'], edge_data['from'],8.33, 15)
            edges[edge_data['id']] = edge

    junctions = {}
    for junction in root.findall('junction'):
        id = junction.attrib['id']
        type = junction.attrib['type']
        incoming_lanes = junction.attrib['incLanes'].split()
        incoming_edges = []
        has_tls = 0
        x,y = net.convertXY2LonLat(float(junction.attrib['x']), float(junction.attrib['y']))
        if x == 0 or y == 0:
            print("Error in junction coordinates")
        for i in incoming_lanes:
            if i[:-2] not in incoming_edges:
                incoming_edges.append(i[:-2])
        if type == "traffic_light":
            has_tls = 1
        if type != "internal":
            junction = JunctionClass(id, incoming_edges, has_tls, x, y)
            junctions[id] = junction

    return edges, junctions

def parse_klm_file(filename):
    #This function will return the coordinates of a single polygon from a kml in the google earth format
    with open(filename, 'r', encoding="utf-8") as f:
        root = parser.parse(f).getroot()
        coordinates = root.Document.Placemark.LineString.coordinates.text.strip()
        coords = []
        for coord in coordinates.split(",0 "):
            value = coord.split(",")
            coords.append([float(value[0]), float(value[1])])
    return coords
        
def get_points_in_area(area_definition_klm, points_to_check):
    #This function will return all the edges and junctions contained in the second parameter, that fit in the polygon defined in the first parameter. The result is ready to be entered in a graph creator and obtain the correponding graph.

    polygon_coords = parse_klm_file(area_definition_klm)

    polygon = Polygon(polygon_coords)
    edges, junctions = edges_junctions_getter(points_to_check)
    
    junctionsInArea = {}
    for junction in junctions.values():
        lon = junction.x
        lat = junction.y
        point = Point(lon,lat)
        if point.within(polygon):
            junctionsInArea[junction.id] = junction
    junctionIDs = [j.id for j in junctionsInArea.values()]
    edgesInArea = {}
    for e in edges.values():
        if e.incoming_edges in junctionIDs and e.outgoing_edges in junctionIDs:
            edgesInArea[e.id] = e
    return edgesInArea, junctionsInArea



### From this point forward functions are deprecated, please refer to the graph_creator file for new versions ###
"""
def create_graph(filename):
#This function is deprecated, please use the functions edges_junctions_getter to obtain edges and junctions and the function create graph from graph_creator to create the graph from these junctions and edges.

    net = sumolib.net.readNet(filename)
    
    tree = ET.parse(filename)
    root = tree.getroot()
    root.tag
    root.attrib


    edges = {}
    for edge in root.findall('edge'):
        try:
            function =  edge.attrib['function']
        except KeyError:
            edge_data = edge.attrib.copy()
            lane_data = []
            i = 0
            for lane in edge.findall('lane'):
                lane_data = lane.attrib.copy()
                i += 1
            
            edge = EdgeClass(edge_data['id'], i, lane_data['length'], lane_data['speed'], edge_data['to'], edge_data['from'],8.33, 15)
            edges[edge_data['id']] = edge

    junctions = {}
    for junction in root.findall('junction'):
        id = junction.attrib['id']
        type = junction.attrib['type']
        incoming_lanes = junction.attrib['incLanes'].split()
        incoming_edges = []
        has_tls = 0
        x,y = net.convertXY2LonLat(float(junction.attrib['x']), float(junction.attrib['y']))
        if x == 0 or y == 0:
            print("Error in junction coordinates")
        for i in incoming_lanes:
            if i[:-2] not in incoming_edges:
                incoming_edges.append(i[:-2])
        if type == "traffic_light":
            has_tls = 1
        if type != "internal":
            junction = JunctionClass(id, incoming_edges, has_tls, x, y)
            junctions[id] = junction

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

    #This part of the code removes nodes that have just one incoming and one outgoing edges, they are the nodes that SUMO enters to represents
    #changes in between roads or other reasons. They would appear as two separete roads when they are just one, to avoid problems, they are removed
    #ATENTION!!!!!!!!!!!!!!!!
    #This does not remove the nodes that have bidirectional edges just one of each, it would be the same scenario as before, but these can't be eliminated
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


    #This part of the code removes the nodes that have just one incoming edge but no outgoing edge (the ones at represent a dead end) 
    #This is so that the future model avoids dead ends.
    nodes_to_remove = [n for n, d in G.nodes(data=True) if len(list(G.neighbors(n))) == 0]
    G.remove_nodes_from(nodes_to_remove)

    pos = {j.id: (float(j.x), float(j.y)) for j in junctions.values()}
    colors = [d["color"] for _, d in G.nodes(data=True)]
    return G, pos, colors, edges, junctions

def draw_graph(G, pos, colors):
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
    plt.show()

def update_edge_vehicles_by_id(G, edge_id, new_value, edges):
    try:
        edge_obj = edges[edge_id]
        edge_obj.number_of_vehicles = new_value
        G[edge_obj.incoming_edges][edge_obj.outgoing_edges].update(edge_obj.as_dict())
        return True
    except:
        return False

def update_edge_vehicles_speed_by_id(G, edge_id, new_value, edges):
    try:
        edge_obj = edges[edge_id]
        edge_obj.vehicle_speed = new_value
        G[edge_obj.incoming_edges][edge_obj.outgoing_edges].update(edge_obj.as_dict())
        return True
    except:
        return False
"""