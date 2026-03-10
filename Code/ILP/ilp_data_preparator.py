import json
import networkx as nx
from collections import defaultdict
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
#from graph_creator import *
from file_parser import *
import pandas
from shapely.geometry import Point, Polygon
from shapely import wkt
import matplotlib.pyplot as plt
import folium
import geopandas as gpd
import branca.colormap as cm
import pandas as pd
import numpy as np
from shapely import wkt

origin_nodes = [
    "30237873",
    "30295271",
    "876375351",
    "1295283770"
]

def get_edges():
    edges_inbound = []
    edges_outbound = []
    nodes_inbound = []
    nodes_outbound = []
    endpoints_inbound = []
    endpoints_outbound = []
    hospitals = []
    with open("ILP/data/inbound_edges.json", "r", encoding="utf-8") as f:
        edges_inbound = json.load(f)
    with open("ILP/data/outbound_edges.json", "r", encoding="utf-8") as f:
        edges_outbound = json.load(f)
    with open("ILP/data//inbound_nodes.json", "r", encoding="utf-8") as f:
        nodes_inbound = json.load(f)
    with open("ILP/data//outbound_nodes.json", "r", encoding="utf-8") as f:
        nodes_outbound = json.load(f)
    with open("ILP/data/inbound_leaves.json", "r", encoding="utf-8") as f:
        endpoints_inbound = json.load(f)
        hospitals = endpoints_inbound["origin_nodes"]
        endpoints_inbound = endpoints_inbound["entry_root_nodes"]
    with open("ILP/data/outbound_leaves.json", "r", encoding="utf-8") as f:
        endpoints_outbound = json.load(f)
        endpoints_outbound = endpoints_outbound["dead_end_leaves"]
    return edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals

def get_edges_dict():
    with open("ILP/data/inbound_edges_dict.json", "r", encoding="utf-8") as f:
        edges_inbound = json.load(f)

    with open("ILP/data/outbound_edges_dict.json", "r", encoding="utf-8") as f:
        edges_outbound = json.load(f)

    with open("ILP/data/inbound_nodes_dict.json", "r", encoding="utf-8") as f:
        nodes_inbound = json.load(f)

    with open("ILP/data/outbound_nodes_dict.json", "r", encoding="utf-8") as f:
        nodes_outbound = json.load(f)

    with open("ILP/data/inbound_leaves.json", "r", encoding="utf-8") as f:
        inbound_data = json.load(f)
        hospitals = inbound_data["origin_nodes"]
        endpoints_inbound = inbound_data["entry_root_nodes"]

    with open("ILP/data/outbound_leaves.json", "r", encoding="utf-8") as f:
        outbound_data = json.load(f)
        endpoints_outbound = outbound_data["dead_end_leaves"]

    return edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals

def convert_to_dict(edges, nodes):
    edges_dict = {}
    for e in edges:
        edges_dict[e["id"]] = e
    
    nodes_dict = {}
    for n in nodes:
        nodes_dict[n["id"]] = n
    #nodes_dict = {n['id']: JunctionClass(**n) for n in nodes}


    return edges_dict, nodes_dict

def create_graph(edges, nodes):
    G = nx.DiGraph()
    nodes_with_edge = []
    nodes_with_no_edge = []
    for key, e in edges.items():
        G.add_edge(e["incoming_edges"], e["outgoing_edges"], **e)
        if e["incoming_edges"] not in nodes_with_edge:
            nodes_with_edge.append(e["incoming_edges"])
        elif e["outgoing_edges"] not in nodes_with_edge:
            nodes_with_edge.append(e["outgoing_edges"])
    for key, n in nodes.items():
        if key in nodes_with_edge:
            G.add_node(n["id"], x = n["x"], y = n["y"])
        else:
            nodes_with_no_edge.append(n["id"])
    return G

def check_routes(edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals):
    G = create_graph(edges_inbound, nodes_inbound)
    endpoints_with_no_path = []
    hospital_nodes = [n["id"] for n in hospitals]
    for n in endpoints_inbound:
        for h in hospital_nodes:
            if not nx.has_path(G, n["id"], h):
                endpoints_with_no_path.append(n["id"])

    G = create_graph(edges_outbound, nodes_outbound)
    for n in endpoints_outbound:
        for h in hospital_nodes:
            if not nx.has_path(G, h, n["id"]):
                endpoints_with_no_path.append(n["id"])

    print(len(endpoints_with_no_path))

def get_routes(edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals):
    G = create_graph(edges_inbound, nodes_inbound)
    hospital_nodes = [n["id"] for n in hospitals]
    routes_inbound_nodes = []
    routes_inbound_edges = []
    for n in endpoints_inbound:
        short_route = None
        for h in hospital_nodes:
            if nx.has_path(G, n["id"], h):
                path = nx.shortest_path(G, n["id"], h)
                if short_route == None or len(path) < len(short_route):
                    short_route = path
        edge_ids = [
            G[u][v]["id"] for u, v in zip(short_route[:-1], short_route[1:])
        ]
        routes_inbound_edges.append(edge_ids)
        routes_inbound_nodes.append(short_route)

    G = create_graph(edges_outbound, nodes_outbound)
    routes_outbound_nodes = []
    routes_outbound_edges = []
    for n in endpoints_outbound:
        short_route = None
        for h in hospital_nodes:
            if nx.has_path(G, h, n["id"]):
                path = nx.shortest_path(G, h, n["id"])
                if short_route == None or len(path) < len(short_route):
                    short_route = path
        edge_ids = [
            G[u][v]["id"] for u, v in zip(short_route[:-1], short_route[1:])
        ]
        routes_outbound_edges.append(edge_ids)
        routes_outbound_nodes.append(short_route)

    with open("ILP/data/routes_inbound_edges.json", "w", encoding="utf-8") as f:
        json.dump(routes_inbound_edges, f, indent = 4, default = str)

    with open("ILP/data/routes_inbound_nodes.json", "w", encoding="utf-8") as f:
        json.dump(routes_inbound_nodes, f, indent = 4, default = str)

    with open("ILP/data/routes_outbound_edges.json", "w", encoding="utf-8") as f:
        json.dump(routes_outbound_edges, f, indent = 4, default = str)

    with open("ILP/data/routes_outbound_nodes.json", "w", encoding="utf-8") as f:
        json.dump(routes_outbound_nodes, f, indent = 4, default = str)

