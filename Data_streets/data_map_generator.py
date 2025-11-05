import pandas as pd
import folium

# Carrega el CSV
df = pd.read_csv("transit_relacio_trams.csv")

# Crea el mapa centrat a Barcelona
mapa = folium.Map(location=[41.3851, 2.1734], zoom_start=13)

# Afegeix cada carrer com una línia

i = 0
for _, fila in df.iterrows():
    # Extreu totes les coordenades com a floats
    coords = [float(x) for x in fila['Coordenades'].split(',')]
    
    # Agrupa les coordenades en tuples (lat, lon)
    punts = [(coords[i+1], coords[i]) for i in range(0, len(coords), 2)]
    
    # Afegeix la polilínia al mapa
    folium.PolyLine(
        locations=punts,
        color='blue',
        weight=4,
        opacity=0.7,
        tooltip=fila['Descripció']
    ).add_to(mapa)
"""
for _, fila in df.iterrows():
    # Extreu les coordenades
    try:
        coords = [float(x) for x in fila['Coordenades'].split(',')]
        lon1, lat1, lon2, lat2 = coords

        # Afegeix la línia al mapa
        folium.PolyLine(
            locations=[(lat1, lon1), (lat2, lon2)],
            color='blue',
            weight=4,
            opacity=0.7,
            tooltip=fila['Descripció']
        ).add_to(mapa)
    except:
        print(f"Error processant la fila {i}: {fila['Coordenades']}")
    i += 1
"""
# Desa el mapa com a fitxer HTML
mapa.save("mapa_carrers.html")
print("Mapa creat: obre 'mapa_carrers.html' al navegador.")


