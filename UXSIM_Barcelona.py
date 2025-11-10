from graph_creator import *
from uxsim import *
from uxsim.ResultGUIViewer import ResultGUIViewer
import pandas as pd
from IPython.display import display
from uxsim.DTAsolvers import *
import time

max_time = 1500
deltan = 5
reaction_time = 1

"""
G, pos, colors, edges, junctions = create_graph('osm.net_Barcelona.xml')
#G, pos, colors, edges, junctions = create_graph('osm.net_2.xml').

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


#W.save_scenario("Barcelona_Completa")
W = World()
World.load_scenario(W,"Barcelona_Completa")

#SANTS --> PL MOLINA
W.adddemand_area2area2(2.142605236350562, 41.38237266952552, 0.000898*2, 2.147248608720307, 41.40128926418698, 0.000898*2, 0, 100, 15 )
#ZONA UNI--> GLORIES
W.adddemand_area2area2(2.113386935119557, 41.384877806836236, 0.000898*2, 2.1864119207487254, 41.40314701241495, 0.000898*2, 0, 100, 15 )
#PL CAT --> PL KENNEDY
W.adddemand_area2area2(2.170289472837438, 41.387362292555665, 0.000898*2, 2.1371405377788366, 41.4097181271445, 0.000898*2, 0, 100, 15 )



# SANTS:  2.142605236350562, 41.38237266952552
#PL MOLINA: 2.147248608720307, 41.40128926418698
#PL CAT: 2.170289472837438, 41.387362292555665
#GLORIES: 2.1864119207487254, 41.40314701241495
#LA MAQUINISTA: 2.1970493195741048, 41.440657791739056
#ZONA UNI: 2.113386935119557, 41.384877806836236
#PL KENNEDY:  2.1371405377788366, 41.4097181271445

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
    for e in edges.values():
        speed = W.get_link(e.id).speed
        num_veh = W.get_link(e.id).num_vehicles
        free_flow_speed = W.get_link(e.id).free_flow_speed
        results_temporary.append({"edge": e.id,"num_veh": num_veh, "speed": speed, "free_flow_speed": free_flow_speed})
        #if speed != free_flow_speed:
            #print(f"Link {e.id} has speed {speed} and {num_veh} vehicles (free flow speed: {free_flow_speed})")
    results.append({"time": current_time, "data": results_temporary})

#W.user_function = log_link_data
#W.set_routing_mode("dynamic")
W.route_choice_principle = "DUE"
#W.route_choice_principle = "UE"
W.exec_simulation()
"""
with open('simulation_results_1.csv', 'w', newline='') as csvfile:
    fieldnames = ['time', 'edge', 'num_veh', 'speed', 'free_flow_speed']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for result in results:
        for data in result["data"]:
            writer.writerow({"time": result["time"], **data})
"""
W.analyzer.print_simple_stats()
"""
total_average_time = sum(average_time) / len(average_time)
print(f"Average time per log_link_data call: {total_average_time} seconds")
W.adddemand_area2area2
"""
"""
#overall
df = W.analyzer.basic_to_pandas()
display(df)

#OD-specific traffic situation
df = W.analyzer.od_to_pandas()
display(df)

#MFD
df = W.analyzer.mfd_to_pandas()
display(df)
"""
"""
#within link
df = W.analyzer.link_traffic_state_to_pandas()
display(df)
df.to_csv('link_traffic.csv', index=False)

#vehicle-level
df = W.analyzer.vehicles_to_pandas()
display(df)
df.to_csv('vehicles.csv', index=False)
W.analyzer.output_data()
"""
"""
"""
W.analyzer.network_anim(animation_speed_inverse=10, timestep_skip=30, detailed=0, network_font_size=0)
W.analyzer.network_fancy(animation_speed_inverse=10, sample_ratio=0.3, interval=3, trace_length=3, network_font_size=0)
