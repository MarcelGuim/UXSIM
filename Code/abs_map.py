import pandas as pd
import geopandas as gpd
from shapely import wkt
import folium
import json

# ============================================================
# LOAD ABS DATA
# ============================================================

CSV_PATH = "poblacio_abs/arees_basiques_de_salut_20260210.csv"
GEOM_COL = "Geometry"

df = pd.read_csv(CSV_PATH)
df[GEOM_COL] = df[GEOM_COL].apply(wkt.loads)

gdf = gpd.GeoDataFrame(
    df,
    geometry=GEOM_COL,
    crs="EPSG:4326"
)

# ============================================================
# MAP 1 — ONLY ABS
# ============================================================

m1 = folium.Map(
    location=[41.3851, 2.1734],
    zoom_start=12
)

folium.GeoJson(
    gdf,
    name="Àrees Bàsiques de Salut",
    style_function=lambda feature: {
        "fillColor": "#1f78b4",
        "color": "black",
        "weight": 0.8,
        "fillOpacity": 0.45,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=[
            "Codi",
            "Nom",
            "Nom sector sanitari",
            "Nom regió sanitària"
        ],
        aliases=[
            "Codi ABS:",
            "Nom:",
            "Sector sanitari:",
            "Regió sanitària:"
        ],
        sticky=True
    )
).add_to(m1)

folium.LayerControl().add_to(m1)
m1.save("abs_barcelona_map.html")
print("Mapa 1 creat: abs_barcelona_map.html")


# ============================================================
# MAP 2 — ABS + EDGES SUPERPOSED
# ============================================================

m2 = folium.Map(
    location=[41.3851, 2.1734],
    zoom_start=12
)

# --- ABS Layer ---
abs_layer = folium.FeatureGroup(name="Àrees Bàsiques de Salut")

folium.GeoJson(
    gdf,
    style_function=lambda feature: {
        "fillColor": "#1f78b4",
        "color": "black",
        "weight": 0.8,
        "fillOpacity": 0.35,
    },
    tooltip=folium.GeoJsonTooltip(
        fields=[
            "Codi",
            "Nom",
            "Nom sector sanitari",
            "Nom regió sanitària"
        ],
        aliases=[
            "Codi ABS:",
            "Nom:",
            "Sector sanitari:",
            "Regió sanitària:"
        ],
        sticky=True
    )
).add_to(abs_layer)

abs_layer.add_to(m2)


# --- EDGES Layer ---
edges_layer = folium.FeatureGroup(name="Emergency Corridors")

with open("emergency_corridors/corridor_edges.json", "r") as f:
    edges_data = json.load(f)

for edge in edges_data:
    latlon = edge["coordinates"]
    style = edge.get("style", {})
    color = style.get("color", "lightgray")
    weight = style.get("weight", 1)
    opacity = style.get("opacity", 0.15)
    edge_id = edge.get("id", "")

    folium.PolyLine(
        latlon,
        color=color,
        weight=weight,
        opacity=opacity,
        tooltip=f"Edge ID: {edge_id}"
    ).add_to(edges_layer)

origin_coordinates = [
    # (longitude, latitude, name)
    (2.1539471460882837,41.38902661612551, "Hospital Clinic"),      # Hospital Clinic
    (2.1746345998135195, 41.416019562159505, "Hospital Sant Pau"),    # Hospital Sant Pau
    (2.194270345996985, 41.38586076739082, "Hospital del Mar"),     # Hospital del Mar
    (2.1428412773627437, 41.42673883887742, "Hospital Vall d'Hebron"),  # Hospital Sant Joan de Déu
    # Add more as needed
]
for v in origin_coordinates:
    folium.CircleMarker(
        location=(v[1], v[0]),
        radius=8,
        color="blue",
        fill=True,
        fill_color="blue",
        fill_opacity=1,
        tooltip=f"{v[2]}",
    ).add_to(edges_layer)

edges_layer.add_to(m2)

coords = []
with open("coords.json", "r") as f:
    coords = json.load(f)
    
for v in coords.values():
    folium.CircleMarker(
        location=(v["lat"], v["lon"]),
        radius=5,
        color="red",
        fill=True,
        fill_color="red",
        fill_opacity=1,
    ).add_to(edges_layer)
# --- Layer Control ---
folium.LayerControl(collapsed=False).add_to(m2)

m2.save("abs_plus_edges_map_2.html")
print("Mapa 2 creat: abs_plus_edges_map.html")