def get_nodes_in_abs(nodes_inbound, nodes_outbound):
    df = pd.read_csv("ILP/poblacio_abs/arees_basiques_de_salut_20260210_def.csv", sep=",")    
    abs_polygons = []
    for index, row in df.iterrows():
        multipolygon = row["Geometry"]
        geom = wkt.loads(multipolygon)
        if geom.geom_type == "MultiPolygon":
            polygons = list(geom.geoms)
        else:
            polygons = [geom]
        abs_polygons.append([row["Codi"], polygons])
    ids = []
    nodes_with_no_abs_inbound = []
    for key, n in nodes_inbound.items():
        node_lonlat = [n["x"],n["y"]]
        point = Point(node_lonlat)
        found = False
        for ap in abs_polygons:
            for p in ap[1]:
                if point.within(p):
                    n["abs"] = ap[0]
                    ids.append(n["id"])
                    found = True
                    break
            if found:
                break
        if not found:
            nodes_with_no_abs_inbound.append([n["id"],node_lonlat])
    nodes_with_no_abs_outbound = []
    for key, n in nodes_outbound.items():
        node_lonlat = [n["x"],n["y"]]
        point = Point(node_lonlat)
        found = False
        for ap in abs_polygons:
            for p in ap[1]:
                if point.within(p):
                    n["abs"] = ap[0]
                    found = True
                    break
            if found:
                break
        if not found:
            nodes_with_no_abs_outbound.append([n["id"],node_lonlat])
    
    print(f"Nodes inbound with no ABS: {len(nodes_with_no_abs_inbound)}")
    print(f"Nodes outbound with no ABS: {len(nodes_with_no_abs_outbound)}")
    with open("ILP/to_fix/inbound_nodes_with_no_abs.json", "w") as f:
        json.dump(nodes_with_no_abs_inbound, f, indent=2)
    with open("ILP/to_fix/outbound_nodes_with_no_abs.json", "w") as f:
        json.dump(nodes_with_no_abs_outbound, f, indent=2)    
    with open("ILP/data/inbound_nodes_dict.json", "w") as f:
        json.dump(nodes_inbound, f, indent=2)
    with open("ILP/data/outbound_nodes_dict.json", "w") as f:
        json.dump(nodes_outbound, f, indent=2)

def get_populatuion_of_node(nodes_inbound, nodes_outbound):
    pop_df = pd.read_csv("ILP/poblacio_abs/Taula_estadistica_poblacio.csv")
    filtered_df = pop_df[pop_df["Tipus de territori"] == "Barri"]
    population_lookup = dict(zip(filtered_df["Territori"], filtered_df["01 Oct. 2025"]))
    
    df = pd.read_csv("ILP/poblacio_abs/BarcelonaCiutat_Barris.csv", sep=",")    
    barris_polygons = []
    for index, row in df.iterrows():
        multipolygon = row["geometria_wgs84"]
        geom = wkt.loads(multipolygon)
        if geom.geom_type == "MultiPolygon":
            polygons = list(geom.geoms)
        else:
            polygons = [geom]
        barris_polygons.append([row["nom_barri"], polygons])
    
    barri_node_map_inbound = {}

    for node in nodes_inbound.values():
        point = Point(node["x"], node["y"])
        for barri_name, polygons in barris_polygons:
            for p in polygons:
                if point.within(p):
                    barri_node_map_inbound.setdefault(barri_name, []).append(node["id"])
                    node["barri"] = barri_name
                    break
            else:
                continue
            break
    
    barri_node_map_outbound = {}
  
    for node in nodes_outbound.values():
        point = Point(node["x"], node["y"])
        for barri_name, polygons in barris_polygons:
            for p in polygons:
                if point.within(p):
                    barri_node_map_outbound.setdefault(barri_name, []).append(node["id"])
                    node["barri"] = barri_name
                    break
            else:
                continue
            break
    nodes_inbound_not_data = []
    for node in nodes_inbound.values():
        try:
            barri = node["barri"]
            population = population_lookup[barri]
            number_of_nodes = len(barri_node_map_inbound[barri])
            node["population"] = float(population)/float(number_of_nodes)
        except:
            id = node["id"]
            lonlat = node["x"], node["y"]
            nodes_inbound_not_data.append([id,lonlat])

    nodes_outbound_no_data = []
    for node in nodes_outbound.values():
        if node["id"] == "308672498":
            print("found")
        try:
            barri = node["barri"]
            population = population_lookup[barri]
            number_of_nodes = len(barri_node_map_outbound[barri])
            node["population"] = float(population)/float(number_of_nodes)
        except Exception as e:
            print(f"Error {e}")
            id = node["id"]
            lonlat = node["x"], node["y"]
            nodes_outbound_no_data.append([id,lonlat])            

    print(f"Nodes inbound with no nieghbourhood: {len(nodes_inbound_not_data)}")
    print(f"Nodes outbound with no nieghbourhood: {len(nodes_outbound_no_data)}")
    with open("ILP/to_fix/inbound_nodes_with_no_nieghbourhood.json", "w") as f:
        json.dump(nodes_inbound_not_data, f, indent=2)
    with open("ILP/to_fix/outbound_nodes_with_no_nieghbourhood.json", "w") as f:
        json.dump(nodes_outbound_no_data, f, indent=2)    
    with open("ILP/data/inbound_nodes_dict_population.json", "w") as f:
        json.dump(nodes_inbound, f, indent=4, ensure_ascii=False)
    with open("ILP/data/outbound_nodes_dict_population.json", "w") as f:
        json.dump(nodes_outbound, f, indent=4, ensure_ascii=False)

