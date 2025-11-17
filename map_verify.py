from graph_creator import *
from uxsim import *
from uxsim.ResultGUIViewer import ResultGUIViewer
import pandas as pd
from IPython.display import display
from uxsim.DTAsolvers import *
import time
import statistics as statis
import folium
from matplotlib import cm, colors
from branca.colormap import LinearColormap
from matplotlib import colors as mcolors
import matplotlib.pyplot as plt

def get_mapa(values_filename, map_filename):
    edges = pd.read_parquet("edges.parquet")
    values = pd.read_parquet(values_filename)
    values["time_group"] = (values["time"] // 300) * 300

    # Afegim dades dels edges a cada registre
    values = pd.merge(values, edges, left_on="edge", right_on="id", how="left")
    cols_to_numeric = ["num_veh", "lanes", "length", "speed", "k_jam"]
    for c in cols_to_numeric:
        values[c] = pd.to_numeric(values[c], errors="coerce")
    # Calculem variables per a cada fila
    values["k_street"] = values["num_veh"] / (values["lanes"] * values["length"]) * 1000
    values["v_max"] = values["speed"]
    values["v_veh"] = values["v_max"] * (1 - values["k_street"] / values["k_jam"])

    # Calculem el LOS per cada fila (vectoritzat)
    values["LOS"] = pd.cut(
        values["v_veh"] / values["v_max"],
        bins=[-float("inf"), 0.31, 0.4, 0.51, 0.67, 0.8, float("inf")],
        labels=[5, 4, 3, 2, 1, 0],
        right=True
    ).astype(int)
    # Ara agrupem per fer la mitjana del LOS
    grouped_2 = (
        values.groupby(["edge", "time_group"], as_index=False)
            .agg({"LOS": "mean"})
            .rename(columns={"LOS": "mean_LOS"})
    )
    # Tornem a unir amb edges si vols el resultat complet
    merged = pd.merge(edges, grouped_2, left_on="id", right_on="edge", how="left", indicator=True)
    k = 0
    while k <= float(merged.iloc[-1]["time_group"]):
        mapa = folium.Map(location=[41.40371878522945, 2.174445524020986], zoom_start=13)
        filtered_df = merged[merged["time_group"] == k].copy()
        norm = colors.Normalize(vmin=0, vmax=6) 
        colormap = cm.get_cmap('jet')
        def value_to_color(value):
            rgba = colormap(norm(value))
            return mcolors.to_hex(rgba)
        for _, row in filtered_df.iterrows():
            edge_id = row["id"]
            LOS = row["mean_LOS"]
            color = value_to_color(LOS)
            x_in, y_in = row["inc_x"], row["inc_y"]
            x_out, y_out = row["out_x"], row["out_y"]
            folium.PolyLine(
                locations= [(y_in, x_in),(y_out, x_out)],
                color=color,
                weight=4,
                opacity=0.8,
                tooltip=f"Edge {edge_id}: {LOS:.2f}"
            ).add_to(mapa)
        LinearColormap(
            colors = ['blue', 'cyan', 'green', 'yellow', 'orange', 'red'], 
            vmin=0, vmax=6, 
            caption='Result Value'
        ).add_to(mapa)
        mapa.save(f"mapas/{map_filename}_{k}.html")
        k += 300

get_mapa("simulation_results_2.parquet", "generated_transit_map_AMB_PUNTS_RODEJANT_MAPA_with_LOS")