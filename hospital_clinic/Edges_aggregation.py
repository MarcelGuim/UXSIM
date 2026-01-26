import json
import networkx as nx
import pandas as pd
from collections import defaultdict
from graph_creator import *
from uxsim import *
import pandas as pd
from IPython.display import display
import time
import statistics as statis
#from coordinates_treatment import *
import random
from collections import defaultdict
from file_parser import *


edges, junctions = get_points_in_area(
    "hospital_clinic/hospital_clinic.kml", 
    "hospital_clinic/osm.net_BARCELONA.xml"
)

G, pos, colors, edges, junctions = create_graph(edges, junctions)

def build_edge_adjacency(G):
    edge_next = defaultdict(list)
    edge_prev = defaultdict(list)
    for u, v, data in G.edges(data=True):
        e_id = data.get("id")
        if e_id is None:
            continue
        e_id = str(e_id)
        for _, w, d2 in G.out_edges(v, data=True):
            nxt = d2.get("id")
            if nxt is not None:
                nxt = str(nxt)
                edge_next[e_id].append(nxt)
                edge_prev[nxt].append(e_id)
    return dict(edge_next), dict(edge_prev)

def load_edge_geometry(edges_parquet):
    df = pd.read_parquet(edges_parquet)
    df["id"] = df["id"].astype(str)
    return {
        row.id: {
            "x_origin": row.inc_x,
            "y_origin": row.inc_y,
            "x_dest": row.out_x,
            "y_dest": row.out_y,
        }
        for _, row in df.iterrows()
    }

def build_full_disjoint_edge_aggregations(edge_next, edge_geom, max_len):
    used = set()
    chains = []

    for edge in edge_geom.keys():
        if edge in used:
            continue

        chain = [edge]
        used.add(edge)
        current = edge

        while len(chain) < max_len:
            candidates = [
                e for e in edge_next.get(current, [])
                if e not in used and e in edge_geom
            ]
            if not candidates:
                break
            nxt = candidates[0]
            chain.append(nxt)
            used.add(nxt)
            current = nxt

        chains.append(chain)

    return chains

def build_edge_aggregation_dict(chains, edge_geom):
    aggregation = {}
    counter = 1

    for chain in chains:
        edges_geometry = []
        for edge_id in chain:
            geom = edge_geom[edge_id]
            edges_geometry.append({
                "edge_id": edge_id,
                "x_origin": geom["x_origin"],
                "y_origin": geom["y_origin"],
                "x_dest": geom["x_dest"],
                "y_dest": geom["y_dest"],
            })

        aggregation[f"edge_aggregation_{counter}"] = {
            "list_of_edges": chain,
            "edges_geometry": edges_geometry
        }
        counter += 1

    return aggregation

def export_disjoint_edge_aggregations_to_json(G, edges_parquet, output_json):
    edge_next, _ = build_edge_adjacency(G)
    edge_geom = load_edge_geometry(edges_parquet)

    chains = build_full_disjoint_edge_aggregations(
        edge_next=edge_next,
        edge_geom=edge_geom,
        max_len=15
    )

    aggregation = build_edge_aggregation_dict(chains, edge_geom)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(aggregation, f, indent=2)

    print(f"✔ Saved {len(aggregation)} edge aggregations to {output_json}")

export_disjoint_edge_aggregations_to_json(
    G=G,
    edges_parquet="hospital_clinic/edges_hospital_clinic.parquet",
    output_json="hospital_clinic/edges_hospital_clinic_LEN15.json"
)