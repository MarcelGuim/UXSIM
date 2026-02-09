import pandas as pd
import folium

df = pd.read_csv("data_streets/2025_03_Marc_TRAMS_TRAMS.csv")

mapa = folium.Map(location=[41.3851, 2.1734], zoom_start=13)


i = 0
for _, fila in df.iterrows():
    coords = [float(x) for x in fila['Coordenades'].split(',')]
    
    punts = [(coords[i+1], coords[i]) for i in range(0, len(coords), 2)]
    
    folium.PolyLine(
        locations=punts,
        color='blue',
        weight=4,
        opacity=0.7,
        tooltip=fila['Descripció']
    ).add_to(mapa)

mapa.save("/data_streets/MAPA/mapa_carrers.html")
print("Mapa creat: obre 'mapa_carrers.html' al navegador.")


