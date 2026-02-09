from matplotlib.pylab import sort
from graph_creator import *
from uxsim import *
import pandas as pd
import folium
import random
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
from playwright.sync_api import sync_playwright
import cv2
import numpy as np

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

        mapa.save(f"{map_filename}{int(k)}.html")
        k += time_increase

def html_to_png(html_path, output_png):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})
        page.goto("file://" + os.path.abspath(html_path))
        page.wait_for_timeout(3000)
        page.screenshot(path=output_png)
        browser.close()

def create_map_gif_standard_LOS(edges_filename, values_filename, map_filename, lat, lon, total_time: int, time_increments: int, filename):
    partitions = int(round(total_time/(60*time_increments)))
    try:
        os.makedirs("temporary/")
    except:
        shutil.rmtree("temporary/")
        os.makedirs("temporary/")
    try:
        os.makedirs("frames/")
    except:
        shutil.rmtree("frames/")
        os.makedirs("frames/")
    print("directories correctly created")
    get_mapa_all_edges(
        edges_filename, 
        values_filename, 
        "temporary/", 
        lat, 
        lon, 
        total_time, 
        partitions
    )
    print("maps created")
    frames_files = []
    for i in range(partitions):
        html_to_png(f"temporary/{60*time_increments*(i+1)}.html", f"frames/frame_{i:03d}.png")
        frames_files.append(f"frames/frame_{i:03d}.png")
    print("screenshots taken")    
    frames_files = []
    for i in range(partitions):
        frames_files.append(f"frames/frame_{i:03d}.png")
    frames = []
    frames.append(imageio.imread("background/black.png"))
    for fname in frames_files:
        frames.append(imageio.imread(fname))
    print("frames read")
    ref_h, ref_w = frames[1].shape[:2]
    fixed_frames = []
    for img in frames:
        resized = cv2.resize(img, (ref_w, ref_h))
        fixed_frames.append(resized)

    kargs = {"fps": 2, "loop":0}
    imageio.mimsave(
        filename,
        fixed_frames,
        "GIF",
        **kargs
    )
    print("gif "+filename+ " created")
    shutil.rmtree("temporary/")
    shutil.rmtree("frames/")
    print("temporary files deleted")

def create_map_gif_normalized_LOS(edges_filename, values_filename, map_filename, lat, lon, total_time: int, time_increments: int, filename):
    partitions = int(round(total_time/(60*time_increments)))
    try:
        os.makedirs("temporary/")
    except:
        shutil.rmtree("temporary/")
        os.makedirs("temporary/")
    try:
        os.makedirs("frames/")
    except:
        shutil.rmtree("frames/")
        os.makedirs("frames/")
    print("directories correctly created")
    get_mapa_all_edges(
        edges_filename, 
        values_filename, 
        "temporary/", 
        lat, 
        lon, 
        total_time, 
        partitions
    )
    print("maps created")
    frames_files = []
    for i in range(partitions):
        html_to_png(f"temporary/{60*time_increments*(i+1)}.html", f"frames/frame_{i:03d}.png")
        frames_files.append(f"frames/frame_{i:03d}.png")
    print("screenshots taken")    
    frames_files = []
    for i in range(partitions):
        frames_files.append(f"frames/frame_{i:03d}.png")
    frames = []
    frames.append(imageio.imread("background/black.png"))
    for fname in frames_files:
        frames.append(imageio.imread(fname))
    print("frames read")
    ref_h, ref_w = frames[1].shape[:2]
    fixed_frames = []
    for img in frames:
        resized = cv2.resize(img, (ref_w, ref_h))
        fixed_frames.append(resized)

    kargs = {"fps": 2, "loop":0}
    imageio.mimsave(
        filename,
        fixed_frames,
        "GIF",
        **kargs
    )
    print("gif "+filename+ " created")
    shutil.rmtree("temporary/")
    shutil.rmtree("frames/")
    print("temporary files deleted")

