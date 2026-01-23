from graph_creator import *
from uxsim import *
import pandas as pd
import folium
from matplotlib import cm, colors
from matplotlib import colors as mcolors
from scipy.spatial.distance import euclidean

time_increase = 3600 / 6
GEOM_TOL = 1e-4   # geometric tolerance for connecting edges


def build_edge_chains(df, max_len=4, tol=GEOM_TOL):
    """
    Build chains of spatially consecutive edges (up to max_len).
    Consecutive means: out_x,out_y -> inc_x,inc_y within tolerance.
    """
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


def get_mapa(values_filename, map_filename):
    edges = pd.read_parquet("edges.parquet")
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
        rgba = color
        map(norm(value))
        return mcolors.to_hex(rgba)

    k = time_increase
    max_time = merged["time_group"].max()

    while k <= max_time:
        mapa = folium.Map(
            location=[41.40371878522945, 2.174445524020986],
            zoom_start=13
        )

        df_t = merged[merged["time_group"] == k].copy()
        df_t = df_t.dropna(subset=["mean_LOS"])

        chains = build_edge_chains(df_t, max_len=4)

        for chain in chains:
            chain_df = df_t.loc[chain]

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

        mapa.save(f"mapas/{map_filename}_{int(k)}.html")
        k += time_increase


# ---- Run ----
get_mapa(
    "RESULTS/simulation_results_TEST_AMB_PUNTS_RODEJANT_MAPA_k300_j2_t658.parquet",
    "TEST_simulation_results_TEST_AMB_PUNTS_RODEJANT_MAPA_k300_j2_t658"
)
