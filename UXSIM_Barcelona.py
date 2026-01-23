from graph_creator import *
from uxsim import *
import pandas as pd
from IPython.display import display
import time
import statistics as statis
from coordinates_treatment import *
import random

max_time = 2000
deltan = 5
reaction_time = 1

#region Set the edge parameters
"""
G, pos, colors, edges, junctions = create_graph('UXSIM/osm.net_2.xml')
junct = pd.DataFrame(columns=["id","incoming","x","y"])
i = 0
for j in junctions.values():
    junct.loc[i] = [j.id, j.incoming, j.x, j.y]
    i += 1

edg = pd.DataFrame(columns=["id", "lanes","length", "speed", "k_jam", "inc_x", "inc_y", "out_x", "out_y"])
i = 0
for e in edges.values():
    try:    
        o_n = junct.loc[junct["id"] == e.outgoing_edges].iloc[0]
        d_n = junct.loc[junct["id"] == e.incoming_edges].iloc[0]
        edg.loc[i] = [e.id, e.lanes, e.length, e.speed, 1000/6.36*e.lanes, o_n["x"], o_n["y"], d_n["x"], d_n["y"]]
        i += 1
    except:
        k = 2
edg.to_parquet("edges.parquet", index=False)
junct.to_parquet("junctions.parquet", index=False)
#endregion
"""
#region Work with the traffic set by edges

#G, pos, colors, edges, junctions = create_graph('osm.net_Barcelona.xml')
G, pos, colors, edges, junctions = create_graph('UXSIM/osm.net_2.xml')

W = World(
    name="Barcelona_completa_3",
    deltan=deltan,
    reaction_time=reaction_time,
    tmax=max_time,
    print_mode=1, save_mode=1, show_mode=1,
    random_seed=0,
    duo_update_time=600, duo_update_weight=0.5, duo_noise=0.01, route_choice_principle="homogeneous_DUO", route_choice_update_gradual=False, instantaneous_TT_timestep_interval=5, 
)
for j in junctions.values():
    W.addNode(name=j.id, x=float(j.x), y=float(j.y))

for e in edges.values():
    W.addLink(name=e.id, start_node=e.incoming_edges, end_node=e.outgoing_edges,
          length=max(round(float(e.length)),1), free_flow_speed=max(round(float(e.speed)),1), number_of_lanes=max(round(float(e.lanes)),1))
"""
i = 0
while i < 1:
    origin = random.choice(list(junctions.keys()))
    destination = random.choice(list(junctions.keys()))
    W.adddemand(origin, destination, i, i+25, random.uniform(10, 15))
    origin = random.choice(list(junctions.keys()))
    destination = random.choice(list(junctions.keys()))
    W.adddemand(origin, destination, i, i+50, random.uniform(13, 17))
    origin = random.choice(list(junctions.keys()))
    destination = random.choice(list(junctions.keys()))
    W.adddemand(origin, destination, i, i+35, random.uniform(21, 22))
    origin = random.choice(list(junctions.keys()))
    destination = random.choice(list(junctions.keys()))
    W.adddemand(origin, destination, i, i+24, random.uniform(12, 29))
    origin = random.choice(list(junctions.keys()))
    destination = random.choice(list(junctions.keys()))
    W.adddemand(origin, destination, i, i+45, random.uniform(1, 24))
    origin = random.choice(list(junctions.keys()))
    destination = random.choice(list(junctions.keys()))
    i += 1
"""
W.save_scenario("escenari_petit")
#endregion

