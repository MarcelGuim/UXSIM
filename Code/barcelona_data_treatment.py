from file_parser import *
import pandas as pd
import folium
from shapely.geometry import Point, Polygon, LineString
import matplotlib.pyplot as plt

def get_dataset_streets_in_area(zone):
    polygon_coords = parse_klm_file(zone+"/"+zone+".kml")
    polygon = Polygon(polygon_coords)
    df_data = pd.read_csv("data_streets/2025_03_Marc_TRAMS_TRAMS.csv")
    df_streets = pd.read_csv("data_streets/transit_relacio_trams.csv")
    mapa = folium.Map(location=[41.3851, 2.1734], zoom_start=14)
    for _, fila in df_streets.iterrows():
        coords = [float(x) for x in fila['Coordenades'].split(',')]
        punts = [(coords[i+1], coords[i]) for i in range(0, len(coords), 2)]
        for i in range(len(punts) - 1):
            point_o = Point(punts[i][1], punts[i][0])
            point_d = Point(punts[i+1][1], punts[i+1][0])
            if point_o.within(polygon) and point_d.within(polygon):
                folium.PolyLine(
                    locations=[[punts[i][0], punts[i][1]], [punts[i+1][0], punts[i+1][1]]],
                    color='blue',
                    weight=4,
                    opacity=0.7,
                    tooltip=fila['Descripció']
                ).add_to(mapa)
    mapa.save("data_streets/MAPA/mapa_carrers.html")

def get_dataset_streets_in_area_with_values(zone, time_start, time_end):
    polygon_coords = parse_klm_file(zone+"/"+zone+".kml")
    polygon = Polygon(polygon_coords)
    df_data = pd.read_csv("data_streets/2025_03_Marc_TRAMS_TRAMS.csv")
    df_streets = pd.read_csv("data_streets/transit_relacio_trams.csv")
    mapa = folium.Map(location=[41.3851, 2.1734], zoom_start=13)
    for _, fila in df_streets.iterrows():
        coords = [float(x) for x in fila['Coordenades'].split(',')]
        punts = [(coords[i+1], coords[i]) for i in range(0, len(coords), 2)]
        for i in range(len(punts) - 1):
            point_o = Point(punts[i][1], punts[i][0])
            point_d = Point(punts[i+1][1], punts[i+1][0])
            if point_o.within(polygon) and point_d.within(polygon):
                folium.PolyLine(
                    locations=[[punts[i][0], punts[i][1]], [punts[i+1][0], punts[i+1][1]]],
                    color='blue',
                    weight=4,
                    opacity=0.7,
                    tooltip=fila['Descripció']
                ).add_to(mapa)
    mapa.save("data_streets/MAPA/mapa_carrers.html")

def prepare_parquet_with_ids_data(zone):
    edges = pd.DataFrame(columns=["id", "lon_o", "lat_o", "lon_d", "lat_d"])
    polygon_coords = parse_klm_file(zone+"/"+zone+".kml")
    polygon = Polygon(polygon_coords)
    df_data = pd.read_csv("data_streets/2025_03_Marc_TRAMS_TRAMS.csv")
    df_streets = pd.read_csv("data_streets/transit_relacio_trams.csv")
    for _, fila in df_streets.iterrows():
        coords = [float(x) for x in fila['Coordenades'].split(',')]
        punts = [(coords[i+1], coords[i]) for i in range(0, len(coords), 2)]
        done = False
        for i in range(len(punts) - 1):
            point_o = Point(punts[i][1], punts[i][0])
            if point_o.within(polygon):
                point_e = Point(punts[len(punts)-1][1], punts[len(punts)-1][0])
                if point_o.within(polygon) and point_e.within(polygon):
                    edges.loc[len(edges)] = [fila['Tram'], punts[i][1], punts[i][0], punts[i+1][1], punts[i+1][0]]
                    done = True
                else:
                    for i in range(len(punts) - 1):
                        point_e =  Point(punts[len(punts)-i-1][1], punts[len(punts)-i-1][0])
                        if point_o.within(polygon) and point_e.within(polygon):
                            edges.loc[len(edges)] = [fila['Tram'], punts[i][1], punts[i][0], punts[i+1][1], punts[i+1][0]]
                            done = True
                            break
            if done:
                break
    edges.to_parquet(zone+"/REAL_DATA/id_with_coords.parquet", index=False)

def prepare_parquet_with_values(zone, i):
    edges_with_coords = pd.read_parquet(zone+"/REAL_DATA/id_with_coords.parquet")
    edges = pd.DataFrame(columns=["id","timestamp", "value"])
    df_data = pd.read_csv("data_streets/2025_"+str(i)+"_TRAMS_TRAMS.csv")
    df_streets = pd.read_csv("data_streets/transit_relacio_trams.csv")
    for _, fila in df_data.iterrows():
        id =  int(fila["idTram"])
        if id in edges_with_coords["id"].values:
            edges.loc[len(edges)] = [id, fila["data"], fila["estatActual"]]
    edges.to_parquet(zone+"/REAL_DATA/id_with_values_"+str(i)+".parquet", index=False)

def get_data_mean_values_for_n_time(zone, time):
    edges_with_coords = pd.read_parquet(zone+"/REAL_DATA/id_with_coords.parquet")
    edges_with_values = pd.read_parquet(zone+"/REAL_DATA/id_with_values.parquet")