def plot_choropleth_folium(
    df_map_merged,
    count_col: str = "Count",
    title: str = "Map",
    name_col: str = "Nom",
) -> folium.Map:
    """
    Generates a Folium interactive map with geometries filled from
    black (low count) to light gray (high count).

    Parameters
    ----------
    df_map_merged : GeoDataFrame or DataFrame
        Must have a 'Geometry' column (WKT string or shapely geometry),
        a name column (default: 'Nom'), and a count column.
    count_col : str
        Name of the column containing the count values.
    title : str
        Title shown as a map overlay.
    name_col : str
        Column used for tooltip labels.

    Returns
    -------
    m : folium.Map
    """
    df = df_map_merged.copy()

    # --- Parse geometry -------------------------------------------------
    if not isinstance(df, gpd.GeoDataFrame):
        if "Geometry" in df.columns:
            df["geometry"] = df["Geometry"].apply(
                lambda g: wkt.loads(g) if isinstance(g, str) else g
            )
        gdf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:4326")
    else:
        gdf = df.copy()
        if "Geometry" in gdf.columns and gdf.geometry.name != "Geometry":
            gdf["geometry"] = gdf["Geometry"].apply(
                lambda g: wkt.loads(g) if isinstance(g, str) else g
            )
            gdf = gdf.set_geometry("geometry")

    # Ensure CRS is WGS84 (required by Folium)
    if gdf.crs and gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    # --- Count column ---------------------------------------------------
    gdf[count_col] = pd.to_numeric(gdf[count_col], errors="coerce").fillna(0)

    vmin = gdf[count_col].min()
    vmax = gdf[count_col].max()

    # --- Color interpolation: black → light gray ------------------------
    def count_to_hex(value):
        if vmax == vmin:
            t = 0.0
        else:
            t = (value - vmin) / (vmax - vmin)
        # black = (0,0,0)  →  light gray = (211,211,211)
        t = 1-t
        r = int(0 + t * 211)
        g = int(0 + t * 211)
        b = int(0 + t * 211)
        return f"#{r:02x}{g:02x}{b:02x}"

    gdf["_color"] = gdf[count_col].apply(count_to_hex)

    # --- Build map centred on the data ----------------------------------
    bounds = gdf.total_bounds  # (minx, miny, maxx, maxy)
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=14 
        )

    # --- Draw each polygon ----------------------------------------------
    for _, row in gdf.iterrows():
        geojson_geom = json.loads(gpd.GeoSeries([row.geometry]).to_json())
        color = row["_color"]
        count_val = row[count_col]
        name_val = row.get(name_col, "")

        folium.GeoJson(
            geojson_geom,
            style_function=lambda feature, c=color: {
                "fillColor": c,
                "color": "#ffffff",       # white border
                "weight": 0.8,
                "fillOpacity": 0.85,
            },
            tooltip=folium.Tooltip(
                f"<b>{name_val}</b><br>{count_col}: {int(count_val)}"
            ),
        ).add_to(m)

    # --- Legend (HTML overlay) ------------------------------------------
    legend_html = f"""
    <div style="
        position: fixed;
        bottom: 40px; right: 40px;
        background: rgba(20,20,20,0.85);
        border: 1px solid #555;
        border-radius: 8px;
        padding: 14px 18px;
        font-family: Arial, sans-serif;
        color: white;
        z-index: 9999;
        min-width: 160px;
    ">
        <b style="font-size:13px;">{title}</b><br>
        <b style="font-size:11px; color:#aaa;">{count_col}</b>
        <div style="margin-top:8px; display:flex; align-items:center; gap:8px;">
            <div style="
                width: 120px; height: 16px;
                background: linear-gradient(to right, #d3d3d3, #000000);
                border-radius: 3px;
                border: 1px solid #666;
            "></div>
        </div>
        <div style="display:flex; justify-content:space-between; width:120px; font-size:10px; color:#ccc; margin-top:3px;">
            <span>{int(vmin)}</span>
            <span>{int(vmax)}</span>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # --- Title overlay --------------------------------------------------
    title_html = f"""
    <div style="
        position: fixed;
        top: 16px; left: 50%; transform: translateX(-50%);
        background: rgba(20,20,20,0.8);
        border: 1px solid #555;
        border-radius: 6px;
        padding: 8px 20px;
        font-family: Arial, sans-serif;
        font-size: 15px;
        font-weight: bold;
        color: white;
        z-index: 9999;
    ">{title}</div>
    """
    m.get_root().html.add_child(folium.Element(title_html))

    return m

def clean_text(s):
    return (
        str(s)
        .replace("\xa0", " ")   # remove NBSP
        .strip()
        .upper()
    )

def get_emergency_in_Barcelona(filename):
    columns = [
        "Núm Incidents", "Dia Alerta", "Hora Alerta", "ABS",
        "Municipi", "Destí Intervenció",
        "Temps Activacio (seg.)", "Temps alerta-assignació (seg.)",
        "Temps Total Gestió (seg.)", "Temps resposta intervenció (seg.)",
        "Temps assistència (seg.)", "Temps transport (seg.)",
        "Temps arribada hos- final intv (seg.)",
        "Temps alerta-final interven"
    ]

    df_barcelona = pd.read_csv(filename, 
                                sep=";", 
                                usecols=columns,
                                dtype={"Municipi": "category", 
                                       "ABS": "category", 
                                       "Destí Intervenció":"category"},
                                na_values=["", "NA", "N/A", "-", "--", "N/D"]
    ).query('Municipi == "Barcelona"')
    df_barcelona["ABS"] = df_barcelona["ABS"].cat.remove_unused_categories()
    df_barcelona["ABS"] = df_barcelona["ABS"].apply(clean_text)
    time_cols = [col for col in df_barcelona.columns if "(seg.)" in col]
    time_cols.append("Temps alerta-final interven")
    df_barcelona[time_cols] = df_barcelona[time_cols].apply(
        pd.to_numeric,
        errors="coerce"
    )

    df_barcelona["Dia Alerta"] = pd.to_datetime(
        df_barcelona["Dia Alerta"],
        errors="coerce"
    )
    df_barcelona["Hora Alerta"] = pd.to_datetime(
        df_barcelona["Hora Alerta"],
        format="%H:%M:%S",
        errors="coerce"
    )
    df_barcelona["Weekday_Num"] = df_barcelona["Dia Alerta"].dt.weekday
    df_barcelona["Weekday_Name"] = df_barcelona["Dia Alerta"].dt.day_name()
    df_barcelona["Hour"] = df_barcelona["Hora Alerta"].dt.hour

    df_barcelona = df_barcelona.sort_values("Dia Alerta")

    df_barcelona["Year"] = df_barcelona["Dia Alerta"].dt.year
    df_barcelona["Month"] = df_barcelona["Dia Alerta"].dt.month
    dfs_by_year = {
        year: data
        for year, data in df_barcelona.groupby("Year")
        }
    #region Get map of accidents concentration
    compute = False
    if compute:
        df_map = pd.read_csv("poblacio_abs/arees_basiques_de_salut_20260210.csv")
        df_week_day = df_barcelona[df_barcelona["Weekday_Num"] < 5]
        df_weekend = df_barcelona[df_barcelona["Weekday_Num"] > 4]
        df_between_hours = df_week_day[(df_week_day["Hour"] > 7) & (df_week_day["Hour"] < 20)]
        df_after_hours = df_week_day[(df_week_day["Hour"] < 8) | (df_week_day["Hour"] > 19)]
        count_weekend = df_weekend["ABS"].value_counts().sort_index(ascending=True)  
        count_between_hours = df_between_hours["ABS"].value_counts().sort_index(ascending=True)  
        count_after_hours = df_after_hours["ABS"].value_counts().sort_index(ascending=True)  
        count_weekend_df = count_weekend.reset_index()
        count_weekend_df.columns = ["Nom", "Count"]
        count_between_hours_df = count_between_hours.reset_index()
        count_between_hours_df.columns = ["Nom", "Count"]
        count_after_hours_df = count_after_hours.reset_index()
        count_after_hours_df.columns = ["Nom", "Count"]
        count_weekend_df["Nom"] = (
            count_weekend_df["Nom"]
            .astype(str)
            .str.strip()
            .str.upper()
        )
        count_between_hours_df["Nom"] = (
            count_between_hours_df["Nom"]
            .astype(str)
            .str.strip()
            .str.upper()
        )
        count_after_hours_df["Nom"] = (
            count_after_hours_df["Nom"]
            .astype(str)
            .str.strip()
            .str.upper()
        )
        df_map["Nom"] = (
            df_map["Nom"]
            .astype(str)
            .str.strip()
            .str.upper()
        )
       
        df_map = df_map.sort_values("Nom")
        df_map_weekend = df_map.merge(count_weekend_df, on="Nom", how="left")
        df_map_between = df_map.merge(count_between_hours_df, on="Nom", how="left")
        df_map_after = df_map.merge(count_after_hours_df, on="Nom", how="left")
        total = df_map_weekend["Count"].sum()
        print("Total:", total)
        total = df_map_between["Count"].sum()
        print("Total:", total)
        total = df_map_after["Count"].sum()
        print("Total:", total)

        # ── Usage ────────────────────────────────────────────────────────────────────
        m = plot_choropleth_folium(df_map_weekend,  count_col="Count", title="Weekend Activity")
        m.save("map_weekend.html")
        m = plot_choropleth_folium(df_map_between,  count_col="Count", title="Between Hours")
        m.save("map_between.html")
        m = plot_choropleth_folium(df_map_after,    count_col="Count", title="After Hours")
        m.save("map_after.html")

    #endregion

    #region Get number of accidents for each ABS
    compute = False
    if compute:
        df_week_day = df_barcelona[df_barcelona["Weekday_Num"] < 5]
        df_between_hours = df_week_day[(df_week_day["Hour"] > 7) & (df_week_day["Hour"] < 20)]
        df_after_hours = df_week_day[(df_week_day["Hour"] < 6) | (df_week_day["Hour"] > 19)]
        percentages_between_hours = df_between_hours["ABS"].value_counts(normalize=True) * 100
        percentages_after_hours = df_after_hours["ABS"].value_counts(normalize=True) * 100
        counts_between_hours = df_between_hours["ABS"].value_counts(normalize=False)
        counts_after_hours = df_after_hours["ABS"].value_counts(normalize=False)

        after_hours_data = pd.concat(
            [counts_after_hours, percentages_after_hours],
            axis=1
        )
        after_hours_data.columns = ["Count", "percentage"]
        counts_after_dict = after_hours_data.to_dict(orient="index")
        
        between_hours_data = pd.concat(
            [counts_between_hours, percentages_between_hours],
            axis=1
        )
        between_hours_data.columns = ["Count", "percentage"]

        counts_between_dict = between_hours_data.to_dict(orient="index")
        
        with open("counts_between_hours.json", "w") as f:
            json.dump(counts_between_dict, f, indent=4)

        with open("counts_after_hours.json", "w") as f:
            json.dump(counts_after_dict, f, indent=4)

        top_n = 20
        fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(14,10))
        percentages_between_hours.head(top_n).plot(
            kind="bar",
            ax=axes[0],
            color="skyblue"
        )
        axes[0].set_ylabel("Percentage of Total (%)")
        axes[0].set_title(f"Top {top_n} ABS in Barcelona (Weekdays, 7-20h)")
        axes[0].tick_params(axis='x', rotation=45)

        percentages_after_hours.head(top_n).plot(
            kind="bar",
            ax=axes[1],
            color="orange"
        )
        axes[1].set_ylabel("Percentage of Total (%)")
        axes[1].set_title(f"Top {top_n} ABS in Barcelona (Weekdays, Before 7h / After 20h)")
        axes[1].tick_params(axis='x', rotation=45)

        plt.tight_layout()
        plt.savefig(f"file_all_years.png")    
    #endregion

    #region Get plot of % of incidences in each ABS
    compute = False
    if compute:
        for key, df in dfs_by_year.items():
            df_week_day = df[df["Weekday_Num"] < 5]
            df_between_hours = df_week_day[(df_week_day["Hour"] > 7) & (df_week_day["Hour"] < 20)]
            df_after_hours = df_week_day[(df_week_day["Hour"] < 6) | (df_week_day["Hour"] > 19)]
            percentages_between_hours = df_between_hours["ABS"].value_counts(normalize=True) * 100
            percentages_after_hours = df_after_hours["ABS"].value_counts(normalize=True) * 100
            top_n = 20
            fig, axes = plt.subplots(nrows=2, ncols=1, figsize=(14,10))
            percentages_between_hours.head(top_n).plot(
                kind="bar",
                ax=axes[0],
                color="skyblue"
            )
            axes[0].set_ylabel("Percentage of Total (%)")
            axes[0].set_title(f"Top {top_n} ABS in Barcelona (Weekdays, 7-20h)")
            axes[0].tick_params(axis='x', rotation=45)

            percentages_after_hours.head(top_n).plot(
                kind="bar",
                ax=axes[1],
                color="orange"
            )
            axes[1].set_ylabel("Percentage of Total (%)")
            axes[1].set_title(f"Top {top_n} ABS in Barcelona (Weekdays, Before 7h / After 20h)")
            axes[1].tick_params(axis='x', rotation=45)

            plt.tight_layout()
            plt.savefig(f"file_{key}.png")
    #endregion

    #region Get mean and variance through years
    compute = False
    if compute:
        for key, df in dfs_by_year.items():
            df_week_day = df[df["Weekday_Num"] < 5]
            df_between_hours = df_week_day[(df_week_day["Hour"] > 7) & (df_week_day["Hour"] < 11)]
            df_after_hours = df_week_day[(df_week_day["Hour"] < 6) | (df_week_day["Hour"] > 19)]
            mean_between_hours = df_between_hours["Temps transport (seg.)"].mean()
            variance_between_hours = df_between_hours["Temps transport (seg.)"].var()
            mean_after_hours = df_after_hours["Temps transport (seg.)"].mean()
            variance_after_hours = df_after_hours["Temps transport (seg.)"].var()

            print(key, mean_between_hours,variance_between_hours, mean_after_hours,variance_after_hours)
    #endregion

def load_and_count(filename: str) -> pd.DataFrame:
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    return (
        pd.DataFrame.from_dict(data, orient="index")
        .reset_index()
        .rename(columns={"index": "node_id"})
        .dropna(subset=["abs"])
    ), data

def get_accidents_per_node(filename_accidents_abs, filename_nodes_inbound_data, filename_nodes_outbound_data):
    df_nodes_inbound, nodes_inbound_json  = load_and_count(filename_nodes_inbound_data)
    df_nodes_outbound, nodes_outbound_json = load_and_count(filename_nodes_outbound_data)

    df_abs_counts = (
        df_nodes_inbound["abs"].value_counts().rename("count_inbound")
        .to_frame()
        .join(df_nodes_outbound["abs"].value_counts().rename("count_outbound"), how="outer")
        .rename_axis("Codi")
        .reset_index()
    )


    df_abs_info = pd.read_csv("ILP/poblacio_abs/arees_basiques_de_salut_20260210_def.csv")

    df_abs = (
        df_abs_info.merge(df_abs_counts, on="Codi", how="left")
        [["Codi", "Nom", "count_inbound", "count_outbound"]]
    )
    with open(filename_accidents_abs, "r", encoding="utf-8") as f:
        abs_accidents = json.load(f)

    df_abs_accidents = pd.DataFrame.from_dict(abs_accidents, orient="index")
    df_abs_accidents = df_abs_accidents.reset_index().rename(columns={"index": "Nom"})
    
    df_abs["Nom"] = df_abs["Nom"].str.upper()
    df_abs_accidents["Nom"] = df_abs_accidents["Nom"].str.upper()

    df_total_data = df_abs_accidents.merge(df_abs, on="Nom", how="left")
    df_total_data["node_inbound"] = df_total_data["Count"]/df_total_data["count_inbound"]
    df_total_data["node_outbound"] = df_total_data["Count"]/df_total_data["count_outbound"]

    df_total_data["Codi"] = df_total_data["Codi"].astype("Int64")  # nullable integer
    nodes_inbound_with_data = {}
    nodes_inbound_with_no_abs = []
    for key, val in nodes_inbound_json.items():
        try:
            abs = val["abs"]
            value = df_total_data.query(f'Codi == {abs}')
            if not value.empty:
                val["accidents"] = float(value["node_inbound"].iloc[0])
            nodes_inbound_with_data[key] = val
        except:
            nodes_inbound_with_no_abs.append(key)
            continue
    nodes_outbound_with_data = {}
    nodes_outbound_with_no_abs = []
    for key, val in nodes_outbound_json.items():
        try:
            abs = val["abs"]
            value = df_total_data.query(f'Codi == {abs}')
            if not value.empty:
                val["accidents"] = float(value["node_outbound"].iloc[0])
            nodes_outbound_with_data[key] = val
        except:
            nodes_outbound_with_no_abs.append(key)
            continue
    

    print(f"Nodes inbound with no accidents: {len(nodes_inbound_with_no_abs)}")
    print(f"Nodes outbound with no accidents: {len(nodes_outbound_with_no_abs)}")
    with open("ILP/to_fix/inbound_nodes_with_no_accidents.json", "w") as f:
        json.dump(nodes_inbound_with_no_abs, f, indent=2)
    with open("ILP/to_fix/outbound_nodes_with_no_accidents.json", "w") as f:
        json.dump(nodes_outbound_with_no_abs, f, indent=2)  

    with open("ILP/data/inbound_nodes_accidents_dict.json", "w", encoding="utf-8") as f:
        json.dump(nodes_inbound_with_data, f, indent = 4, default = str)
    
    with open("ILP/data/outbound_nodes_accidents_dict.json", "w", encoding="utf-8") as f:
        json.dump(nodes_outbound_with_data, f, indent = 4, default = str)

def get_routes_within_fences(filename_routes_inbound, filename_routes_outbound, filename_nodes_inbound, filename_nodes_outbound):
    #region Get data from JSON
    with open(filename_routes_inbound, "r", encoding="utf-8") as f:
        routes_inbound = json.load(f)
    with open(filename_routes_outbound, "r", encoding="utf-8") as f:
        routes_outbound = json.load(f)
    with open(filename_nodes_inbound, "r", encoding="utf-8") as f:
        nodes_inbound = json.load(f)
    with open(filename_nodes_outbound, "r", encoding="utf-8") as f:
        nodes_outbound = json.load(f)
    #endregion
    final_routes_inbound = []
    for route in routes_inbound:
        correct = True
        route_alt = []
        for n in route:
            if n in nodes_inbound:
                route_alt.append(n)
            else:
                correct = False
                #final_routes_inbound.append(route_alt)
                break
        if correct:
            final_routes_inbound.append(route)

    final_routes_outbound = []
    for route in routes_outbound:
        correct = True
        route_alt = []
        for n in route:
            if n in nodes_outbound:
                route_alt.append(n)
            else:
                correct = False
                #final_routes_outbound.append(route_alt)
                break
        if correct:
            final_routes_outbound.append(route)
    
    print(len(routes_inbound))
    print(len(final_routes_inbound))
    print(len(routes_outbound))
    print(len(final_routes_outbound))


    with open("ILP/data/final_routes_inbound.json", "w", encoding="utf-8") as f:
        json.dump(final_routes_inbound, f, indent = 4, default = str)
    with open("ILP/data/final_routes_outbound.json", "w", encoding="utf-8") as f:
        json.dump(final_routes_outbound, f, indent = 4, default = str)

def append_node_info_in_edge(node, edge):
    if node["abs"] not in edge["abs"]:
        edge["abs"].append(node["abs"])
    edge["population"] += float(node["population"])
    edge["accidents"] += float(node["accidents"])

def get_routes_within_parameters(filename_routes_inbound, filename_routes_outbound, filename_nodes_inbound, filename_nodes_outbound, filename_edges_inbound, filename_edges_outbound, filename_leaves_inbound, filename_leaves_outbound):
    #region Get data from JSON
    with open(filename_routes_inbound, "r", encoding="utf-8") as f:
        routes_inbound = json.load(f)
    with open(filename_routes_outbound, "r", encoding="utf-8") as f:
        routes_outbound = json.load(f)
    with open(filename_nodes_inbound, "r", encoding="utf-8") as f:
        nodes_inbound = json.load(f)
    with open(filename_nodes_outbound, "r", encoding="utf-8") as f:
        nodes_outbound = json.load(f)
    with open(filename_edges_inbound, "r", encoding="utf-8") as f:
        edges_inbound = json.load(f)
    with open(filename_edges_outbound, "r", encoding="utf-8") as f:
        edges_outbound = json.load(f)
    with open(filename_leaves_inbound, "r", encoding="utf-8") as f:
        leaves_inbound = json.load(f)
    with open(filename_leaves_outbound, "r", encoding="utf-8") as f:
        leaves_outbound = json.load(f)
    #endregion
    G_in = create_graph(edges_inbound, nodes_inbound)
    G_out = create_graph(edges_outbound, nodes_outbound)
    
    for key, n in nodes_inbound.items():
        try:   
            po = n["population"]
            abs = n["abs"]
            acc = n["accidents"]
        except:
            print(f"ATTENTION!!!!! There is a wrongly formated inbound node, key--> {key}")
        
    for key, n in nodes_outbound.items():
        try:   
            po = n["population"]
            abs = n["abs"]
            acc = n["accidents"]
        except:
            print(f"ATTENTION!!!!! There is a wrongly formated outbound node, key--> {key}")
    
    for key, e in edges_inbound.items():
        edges_inbound[key]["population"] = 0
        edges_inbound[key]["accidents"] = 0
        edges_inbound[key]["abs"] = []

    for key, e in edges_outbound.items():
        edges_outbound[key]["population"] = 0
        edges_outbound[key]["accidents"] = 0
        edges_outbound[key]["abs"] = []

    for route in routes_inbound:
        pairs = [list(pair) for pair in zip(route[:-1], route[1:])]
        nodes_in_route = []
        for p in pairs:
            edge_info = G_in.get_edge_data(p[0], p[1])
            edge = edges_inbound[edge_info["id"]]
            nodes_in_route.append(p[0])
            if edge["id"] == "238179161#0":
                print("found")
            for n in nodes_in_route:
                node = nodes_inbound[n]
                append_node_info_in_edge(node, edge)

    for route in routes_outbound:
        pairs = [list(pair) for pair in zip(route[:-1], route[1:])]
        nodes_in_route = []
        for p in pairs:
            edge_info = G_out.get_edge_data(p[0], p[1])
            edge = edges_outbound[edge_info["id"]]
            nodes_in_route.append(p[0])
            for n in nodes_in_route:
                node = nodes_outbound[n]
                append_node_info_in_edge(node, edge)

    with open("ILP/data/inbound_edges_with_info.json", "w", encoding="utf-8") as f:
        json.dump(edges_inbound, f, indent = 4, default = EdgeClass.json_serializer)

    with open("ILP/data/outbound_edges_with_info.json", "w", encoding="utf-8") as f:
        json.dump(edges_outbound, f, indent = 4, default = EdgeClass.json_serializer)

def get_nodes_in_area(filename_nodes_inbound, filename_nodes_outbound):
    with open(filename_nodes_inbound, "r", encoding="utf-8") as f:
        nodes_inbound = json.load(f)
    with open(filename_nodes_outbound, "r", encoding="utf-8") as f:
        nodes_outbound = json.load(f)
    
    final_inbound = {}
    non_final_inbound = []
    for key, n in nodes_inbound.items():
        try:
            pop = n["population"]
            abs = n["abs"]
            acc = n["accidents"]
            final_inbound[key] = n
        except:
            non_final_inbound.append(key)
            continue

    final_outbound = {}
    non_final_outbound = []
    for key, n in nodes_outbound.items():
        try:
            pop = n["population"]
            abs = n["abs"]
            acc = n["accidents"]
            final_outbound[key] = n
        except:
            non_final_outbound.append(key)
            continue
    print(len(nodes_inbound))
    print(len(final_inbound))
    print(len(nodes_outbound))
    print(len(final_outbound)) 
    with open("ILP/data/nodes_inbound_to_modify.json", "w", encoding="utf-8") as f:
        json.dump(non_final_inbound, f, indent = 4, default = str)
    with open("ILP/data/nodes_outbound_to_modify.json", "w", encoding="utf-8") as f:
        json.dump(non_final_outbound, f, indent = 4, default = str)
    """
    with open("ILP/data/nodes_inbound.json", "w", encoding="utf-8") as f:
        json.dump(final_inbound, f, indent = 4, default = str)
    with open("ILP/data/nodes_outbound.json", "w", encoding="utf-8") as f:
        json.dump(final_outbound, f, indent = 4, default = str)
    """

def see_location_of_points(filename_nodes_inbound, filename_nodes_outbound):
    with open(filename_nodes_inbound, "r", encoding="utf-8") as f:
        nodes_inbound = json.load(f)
    with open(filename_nodes_outbound, "r", encoding="utf-8") as f:
        nodes_outbound = json.load(f)
    m = folium.Map(
        location=[41.398294520907044, 2.166181913615897],
        zoom_start=12
        )
    fg_inb = folium.FeatureGroup(name="Inbound", show=True)
    for n in nodes_inbound:
        folium.CircleMarker(
            location=(n[1][1],n[1][0]), radius=6, color="#FF0000", fill=True,
            fill_color="#e60000", fill_opacity=0.9,
            tooltip=f"Inbound endpoint: {n[0]}",
        ).add_to(fg_inb)
    fg_out = folium.FeatureGroup(name="Outbound", show=True)
    for n in nodes_outbound:
        folium.CircleMarker(
            location=(n[1][1],n[1][0]), radius=6, color="#001be6", fill=True,
            fill_color="#001be6", fill_opacity=0.9,
            tooltip=f"Outbound endpoint: {n[0]}",
        ).add_to(fg_out)
    fg_inb.add_to(m)
    fg_out.add_to(m)
    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    m.save("ILP/to_fix/map_with_no_neighbourhood_2.html")

def random_gauss_range(mean, std, min_val, max_val):
    while True:
        x = np.random.normal(mean, std)
        if min_val <= x <= max_val:
            return x

def add_real_time_for_edges(filename_edges_inbound, filename_edges_outbound):
    with open(filename_edges_inbound, "r", encoding="utf-8") as f:
        edges_inbound = json.load(f)
    with open(filename_edges_outbound, "r", encoding="utf-8") as f:
        edges_outbound = json.load(f)

    for key, edge in edges_inbound.items():
        LOS = random_gauss_range(2.5, 2, 1.8, 3.3)
        edge["LOS"] = LOS
        speed = 0.0
        if LOS < 2:
            speed = 1 - 0.2*(LOS - 1)
        if 2 <= LOS < 3:
            speed = 0.8 - 0.2*(LOS - 2)
        if LOS >= 3:
            speed = 0.6 - 0.15*(LOS - 3)
        edge["speed_real"] = speed
        
        length = float(edge["length"])
        v_m = float(edge["speed"])
        v_v = v_m*speed
        v_e = 1.3*v_v
        a = 0.15
        b = 4
        t_bpr = length/v_e*(1+a*(1-speed)**b)
        V_k = v_v*3.6*80*(1-speed)
        N = edge["lanes"]
        t_clear = V_k**2/(1*428.8*speed*v_v*N**2)
        t_no_device = max(t_clear, t_bpr)
        t_device = length/v_e
        decrease = (t_no_device - t_device)/t_no_device * 100
        edge["t_no_device"] = t_no_device
        edge["t_device"] = t_device

    for key, edge in edges_outbound.items():
        LOS = random_gauss_range(2.5, 2, 1.8, 3.3)
        edge["LOS"] = LOS
        speed = 0.0
        if LOS < 2:
            speed = 1 - 0.2*(LOS - 1)
        if 2 <= LOS < 3:
            speed = 0.8 - 0.2*(LOS - 2)
        if LOS >= 3:
            speed = 0.6 - 0.15*(LOS - 3)
        edge["speed_real"] = speed
        
        length = float(edge["length"])
        v_m = float(edge["speed"])
        v_v = v_m*speed
        v_e = 1.3*v_v
        a = 0.15
        b = 4
        t_bpr = length/v_e*(1+a*(1-speed)**b)
        V_k = v_v*3.6*80*(1-speed)
        N = edge["lanes"]
        t_clear = V_k**2/(1*428.8*speed*v_v*N**2)
        t_no_device = max(t_clear, t_bpr)
        t_device = length/v_e
        decrease = (t_no_device - t_device)/t_no_device * 100
        edge["t_no_device"] = t_no_device
        edge["t_device"] = t_device

    with open("ILP/data/inbound_edges_with_times_dict.json", "w", encoding="utf-8") as f:
        json.dump(edges_inbound, f, indent = 4, default = str)
    
    with open("ILP/data/outbound_edges_with_times_dict.json", "w", encoding="utf-8") as f:
        json.dump(edges_outbound, f, indent = 4, default = str)


start = False
if start:
    edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals = get_edges()
    edges_inbound_dict, nodes_inbound_dict = convert_to_dict(edges_inbound, nodes_inbound)
    edges_outbound_dict, nodes_outbound_dict = convert_to_dict(edges_outbound, nodes_outbound)
    edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals = get_edges_dict()
    check_routes(edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals)
    get_routes(edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals)    
    get_nodes_in_abs(nodes_inbound, nodes_outbound)
    get_populatuion_of_node(nodes_inbound, nodes_outbound)
    get_accidents_per_node("ILP/data/counts_between_hours.json", "ILP/data/nodes_inbound.json", "ILP/data/nodes_outbound.json")
    get_routes_within_fences("ILP/data/routes_inbound_nodes.json", "ILP/data/routes_outbound_nodes.json", "ILP/data/inbound_nodes_dict.json", "ILP/data/outbound_nodes_dict.json")
    get_routes_within_parameters(
        "ILP/data/routes_inbound_nodes.json",
        "ILP/data/routes_outbound_nodes.json",
        "ILP/data/inbound_nodes_dict.json",
        "ILP/data/outbound_nodes_dict.json",
        "ILP/data/inbound_edges_dict.json",
        "ILP/data/outbound_edges_dict.json",
        "ILP/data/inbound_leaves.json",
        "ILP/data/outbound_leaves.json"
    )

add_real_time_for_edges(
        "ILP/data/inbound_edges_with_info.json",
        "ILP/data/outbound_edges_with_info.json",
    )
#edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals = get_edges_dict()
#get_populatuion_of_node(nodes_inbound, nodes_outbound)
"""see_location_of_points(
    "ILP/to_fix/inbound_nodes_with_no_nieghbourhood.json",
    "ILP/to_fix/outbound_nodes_with_no_nieghbourhood.json"
)"""
#============== NEXT STEPS ================
"""
Add population and accident to nodes.
Check and make sure all nodes have everything, add the ones that don't have it in a separate file, and add them later
manually or automatically, we'll see
"""



#get_accidents_per_node("ILP/data/counts_between_hours.json", "ILP/data/nodes_inbound.json", "ILP/data/nodes_outbound.json")
#get_emergency_in_Barcelona("poblacio_abs/2015_22_Table_1.csv")
#edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals = get_edges()
#edges_inbound_dict, edges_outbound_dict, nodes_inbound_dict, nodes_outbound_dict, endpoints_inbound, endpoints_outbound, hospitals = get_edges_dict()
#check_routes(edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals)
#get_routes(edges_inbound, edges_outbound, nodes_inbound, nodes_outbound, endpoints_inbound, endpoints_outbound, hospitals)
#get_nodes_in_abs(nodes_inbound, nodes_outbound)
#get_populatuion_of_node(nodes_inbound_dict, nodes_outbound_dict)