W = World()
nodes, links = World.load_scenario(W,"Barcelona_Completa")
W.TMAX = 4000
W.name = "Test_for_complete_barcelona_2"
traffic = 0.1
time_traffic = 1000
"""
#region  E--> W
#RAZZ --> PL ESPANYA
W.adddemand_area2area2(2.1910058153933245, 41.39784487894918, 0.000898*3, 2.1518836051834, 41.377184304172175, 0.000898*3, 0, time_traffic, traffic )
#RAZZ --> SANTS
W.adddemand_area2area2(2.1910058153933245, 41.39784487894918, 0.000898*3, 2.1518836051834, 41.377184304172175, 0.000898*3, 0, time_traffic, traffic )
#RAZZ --> PARIS_TARRADELLES
W.adddemand_area2area2(2.1910058153933245, 41.39784487894918, 0.000898*3, 2.1518836051834, 41.377184304172175, 0.000898*3, 0, time_traffic, traffic )
#L'AUDITORI --> PL ESPANYA
W.adddemand_area2area2(2.1834959345843443, 41.39737388125027, 0.000898*3, 2.1518836051834, 41.377184304172175, 0.000898*3, 0, time_traffic, traffic )
#L'AUDITORI --> SANTS
W.adddemand_area2area2(2.1834959345843443, 41.39737388125027, 0.000898*3, 2.1518836051834, 41.377184304172175, 0.000898*3, 0, time_traffic, traffic )
#L'AUDITORI --> PARIS_TARRADELLES
W.adddemand_area2area2(2.1834959345843443, 41.39737388125027, 0.000898*3, 2.1518836051834, 41.377184304172175, 0.000898*3, 0, time_traffic, traffic )
#GLORIES --> PL ESPANYA
W.adddemand_area2area2(2.1864119207487254, 41.40314701241495, 0.000898*3, 2.1518836051834, 41.377184304172175, 0.000898*3, 0, time_traffic, traffic )
#GLORIES --> SANTS
W.adddemand_area2area2(2.1864119207487254, 41.40314701241495, 0.000898*3, 2.1518836051834, 41.377184304172175, 0.000898*3, 0, time_traffic, traffic )
#GLORIES --> PARIS_TARRADELLES
W.adddemand_area2area2(2.1864119207487254, 41.40314701241495, 0.000898*3, 2.1518836051834, 41.377184304172175, 0.000898*3, 0, time_traffic, traffic )
#endregion

#region W --> E
#PL ESPANYA --> RAZZ
W.adddemand_area2area2(2.1518836051834, 41.377184304172175, 0.000898*3, 2.1910058153933245, 41.39784487894918, 0.000898*3, 0, time_traffic, traffic )
#PL ESPANYA --> L'AUDITORI
W.adddemand_area2area2(2.1518836051834, 41.377184304172175, 0.000898*3, 2.1834959345843443, 41.39737388125027, 0.000898*3, 0, time_traffic, traffic )
#PL ESPANYA --> GLORIES
W.adddemand_area2area2(2.1518836051834, 41.377184304172175, 0.000898*3, 2.1864119207487254, 41.40314701241495, 0.000898*3, 0, time_traffic, traffic )
#SANTS --> RAZZ
W.adddemand_area2area2(2.142605236350562, 41.38237266952552, 0.000898*3, 2.1910058153933245, 41.39784487894918, 0.000898*3, 0, time_traffic, traffic )
#SANTS --> L'AUDITORI
W.adddemand_area2area2(2.142605236350562, 41.38237266952552, 0.000898*3, 2.1834959345843443, 41.39737388125027, 0.000898*3, 0, time_traffic, traffic )
#SANTS --> GLORIES
W.adddemand_area2area2(2.142605236350562, 41.38237266952552, 0.000898*3, 2.1864119207487254, 41.40314701241495, 0.000898*3, 0, time_traffic, traffic )
#PARIS_TARRADELLES --> RAZZ
W.adddemand_area2area2(2.142617871646794, 41.38569821918521, 0.000898*3, 2.1910058153933245, 41.39784487894918, 0.000898*3, 0, time_traffic, traffic )
#PARIS_TARRADELLES --> L'AUDITORI
W.adddemand_area2area2(2.142617871646794, 41.38569821918521, 0.000898*3, 2.1834959345843443, 41.39737388125027, 0.000898*3, 0, time_traffic, traffic )
#PARIS_TARRADELLES --> GLORIES
W.adddemand_area2area2(2.142617871646794, 41.38569821918521, 0.000898*3, 2.1864119207487254, 41.40314701241495, 0.000898*3, 0, time_traffic, traffic )
#endregion

#region N --> S
#MARINA--> DIAGONAL_SICILIA
W.adddemand_area2area2(2.186760809819229, 41.39475269483569, 0.000898*3, 2.175002511446816, 41.40045252363546, 0.000898*3, 0, time_traffic, traffic )
#ARC DE TRIONF--> VERDAGER
W.adddemand_area2area2(2.179686362185908, 41.39169941176438, 0.000898*3, 2.167866529567611, 41.39887677448817, 0.000898*3, 0, time_traffic, traffic )
#Urquinaona--> DIAGONAL_ROGER_LLURIA
W.adddemand_area2area2(2.1732415429399263, 41.38926656914354, 0.000898*3, 2.1632935372472564, 41.39752220367918, 0.000898*3, 0, time_traffic, traffic )
#PL UNI--> JARDINETS DE GRACIA
W.adddemand_area2area2(2.1640114366404832, 41.38569497148233, 0.000898*3, 2.159311981359677, 41.396698512347605, 0.000898*3, 0, time_traffic, traffic )
#SANT ANTONI--> DIAGONAL_BALMES
W.adddemand_area2area2(2.1621233850851613, 41.37952456335646, 0.000898*3, 2.154613470457876, 41.39531084575437, 0.000898*3, 0, time_traffic, traffic )
#PARAL·LEL--> DIAGONAL_MUNTANER
W.adddemand_area2area2(2.167739621349403, 41.37517562555826, 0.000898*3, 2.1496482613474606, 41.39408485618872, 0.000898*3, 0, time_traffic, traffic )
#POBLE SEC--> PL FRANCESC MACIA
W.adddemand_area2area2(2.1604166622176115, 41.3751144275215, 0.000898*3, 2.1439731239991375, 41.392442713721515, 0.000898*3, 0, time_traffic, traffic )
#PL ESPANYA--> LA ILLA
W.adddemand_area2area2(2.1493439402331846, 41.37500423375397, 0.000898*3, 2.135239399502743, 41.39022616032509, 0.000898*3, 0, time_traffic, traffic )
#endregion

#region S --> N
#DIAGONAL_SICILIA --> MARINA
W.adddemand_area2area2(2.175002511446816, 41.40045252363546, 0.000898*3,2.186760809819229, 41.39475269483569, 0.000898*3, 0, time_traffic, traffic )
#VERDAGER --> ARC DE TRIONF
W.adddemand_area2area2(2.167866529567611, 41.39887677448817, 0.000898*3, 2.179686362185908, 41.39169941176438, 0.000898*3, 0, time_traffic, traffic )
#DIAGONAL_ROGER_LLURIA --> Urquinaona
W.adddemand_area2area2(2.1632935372472564, 41.39752220367918, 0.000898*3,2.1732415429399263, 41.38926656914354, 0.000898*3, 0, time_traffic, traffic )
#JARDINETS DE GRACIA --> PL UNI
W.adddemand_area2area2(2.159311981359677, 41.396698512347605, 0.000898*3, 2.1640114366404832, 41.38569497148233, 0.000898*3, 0, time_traffic, traffic )
#DIAGONAL_BALMES --> SANT ANTONI
W.adddemand_area2area2(2.154613470457876, 41.39531084575437, 0.000898*3, 2.1621233850851613, 41.37952456335646, 0.000898*3, 0, time_traffic, traffic )
#DIAGONAL_MUNTANER--> PARAL·LEL
W.adddemand_area2area2(2.1496482613474606, 41.39408485618872, 0.000898*3, 2.167739621349403, 41.37517562555826, 0.000898*3, 0, time_traffic, traffic )
#PL FRANCESC MACIA --> POBLE SEC
W.adddemand_area2area2(2.1439731239991375, 41.392442713721515, 0.000898*3, 2.1604166622176115, 41.3751144275215, 0.000898*3, 0, time_traffic, traffic )
#LA ILLA --> PL ESPANYA
W.adddemand_area2area2(2.135239399502743, 41.39022616032509, 0.000898*3, 2.1493439402331846, 41.37500423375397, 0.000898*3, 0, time_traffic, traffic )
#endregion
"""
#region Traffic data W-E
# SANTS:  2.142605236350562, 41.38237266952552
#PL MOLINA: 2.147248608720307, 41.40128926418698
#PL CAT: 2.170289472837438, 41.387362292555665
#GLORIES: 2.1864119207487254, 41.40314701241495
#LA MAQUINISTA: 2.1970493195741048, 41.440657791739056
#ZONA UNI: 2.113386935119557, 41.384877806836236
#PL KENNEDY:  2.1371405377788366, 41.4097181271445
#RAZZMATAZZ: 2.1910058153933245, 41.39784487894918
#L'AUDITORI: 2.1834959345843443, 41.39737388125027
#PL ESPANYA: 2.1518836051834, 41.377184304172175
#PARIS_JOSEP TARRADELLES: 2.142617871646794, 41.38569821918521
#endregion

