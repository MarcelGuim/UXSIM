import json
import folium
import pandas as pd
from shapely import wkt
import geopandas as gpd


def test_something_forgot():
    # ---- Load JSON file ----
    with open("emergency_corridors/corridor_edges.json", "r", encoding="utf-8") as f:
        edges = json.load(f)

    # ---- Create base map (centered on first edge) ----
    first_coord = edges[0]["coordinates"][0]
    map_center = [first_coord[0], first_coord[1]]

    m = folium.Map(location=map_center, zoom_start=16)

    # ---- Add edges to map ----
    print(len(edges))
    for edge in edges:
        coords = edge["coordinates"]
        
        # Convert to Leaflet format [lat, lon]
        latlngs = [(c[0], c[1]) for c in coords]

        style = edge.get("style", {})
        attributes = edge.get("attributes", {})

        popup_html = f"""
        <b>Edge ID:</b> {attributes.get("id")}<br>
        <b>Lanes:</b> {attributes.get("lanes")}<br>
        <b>Length:</b> {attributes.get("length")} m<br>
        <b>Speed:</b> {attributes.get("speed")} m/s<br>
        <b>Vehicles:</b> {attributes.get("number_of_vehicles")}<br>
        <b>Density:</b> {attributes.get("density")}
        """

        folium.PolyLine(
            locations=latlngs,
            color=style.get("color", "blue"),
            weight=style.get("weight", 3),
            opacity=style.get("opacity", 1),
            popup=folium.Popup(popup_html, max_width=300)
        ).add_to(m)

    # ---- Save map to HTML file ----
    m.save("corridor_map.html")

    print("Map successfully saved as corridor_map.html")

def get_map_abs_points():
    df = pd.read_csv("ILP/poblacio_abs/arees_basiques_de_salut_20260210_copy.csv", sep=",")    
    latlon = []
    for index, row in df.iterrows():
        if row["Codi"] == 73:
            geom = row["Geometry"]
            points = geom.split("(((")[1].split("))")[0]
            l_p = points.split(",")
            for point in l_p:
                vals = point.split(" ")
                lat = vals[1]
                lon = vals[2]
                latlon.append([lat, lon])

    m = folium.Map(
        location=[latlon[0][1], latlon[0][0]],
        zoom_start=15 
    )
    for lat, lon in latlon:
        folium.CircleMarker(
            location=(lon,lat), radius=3, color="#FF0000", fill=True,
            fill_color="#e60000", fill_opacity=0.9,
            tooltip=f"lat, lon: {lat}, {lon}",
        ).add_to(m)
    m.save("ILP/poblacio_abs/map_with_points_fixed_79_2.html")

def get_map_neighbourhood():
    df = pd.read_csv("ILP/poblacio_abs/BarcelonaCiutat_Barris.csv", sep=",")    
    latlon = []
    for index, row in df.iterrows():
        if row["codi_barri"] == 73:
            points = row["geometria_wgs84"].split("((")[1].split("))")[0]
            l_p = points.split(",")
            for point in l_p:
                vals = point.split(" ")
                if len(vals) != 3:
                    print(vals)
                lat = vals[1]
                lon = vals[2]
                latlon.append([lat, lon])

    m = folium.Map(
        location=[latlon[0][1], latlon[0][0]],
        zoom_start=15 
    )
    for lat, lon in latlon:
        folium.CircleMarker(
            location=(lon,lat), radius=3, color="#FF0000", fill=True,
            fill_color="#e60000", fill_opacity=0.9,
            tooltip=f"lat, lon: {lat}, {lon}",
        ).add_to(m)
    m.save("ILP/poblacio_abs/map_with_neighbourhoods_20_2.html")

def draw_neighbourhood():
    df = pd.read_csv("ILP/poblacio_abs/BarcelonaCiutat_Barris.csv", sep=",")    
    GEOM_COL = "geometria_wgs84"
    
    df[GEOM_COL] = df[GEOM_COL].apply(wkt.loads)
    
    m = folium.Map(
        location=[41.40070445909809, 2.167557256927841],
        zoom_start=15 
    )

    gdf = gpd.GeoDataFrame(
        df,
        geometry=GEOM_COL,
        crs="EPSG:4326"
    )

    folium.GeoJson(
        gdf,
        name="Neighbourhood",
        style_function=lambda feature: {
            "fillColor": "#1f78b4",
            "color": "black",
            "weight": 0.8,
            "fillOpacity": 0.45,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=[
                "nom_barri",
                "codi_barri"
            ],
            aliases=[
                "Codi nom_barri:",
                "codi_barri:"
            ],
            sticky=True
        )
    ).add_to(m)

    m.save("ILP/poblacio_abs/map_with_neighbourhoods_all_of_them.html")

def get_info_edges():
    with open("ILP/data/inbound_edges_with_info.json", "r", encoding="utf-8") as f:
        inbound_edges = json.load(f)

    with open("ILP/data/outbound_edges_with_info.json", "r", encoding="utf-8") as f:
        outbound_edges = json.load(f)
    
    backbone_inbound = 0
    primary_inbound = 0
    secondary_inbound = 0
    tertiary_inbound = 0

    for key, e in inbound_edges.items():
        if e["tier"] == "backbone":
            backbone_inbound += 1
        if e["tier"] == "primary":
            primary_inbound += 1
        if e["tier"] == "secondary":
            secondary_inbound += 1
        if e["tier"] == "tertiary":
            tertiary_inbound += 1

    backbone_outbound = 0
    primary_outbound = 0
    secondary_outbound = 0
    tertiary_outbound = 0

    for key, e in outbound_edges.items():
        if e["tier"] == "backbone":
            backbone_outbound += 1
        if e["tier"] == "primary":
            primary_outbound += 1
        if e["tier"] == "secondary":
            secondary_outbound += 1
        if e["tier"] == "tertiary":
            tertiary_outbound += 1   

    print(f"The inbound corridor has {backbone_inbound} backbone edges")
    print(f"The inbound corridor has {primary_inbound} primary edges")
    print(f"The inbound corridor has {secondary_inbound} secondary edges")
    print(f"The inbound corridor has {tertiary_inbound} tertiary edges")

    print(f"The outbound corridor has {backbone_outbound} backbone edges")
    print(f"The outbound corridor has {primary_outbound} primary edges")
    print(f"The outbound corridor has {secondary_outbound} secondary edges")
    print(f"The outbound corridor has {tertiary_outbound} tertiary edges")

if __name__ == "__main__":
    get_info_edges()