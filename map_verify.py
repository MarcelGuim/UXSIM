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


def get_mapa(values_filename, map_filename):
    edges = pd.read_parquet("edges.parquet")
    values = pd.read_parquet(values_filename)
    values["time_group"] = (values["time"] // 300) * 300
    grouped = (
        values.groupby(["edge", "time_group"], as_index=False)
            .agg({"num_veh": "mean"})
            .rename(columns={"num_veh": "mean_num_veh"})
    )
    merged = pd.merge(edges, grouped, left_on="id", right_on="edge", how="left", indicator=True)
    print(merged["_merge"].value_counts())
    merged = merged.drop(columns=["edge"])
    
    k = 0
    while k <= float(merged.iloc[-1]["time_group"]):
        mapa = folium.Map(location=[41.3851, 2.1734], zoom_start=13)
        filtered_df = merged[merged["time_group"] == k].copy()
        values = filtered_df["mean_num_veh"]
        v_max = max(values)
        """
        def value_to_color(value):
            rgba = colormap(norm(value))
            return mcolors.to_hex(rgba)
        """
        def value_to_color(value):
            if value == 0: return '#0000ff'
            elif value == 1: return '#00ff00'
            elif value == 2: return '#ffff00'
            elif value == 3: return '#ffa500'
            elif value == 4: return '#ff4500'
            elif value == 5: return '#ff0000'
        for _, row in filtered_df.iterrows():
            edge_id = row["id"]
            k_jam = float(row["k_jam"])*0.8
            mean_veh = float(row["mean_num_veh"])
            v_max = float(row["speed"])
            lanes = float(row["lanes"])
            length = float(row["length"])
            k_veh = mean_veh/(length*lanes)*1000
            v_veh = v_max*(1-k_veh/k_jam)
            LOS = 0
            if v_veh > 0.8*v_max:
                LOS = 0
            elif v_veh > 0.67*v_max and v_veh < 0.8*v_max:
                LOS = 1
            elif v_veh > 0.51*v_max and v_veh < 0.67*v_max:
                LOS = 2
            elif v_veh > 0.4*v_max and v_veh < 0.51*v_max:
                LOS = 3
            elif v_veh > 0.31*v_max and v_veh < 0.4*v_max:
                LOS = 4
            elif v_veh < 0.31*v_max:
                LOS = 5
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
            colors=['blue', 'green', 'yellow', 'red'], 
            vmin=0, vmax=5, 
            caption='Result Value'
        ).add_to(mapa)
        mapa.save(f"{map_filename}_{k}.html")
        k += 300

get_mapa("simulation_results_4.parquet", "generated_transit_map_4_with_LOS")