#region Traffic data N-S
#Zona S:
#MARINA: 2.186760809819229, 41.39475269483569
#ARC DE TRIONF: 2.179686362185908, 41.39169941176438
#Urquinaona: 2.1732415429399263, 41.38926656914354
#PL UNI: 2.1640114366404832, 41.38569497148233
#SANT ANTONI: 2.1621233850851613, 41.37952456335646
#PARAL·LEL: 2.167739621349403, 41.37517562555826
#POBLE SEC: 2.1604166622176115, 41.3751144275215
#PL ESPANYA: 2.1493439402331846, 41.37500423375397

#ZONA N:
#LA ILLA: 2.135239399502743, 41.39022616032509
#PL FRANCESC MACIA: 2.1439731239991375, 41.392442713721515
#DIAGONAL_MUNTANER: 2.1496482613474606, 41.39408485618872
#DIAGONAL_BALMES: 2.154613470457876, 41.39531084575437
#JARDINETS DE GRACIA: 2.159311981359677, 41.396698512347605
#DIAGONAL_ROGER_LLURIA: 2.1632935372472564, 41.39752220367918
#VERDAGER: 2.167866529567611, 41.39887677448817
#DIAGONAL_ROGER_DE_FLOR: 2.171609402654212, 41.399628672339595
#DIAGONAL_SICILIA: 2.175002511446816, 41.40045252363546
#endregion