def compute_los_time_stats_with_plots(zone, i):
    edges = pd.read_parquet(zone+"/REAL_DATA/id_with_values_"+str(i)+".parquet")
    edges["timestamp"] = pd.to_datetime(
    edges["timestamp"],
    format="%Y%m%d%H%M%S"
    )
    edges = edges[~edges["value"].isin([0, 6])]
    stats = (
        edges
        .groupby("timestamp")["value"]
        .agg(
            mean_value="mean",
            variance=lambda x: x.var(ddof=0)
        )
        .reset_index()
    )

    stats.to_csv(zone+"/mean_variance_"+str(i)+".csv", index=False)

    plt.figure()
    plt.hist(stats["variance"].dropna(), bins=30)
    plt.xlabel("Variance of LOS")
    plt.ylabel("Frequency")
    plt.title("Histogram of LOS Variance for March")
    plt.savefig(zone + "/REAL_DATA/hist_variance_"+str(i)+".png")
    plt.close()

    plt.figure()
    plt.hist(stats["mean_value"].dropna(), bins=30)
    plt.xlabel("Mean LOS")
    plt.ylabel("Frequency")
    plt.title("Histogram of Mean LOS for March")
    plt.savefig(zone + "/REAL_DATA/hist_mean_"+str(i)+".png")
    plt.close()

    return stats

def compute_los_time_stats_with_plots_MEAN_LOS_given(zone, i, mean_los_start, mean_los_end):
    edges = pd.read_parquet(zone + "/REAL_DATA/id_with_values_" + str(i) + ".parquet")

    edges["timestamp"] = pd.to_datetime(
        edges["timestamp"],
        format="%Y%m%d%H%M%S"
    )

    edges = edges[~edges["value"].isin([0, 6])]

    stats = (
        edges
        .groupby("timestamp")["value"]
        .agg(
            mean_value="mean",
            variance=lambda x: x.var(ddof=0)
        )
        .reset_index()
    )

    filtered_stats = stats[
        (stats["mean_value"] >= mean_los_start) &
        (stats["mean_value"] <= mean_los_end)
    ]

    filtered_edges = edges[
        edges["timestamp"].isin(filtered_stats["timestamp"])
    ]

    # 1️⃣ Histogram of variance of the streets
    plt.figure()
    plt.hist(filtered_stats["variance"].dropna(), bins=30)
    plt.xlabel("Variance of LOS")
    plt.ylabel("Frequency")
    plt.title(
        f"Histogram of LOS Variance (Mean LOS ∈ [{mean_los_start}, {mean_los_end}])"
    )
    plt.savefig(
        zone + f"/REAL_DATA/hist_variance_{mean_los_start}_{mean_los_end}_{i}.png"
    )
    plt.close()

    # 2️⃣ Histogram of LOS values for every street
    plt.figure()
    plt.hist(filtered_edges["value"].dropna(), bins=5)
    plt.xlabel("LOS value")
    plt.ylabel("Frequency")
    plt.title(
        f"Histogram of LOS Values for All Streets\n"
        f"(Mean LOS ∈ [{mean_los_start}, {mean_los_end}])"
    )
    plt.savefig(
        zone + f"/REAL_DATA/hist_los_values_{mean_los_start}_{mean_los_end}_{i}.png"
    )
    plt.close()

    # 3️⃣ Histogram of HOURS of the day (0–23)
    filtered_stats["hour"] = filtered_stats["timestamp"].dt.hour

    plt.figure()
    plt.hist(filtered_stats["hour"], bins=24, range=(0, 24))
    plt.xlabel("Hour of day")
    plt.ylabel("Frequency")
    plt.title(
        f"Hours of Day Where Mean LOS ∈ [{mean_los_start}, {mean_los_end}]"
    )
    plt.xticks(range(0, 24))
    plt.tight_layout()
    plt.savefig(
        zone + f"/REAL_DATA/hist_hours_{mean_los_start}_{mean_los_end}_{i}.png"
    )
    plt.close()

    # 4️⃣ Percentage histogram of MEAN LOS (bin width = 0.5)

    mean_los_values = stats["mean_value"].dropna()

    # Define bins: from 0 up to max mean LOS, step 0.5
    bin_width = 0.25
    max_los = mean_los_values.max()
    bins = np.arange(0, max_los + bin_width, bin_width)

    # Compute histogram counts
    counts, bin_edges = np.histogram(mean_los_values, bins=bins)

    # Convert counts to percentages
    percentages = counts / counts.sum() * 100

    # Bin centers for plotting
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    plt.figure()
    plt.bar(bin_centers, percentages, width=bin_width * 0.9)
    plt.xlabel("Mean LOS")
    plt.ylabel("Percentage of time (%)")
    plt.title("Percentage of Time Spent at Each Mean LOS\n(bin size = 0.25)")
    plt.xticks(bin_edges, rotation=45)
    plt.tight_layout()
    plt.savefig(zone + f"/REAL_DATA/mean_los_percentage_bins_0.25_{i}.png")
    plt.close()

    return filtered_stats
compute_los_time_stats_with_plots("eixample", 3)
#compute_los_time_stats_with_plots_MEAN_LOS_given("eixample", 3, 2.0, 2.6)
"""
for i in range(3):
    i += 10
    prepare_parquet_with_values("eixample", i)    
    compute_los_time_stats_with_plots("eixample",i)
"""
#compute_los_time_stats_with_plots("eixample")
#prepare_parquet_with_ids_data("eixample")
#prepare_parquet_with_values("eixample")
#prepare_barcelona_data("eixample")
#get_dataset_streets_in_area("eixample")