import math
import folium


def haversine(lat1, lon1, lat2, lon2):
    R = 6371000 
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def points_every_step(lat1, lon1, lat2, lon2, step=200):
    total_dist = haversine(lat1, lon1, lat2, lon2)
    num_points = int(total_dist // step)

    points = []
    for i in range(num_points + 1):
        f = (i * step) / total_dist
        lat = lat1 + f * (lat2 - lat1)
        lon = lon1 + f * (lon2 - lon1)
        points.append((lat, lon))
    
    if points[-1] != (lat2, lon2):
        points.append((lat2, lon2))

    return points


latNE, lonNE = 41.45451661930665, 2.190474756351841
latSE, lonSE = 41.41145017579832, 2.2192432393629677
latS, lonS = 41.37382938880439, 2.1723010626498644
latSW, lonSW = 41.36643411525765, 2.1347150787997315
latNW, lonNW = 41.38990024609306, 2.1086975327862962
latN, lonN = 41.42905922158699, 2.1376188612005067

puntsNE_SE = []
puntsSE_S = []
puntsS_SW = []
puntsSW_NW = []
puntsNW_N = []
puntsN_NE = []

def get_points(distance):
    puntsNE_SE = points_every_step(latNE, lonNE, latSE, lonSE, distance)
    puntsSE_S = points_every_step(latSE, lonSE, latS, lonS, distance)
    puntsS_SW = points_every_step(latS, lonS, latSW, lonSW, distance)
    puntsSW_NW = points_every_step(latSW, lonSW, latNW, lonNW, distance)
    puntsNW_N = points_every_step(latNW, lonNW, latN, lonN, distance)
    puntsN_NE = points_every_step(latN, lonN, latNE, lonNE, distance)
    print(f" the total points considered for this simulation is {len(puntsNE_SE) + len(puntsSE_S) + len(puntsS_SW) + len(puntsSW_NW) + len(puntsNW_N) + len(puntsN_NE)}")
    
    return puntsNE_SE, puntsSE_S, puntsS_SW, puntsSW_NW, puntsNW_N, puntsN_NE


mapa = folium.Map(location=[41.40371878522945, 2.174445524020986], zoom_start=13)
for p in puntsNE_SE:
    folium.Marker( location=[ p[0], p[1] ],  icon=folium.Icon(color="red") ).add_to( mapa )
for p in puntsSE_S:
    folium.Marker( location=[ p[0], p[1] ],  icon=folium.Icon(color="green")).add_to( mapa )
for p in puntsS_SW:
    folium.Marker( location=[ p[0], p[1] ],  icon=folium.Icon(color="red")).add_to( mapa )
for p in puntsSW_NW:
    folium.Marker( location=[ p[0], p[1] ],  icon=folium.Icon(color="green")).add_to( mapa )
for p in puntsNW_N:
    folium.Marker( location=[ p[0], p[1] ],  icon=folium.Icon(color="red")).add_to( mapa )
for p in puntsN_NE:
    folium.Marker( location=[ p[0], p[1] ],  icon=folium.Icon(color="green")).add_to( mapa )

mapa.save("map_with_possible_points.html")