#region Traffic with points every X distance
distance = 200
puntsNE_SE, puntsSE_S, puntsS_SW, puntsSW_NW, puntsNW_N, puntsN_NE = get_points(distance)
punts_N = puntsNW_N + puntsN_NE
punts_W = puntsS_SW+ puntsSW_NW + puntsNW_N
punts_S = puntsSE_S+ puntsS_SW
for p in puntsNE_SE:
    final = random.choice(punts_W)
    W.adddemand_area2area2(p[1], p[0], distance/111320/2, final[1], final[0], distance/111320/2, 0, time_traffic, traffic)
    W.adddemand_area2area2(p[1], p[0], distance/111320/2, final[1], final[0], distance/111320/2, 0, time_traffic, traffic )
    W.adddemand_area2area2(p[1], p[0], distance/111320/2, final[1], final[0], distance/111320/2, 0, time_traffic, traffic )

#W.adddemand_area2area2(2.186760809819229, 41.39475269483569, distance/111320/2, 2.175002511446816, 41.40045252363546, distance/111320/2, 0, time_traffic, traffic )

#endregion
sample_time_between_timestamps = 2
W.show_progress_deltat_timestep = sample_time_between_timestamps
current_time = 0
results = []
average_time = []
time1 = time.perf_counter()
time2 = time.perf_counter()

def log_link_data(W):
    global current_time, results, time1, time2, average_time
    current_time += 5
    results_temporary = []
    time2 = time.perf_counter()
    elapsed_time = time2 - time1
    time1 = time2
    average_time.append(elapsed_time)
    for e in links:
        num_veh = W.get_link(e).num_vehicles
        results_temporary.append({"edge": e,"num_veh": num_veh})
        #if speed != free_flow_speed:
            #print(f"Link {e.id} has speed {speed} and {num_veh} vehicles (free flow speed: {free_flow_speed})")
    results.append({"time": current_time, "data": results_temporary})

W.user_function = log_link_data
#W.set_routing_mode("dynamic")
W.route_choice_principle = "DUE"
#W.route_choice_principle = "UE"
W.exec_simulation()

frames = []
for result in results:
    # Create a temporary DataFrame for each time step
    df = pd.DataFrame(result["data"])
    df["time"] = result["time"]  # add the time column
    frames.append(df)

# Combine all partial DataFrames into one
all_streets_df = pd.concat(frames, ignore_index=True)

# Save as Parquet
all_streets_df.to_parquet("simulation_results_TEST_AMB_PUNTS_RODEJANT_MAPA.parquet", index=False)

print(statis.mean(average_time))

#W.analyzer.print_simple_stats()
#W.analyzer.network_anim(animation_speed_inverse=10, timestep_skip=30, detailed=0, network_font_size=0)
#W.analyzer.network_fancy(animation_speed_inverse=10, sample_ratio=0.3, interval=3, trace_length=3, network_font_size=0)

