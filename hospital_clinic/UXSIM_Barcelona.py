from graph_creator import *
from file_parser import *
from uxsim import *
import pandas as pd
from IPython.display import display
import time
import statistics as statis
import random
import pyarrow as pa
import pyarrow.parquet as pq

#FER CONVERSIÓ DE LOS A PARTIR DE VELOCITAT EN COMPTES DE LOS A PARTIR DE COTXES QUE HI HA EN 
#AQUELL CARRER


#region Data format and functions
_buffer_edge = []
_buffer_veh = []
_buffer_speed = []
_buffer_time = []
_buffer_k = []
_buffer_j = []

EDGE_SCHEMA = pa.schema([
    ("edge", pa.dictionary(pa.int32(), pa.string())),
    ("num_veh", pa.int32()),
    ("speed_veh", pa.int32()),
    ("time", pa.int32()),
    ("k", pa.int32()),
    ("j", pa.float32()),
])

def collect_edge_data(edge_id: str,
                      num_veh: int,
                      speed_veh: int,
                      time: int,
                      k: int,
                      j: float):
    
    _buffer_edge.append(edge_id)
    _buffer_veh.append(int(num_veh))
    _buffer_speed.append(int(speed_veh))
    _buffer_time.append(int(time))
    _buffer_k.append(int(k))
    _buffer_j.append(float(j))

def flush_edge_data_to_disk(output_path: str):
    if not _buffer_edge:
        print("No data to write.")
        return

    table = pa.Table.from_arrays(
        [
            pa.array(_buffer_edge),
            pa.array(_buffer_veh),
            pa.array(_buffer_speed),
            pa.array(_buffer_time),
            pa.array(_buffer_k),
            pa.array(_buffer_j),
        ],
        schema=EDGE_SCHEMA
    )

    pq.write_table(
        table,
        output_path,
        compression="snappy"
    )
    _buffer_edge.clear()
    _buffer_veh.clear()
    _buffer_speed.clear()
    _buffer_time.clear()
    _buffer_k.clear()
    _buffer_j.clear()

#endregion

#region Get edges and junctions parquet
"""
edges, junctions = get_points_in_area(
    "hospital_clinic/hospital_clinic.kml", 
    "hospital_clinic/osm.net_BARCELONA.xml"
)
G, pos, colors, edges, junctions = create_graph(edges, junctions)

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
edg.to_parquet("hospital_clinic/edges_hospital_clinic.parquet", index=False)
junct.to_parquet("hospital_clinic/junctions_hospital_clincic.parquet", index=False)
"""
#endregion

simulation_name = "Hospital_Clinic_1"
max_time = 3600
deltan = 5
reaction_time = 1
duo_update_time=10
duo_update_weight=0.5 
duo_noise=0.01
route_choice_principle="homogeneous_DUO"
route_choice_update_gradual=False
instantaneous_TT_timestep_interval=5 
load_from_previously_saved = True
junctions = None
edges = None

if not load_from_previously_saved:
    print("loading from zero")
    edges, junctions = get_points_in_area(
        "hospital_clinic/hospital_clinic.kml", 
        "hospital_clinic/osm.net_BARCELONA.xml"
    )
    G, pos, colors, edges, junctions = create_graph(edges, junctions)
    W = World(
        name=simulation_name,
        deltan=deltan,
        reaction_time=reaction_time,
        tmax=max_time,
        print_mode=1, 
        save_mode=1, 
        show_mode=1,
        random_seed=0,
        duo_update_time=duo_update_time, 
        duo_update_weight=duo_update_weight, 
        duo_noise=duo_noise, 
        route_choice_principle=route_choice_principle, 
        route_choice_update_gradual=route_choice_update_gradual, 
        instantaneous_TT_timestep_interval=instantaneous_TT_timestep_interval, 
    )
    for j in junctions.values():
        W.addNode(name=j.id, x=float(j.x), y=float(j.y))

    for e in edges.values():
        W.addLink(name=e.id, start_node=e.incoming_edges, end_node=e.outgoing_edges,
            length=max(round(float(e.length)),1), free_flow_speed=max(round(float(e.speed)),1), number_of_lanes=max(round(float(e.lanes)),1))
    edges = [e.id for e in edges.values()]
    W.save_scenario("hospital_clinic_simulation")
else:
    print("loading from saved scenario")
    W = World()
    junctions, edges = World.load_scenario(W,"hospital_clinic_simulation")
    W.name=simulation_name
    W.DELTAN=deltan
    W.REACTION_TIME=reaction_time
    W.TMAX=max_time
    W.DUO_UPDATE_TIME=duo_update_time 
    W.DUO_UPDATE_WEIGHT=duo_update_weight 
    W.DUO_NOISE=duo_noise
    W.route_choice_principle=route_choice_principle 
    W.route_choice_update_gradual=route_choice_update_gradual 
    W.instantaneous_TT_timestep_interval=instantaneous_TT_timestep_interval 

#COSES A ANALITZAR EL SEU SIGNIFICAT
#W.set_routing_mode("dynamic")
#W.route_choice_principle = "DUE"


traffic = 0.05
time_traffic = 3000

sample_time_between_timestamps = 2
W.show_progress_deltat_timestep = sample_time_between_timestamps
current_time = 0
results = []
average_time = []
time1 = time.perf_counter()
time2 = time.perf_counter()

def log_link_data(W):
    global current_time, results, time1, time2, average_time
    current_time += deltan
    time2 = time.perf_counter()
    elapsed_time = time2 - time1
    time1 = time2
    average_time.append(elapsed_time)
    for e in edges:
        collect_edge_data(
            edge_id=e,
            num_veh=W.get_link(e).num_vehicles,
            speed_veh=W.get_link(e).speed,
            time=current_time,
            k=0,
            j=traffic
        )

#region Add random traffic
junction_list = None
if not load_from_previously_saved:
    junction_list = list(junctions.values())
    for _ in range(400):
        origin = random.choice(junction_list)
        destination = random.choice(junction_list)
        while destination.id == origin.id:
            destination = random.choice(junction_list)
        W.adddemand(
            origin.id,
            destination.id,
            0, 
            time_traffic,
            traffic
        )
else:
    junction_list = junctions
    for _ in range(1000):
        origin = random.choice(junction_list)
        destination = random.choice(junction_list)
        time_start = random.randint(0,time_traffic)
        time_end = random.randint(time_start,time_traffic)
        while destination == origin:
            destination = random.choice(junction_list)
        W.adddemand(
            origin,
            destination,
            time_start, 
            time_end,
            traffic
        )
#endregion

W.user_function = log_link_data
W.exec_simulation()

print(statis.mean(average_time))
W.analyzer.print_simple_stats()

flush_edge_data_to_disk(
    "hospital_clinic/RESULTS/simulation_results_TEST_AMB_PUNTS_RODEJANT_MAPA_9.parquet"
)

"""
W.analyzer.network_fancy(
    animation_speed_inverse=30, 
    sample_ratio=0.5, 
    interval=3, 
    trace_length=3, 
    network_font_size=0
    )
"""