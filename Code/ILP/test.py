import json
import folium

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
