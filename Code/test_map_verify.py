from graph_creator import *
from uxsim import *
import pandas as pd
import folium
from matplotlib import cm, colors
from matplotlib import colors as mcolors
from scipy.spatial.distance import euclidean
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
import glob
import os
import imageio.v2 as imageio
import glob

GEOM_TOL = 1e-4 

def build_edge_chains(df, max_len=4, tol=GEOM_TOL):
    chains = []
    used = set()
    df = df.reset_index(drop=True)

    for i, row in df.iterrows():
        if i in used:
            continue

        chain = [i]
        used.add(i)
        curr_out = (row["out_x"], row["out_y"])

        while len(chain) < max_len:
            found = False
            for j, r in df.iterrows():
                if j in used:
                    continue
                if euclidean(curr_out, (r["inc_x"], r["inc_y"])) < tol:
                    chain.append(j)
                    used.add(j)
                    curr_out = (r["out_x"], r["out_y"])
                    found = True
                    break
            if not found:
                break

        chains.append(chain)

    return chains

def get_mapa(values_filename, map_filename, total_time: int, partition: int):
    time_increase = total_time/partition
    edges = pd.read_parquet("hospital_clinic/edges_hospital_clinic.parquet")
    values = pd.read_parquet(values_filename)

    values["time_group"] = (values["time"] // time_increase) * time_increase

    values = pd.merge(values, edges, left_on="edge", right_on="id", how="left")

    cols_to_numeric = ["num_veh", "lanes", "length", "speed", "k_jam"]
    for c in cols_to_numeric:
        values[c] = pd.to_numeric(values[c], errors="coerce")

    values["k_street"] = values["num_veh"] / (values["lanes"] * values["length"]) * 1000
    values["v_max"] = values["speed"]
    values["v_veh"] = values["v_max"] * (1 - values["k_street"] / values["k_jam"])

    values["LOS"] = pd.cut(
        values["v_veh"] / values["v_max"],
        bins=[-float("inf"), 0.31, 0.4, 0.51, 0.67, 0.8, float("inf")],
        labels=[5, 4, 3, 2, 1, 0],
        right=True
    ).astype(int)

    grouped = (
        values.groupby(["edge", "time_group"], as_index=False)
              .agg(mean_LOS=("LOS", "mean"))
    )

    merged = pd.merge(edges, grouped, left_on="id", right_on="edge", how="left")

    # ---- Map creation per time slice ----
    norm = colors.Normalize(vmin=0, vmax=6)
    colormap = cm.get_cmap("jet")

    def value_to_color(value):
        rgba = colormap(norm(value))
        return mcolors.to_hex(rgba)

    k = time_increase
    max_time = merged["time_group"].max()

    while k <= max_time:
        mapa = folium.Map(
            location=[41.38246354510279, 2.1472665793524985],
            zoom_start=14
        )

        df_t = merged[merged["time_group"] == k].copy()
        df_t = df_t.dropna(subset=["mean_LOS"])

        chains = build_edge_chains(df_t, max_len=4)

        for chain in chains:
            chain_df = df_t.iloc[chain]

            avg_los = chain_df["mean_LOS"].mean()
            color = value_to_color(avg_los)

            start = (chain_df.iloc[0]["inc_y"], chain_df.iloc[0]["inc_x"])
            end = (chain_df.iloc[-1]["out_y"], chain_df.iloc[-1]["out_x"])

            folium.PolyLine(
                locations=[start, end],
                color=color,
                weight=6,
                opacity=0.9,
                tooltip=f"Avg LOS (spatial 4 edges): {avg_los:.2f}"
            ).add_to(mapa)

        folium.LinearColormap(
            colors=["blue", "cyan", "green", "yellow", "orange", "red"],
            vmin=0,
            vmax=6,
            caption="LOS (4-edge spatial average)"
        ).add_to(mapa)

        mapa.save(f"{map_filename}_{int(k)}.html")
        k += time_increase

def get_mapa_all_edges(edges_filename, values_filename, map_filename, lat, lon, total_time: int, partition: int):
    time_increase = total_time/partition
    edges = pd.read_parquet(edges_filename)
    values = pd.read_parquet(values_filename)

    values["time_group"] = (values["time"] // time_increase) * time_increase

    values = pd.merge(values, edges, left_on="edge", right_on="id", how="left")

    cols_to_numeric = ["num_veh", "speed_veh", "lanes", "length", "speed", "k_jam"]
    for c in cols_to_numeric:
        values[c] = pd.to_numeric(values[c], errors="coerce")

    
    # LOS with number of vehicles
    """
    values["k_street"] = values["num_veh"] / (values["lanes"] * values["length"]) * 1000
    values["v_max"] = values["speed"]
    values["v_veh"] = values["v_max"] * (1 - values["k_street"] / values["k_jam"])

    values["LOS"] = pd.cut(
        values["v_veh"] / values["v_max"],
        bins=[-float("inf"), 0.31, 0.4, 0.51, 0.67, 0.8, float("inf")],
        labels=[5, 4, 3, 2, 1, 0],
        right=True
    ).astype(int)
    """
    #LOS with speed of vehicles
    values["v_max"] = values["speed"]
    values["LOS"] = pd.cut(
        values["speed_veh"] / values["v_max"],
        bins=[-float("inf"), 0.31, 0.4, 0.51, 0.67, 0.8, float("inf")],
        labels=[5, 4, 3, 2, 1, 0],
        right=True
    ).astype("Int64")

    grouped = (
        values.groupby(["edge", "time_group"], as_index=False)
              .agg(mean_LOS=("LOS", "mean"))
    )

    merged = pd.merge(edges, grouped, left_on="id", right_on="edge", how="left")

    norm = colors.Normalize(vmin=0, vmax=6)
    colormap = cm.get_cmap("jet")

    def value_to_color(value):
        return mcolors.to_hex(colormap(norm(value)))

    k = time_increase
    max_time = merged["time_group"].max()

    while k <= max_time:
        mapa = folium.Map(
            location=[lat,lon],
            zoom_start=14
        )

        df_t = merged[merged["time_group"] == k].copy()
        df_t = df_t.dropna(subset=["mean_LOS"])

        for _, row in df_t.iterrows():
            start = (row["inc_y"], row["inc_x"])
            end = (row["out_y"], row["out_x"])

            folium.PolyLine(
                locations=[start, end],
                color=value_to_color(row["mean_LOS"]),
                weight=4,
                opacity=0.85,
                tooltip=f"Edge {row['id']} | LOS: {row['mean_LOS']:.2f}"
            ).add_to(mapa)

        folium.LinearColormap(
            colors=["blue", "cyan", "green", "yellow", "orange", "red"],
            vmin=0,
            vmax=6,
            caption="LOS per street"
        ).add_to(mapa)

        mapa.save(f"{map_filename}_{int(k)}.html")
        k += time_increase

def create_map_gif(edges_filename, values_filename, map_filename, lat, lon, total_time: int, time_increments: int):
    os.makedirs("temporary/")
    partitions = total_time/(60*time_increments)
    get_mapa_all_edges(
        edges_filename, 
        values_filename, 
        "temporary/map", 
        lat, 
        lon, 
        total_time, 
        partitions
    )
    html_files = sorted(glob.glob("/temporary"))
    output_dir = "frames"
    os.makedirs(output_dir, exist_ok=True)

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--window-size=1200,900")

    driver = webdriver.Chrome(options=options)

    for i, html in enumerate(html_files):
        driver.get("file://" + os.path.abspath(html))
        time.sleep(2)  # let Leaflet tiles load
        driver.save_screenshot(f"{output_dir}/frame_{i:03d}.png")

    driver.quit()
    frames = []
    for fname in sorted(glob.glob("frames/frame_*.png")):
        frames.append(imageio.imread(fname))

    imageio.mimsave(
        "traffic_evolution.gif",
        frames,
        duration=0.6  # seconds per frame
    )

    shutil.rmtree("temporary")


"""
get_mapa_all_edges(
    "eixample/edges_eixample.parquet",
    "eixample/RESULTS/simulation1.parquet",
    "eixample/MAPA/mapa_1"
)
"""