def divide_data_in_time_slots(zone, edges_filename, data_filename, timeslots):
    edges = pd.read_parquet(edges_filename)
    values = pd.read_parquet(data_filename)
    timeslots = timeslots * 60
    values["time_group"] = (values["time"] // timeslots) * timeslots
    values = pd.merge(values, edges, left_on="edge", right_on="id", how="left")
    cols_to_numeric = ["num_veh", "speed_veh", "lanes", "length", "speed", "k_jam"]
    for c in cols_to_numeric:
        values[c] = pd.to_numeric(values[c], errors="coerce")
    """    
    values["speed_veh"] = values["speed_veh"].mask(
        values["speed_veh"].isna() | (values["speed_veh"] == 0),
        values["speed"] * random.uniform(0.75,0.9)
    ).astype(float)
    """
# Divide speed_veh by the factor
    #alues["speed_veh"] = values["speed_veh"] / factor_per_row


    values["v_max"] = values["speed"]
    values["LOS"] = pd.cut(
        values["speed_veh"]*1.3 / values["v_max"]/1.2,
        #bins=[-float("inf"), 0.31, 0.4, 0.51, 0.67, 0.75, float("inf")],
        bins=[-float("inf"), 0.30, 0.45, 0.6, 0.8, float("inf")],
        labels=[5, 4, 3, 2, 1],
        right=True
    ).astype("Int64")

    #values["LOS"] = values["LOS"].fillna(1).astype(float)

    grouped = (
        values.groupby("time_group", as_index=False)
              .agg(mean_LOS=("LOS", "mean"))
    )
    print(grouped)
    valid_time_groups = sorted(grouped["time_group"].unique())
    if len(valid_time_groups) <= 2:
        return  # nothing to save

    valid_time_groups = valid_time_groups[1:-2]

    values = values[values["time_group"].isin(valid_time_groups)]
    grouped = grouped[grouped["time_group"].isin(valid_time_groups)]

    subset = values[["time_group", "time", "edge", "speed_veh", "LOS"]].copy()

    for _, row in grouped.iterrows():
        tg = row["time_group"]
        mean_los = round(row["mean_LOS"], 1)
        out_path = zone+"/SIMULATED_DATA/"+str(mean_los)+"/"+str(row["mean_LOS"])+".parquet"
        os.makedirs(zone+"/SIMULATED_DATA/"+str(mean_los)+"/", exist_ok=True)
        tg_data = subset[subset["time_group"] == tg]
        tg_data.to_parquet(out_path, index=False)

def process_and_save_los(zone, edges_filename, data_filename, timeslots):
    edges = pd.read_parquet(edges_filename)
    print(edges.columns)
    print(edges["speed"].isna().sum())
    print((edges["speed"] == 0.0).sum())

    values = pd.read_parquet(data_filename)
    timeslots = timeslots * 60
    values["time_group"] = (values["time"] // timeslots) * timeslots
    values = pd.merge(values, edges, left_on="edge", right_on="id", how="left")
    cols_to_numeric = ["num_veh", "speed_veh", "lanes", "length", "speed", "k_jam"]
    for c in cols_to_numeric:
        values[c] = pd.to_numeric(values[c], errors="coerce")
    values["speed_veh"] = values["speed_veh"].fillna(0)
    print(values["speed"].isna().sum())
    print((values["speed"] == 0.0).sum())
    # 1️⃣ Group by edge and sort by time
    values = values.sort_values(["edge", "time"]).reset_index(drop=True)
    print((values["speed_veh"] == 0.0).sum())
    # 2️⃣ Fill veh_speed if zero
    for i in range(len(values)):
        if values.loc[i, "speed_veh"] == 0.0 or values.loc[i, "speed_veh"] == 0:
            new_speed = values.loc[i, "speed_veh"]
            old_speed = values.loc[i-1, "speed_veh"]
            this_edge = values.loc[i, "edge"]
            old_edge = values.loc[i-1, "edge"]
            this_time = values.loc[i, "time"]
            old_time = values.loc[i-1, "time"]
            if i > 0 and values.loc[i, "edge"] == values.loc[i - 1, "edge"] and values.loc[i - 1, "speed_veh"] > 0:
                # previous row same edge → multiply previous speed by random factor 0.95-1.05
                factor = random.uniform(0.95, 1.05)
                values.loc[i, "speed_veh"] = values.loc[i - 1, "speed_veh"] * factor
                new_speed = values.loc[i, "speed_veh"]
                old_speed = values.loc[i-1, "speed_veh"]
                max_speed = values.loc[i, "speed"]
            else:
                # previous row not same edge → speed * random factor 0.75-0.9
                factor = random.uniform(0.75, 0.9)
                values.loc[i, "speed_veh"] = values.loc[i, "speed"] * factor
    values.to_parquet("eixample/RESULTS/simulation25_2.parquet", index=False)
    # 3️⃣ Compute LOS
    values["v_max"] = values["speed"]
    values["LOS"] = pd.cut(
        values["speed_veh"] / values["v_max"],
        bins=[-float("inf"), 0.30, 0.45, 0.6, 0.8, float("inf")],
        labels=[5, 4, 3, 2, 1],
        right=True
    ).astype("Int64")

    # 4️⃣ Compute mean LOS per time_group
    grouped = (
        values.groupby("time_group", as_index=False)
              .agg(mean_LOS=("LOS", "mean"))
    )

    print(grouped)
    """
    valid_time_groups = sorted(grouped["time_group"].unique())
    if len(valid_time_groups) <= 2:
        return  # nothing to save

    # Remove first and last two time_groups
    valid_time_groups = valid_time_groups[1:-2]

    values = values[values["time_group"].isin(valid_time_groups)]
    grouped = grouped[grouped["time_group"].isin(valid_time_groups)]

    subset = values[["time_group", "time", "edge", "speed_veh", "LOS"]].copy()

    # 5️⃣ Save each time_group according to rounded mean LOS
    for _, row in grouped.iterrows():
        tg = row["time_group"]
        mean_los = round(row["mean_LOS"], 1)
        out_dir = f"{zone}/SIMULATED_DATA/{mean_los}/"
        os.makedirs(out_dir, exist_ok=True)
        out_path = f"{out_dir}{row['mean_LOS']}.parquet"

        tg_data = subset[subset["time_group"] == tg]
        tg_data.to_parquet(out_path, index=False)
    """

def compute_los_time_stats_with_plots(zone, filename):
    edges = pd.read_parquet(zone+"/SIMULATED_DATA/"+filename)
    edges = edges[~edges["LOS"].isin([0, 6])]
    stats = (
        edges
        .agg(
            mean_value="mean",
            variance=lambda x: x.var(ddof=0)
        )
        .reset_index()
    )
    plt.figure()
    plt.hist(stats["variance"].dropna(), bins=30)
    plt.xlabel("Variance of LOS")
    plt.ylabel("Frequency")
    plt.title("Histogram of LOS Variance for March")
    plt.savefig(zone+"/SIMULATED_DATA/"+filename+"variance.png")
    plt.close()

    plt.figure()
    plt.hist(stats["mean_value"].dropna(), bins=30)
    plt.xlabel("Mean LOS")
    plt.ylabel("Frequency")
    plt.title("Histogram of Mean LOS for March")
    plt.savefig(zone+"/SIMULATED_DATA/"+filename+"hist_mean.png")
    plt.close()

def compute_los_histogram_with_variance(zone, filename):
    # Load one time_group file
    df = pd.read_parquet(f"{zone}/SIMULATED_DATA/{filename}")

    # Clean LOS
    los = df["LOS"].astype(float)
    los = los[~los.isin([0, 6])]

    # Compute statistics
    mean_los = los.mean()
    var_los = los.var(ddof=0)

    # Histogram of LOS values (edges)
    plt.figure()
    plt.hist(los, bins=np.arange(los.min(), los.max() + 1, 0.5))
    plt.xlabel("LOS")
    plt.ylabel("Number of edges")
    plt.title(
        "LOS distribution per time group"
    )
    plt.tight_layout()

    # Output path
    out_path = f"{zone}/SIMULATED_DATA/{filename}_los_hist.png"
    plt.savefig(out_path)
    plt.close()

    return mean_los, var_los

#process_and_save_los("eixample","eixample/edges_eixample_important.parquet","eixample/RESULTS/simulation25.parquet", 30)
#divide_data_in_time_slots("eixample","eixample/edges_eixample_important.parquet","eixample/RESULTS/simulation27.parquet", 30)
#compute_los_histogram_with_variance("eixample","2.7/2.665836554663495.parquet")                                
