from graph_creator import *
from uxsim import *
from coordinates_treatment import *
import random
import pyarrow as pa
import pyarrow.parquet as pq
import gc
import os


MAX_TIME = 3600 * 3
LOG_INTERVAL = 5  #Cada 5 segons pren una mostra
WRITE_EVERY = 6   #Cada 6 mostres ho guarda a memoria
MAX_VEHICLES = 150_000



def run_simulation(k, j):
    W = World()
    nodes, links = World.load_scenario(W, "Barcelona_Completa")
    W.TMAX = MAX_TIME
    W.name = "Test_for_complete_barcelona_2"

    traffic = j
    distance = k

    puntsNE_SE, puntsSE_S, puntsS_SW, puntsSW_NW, puntsNW_N, puntsN_NE = get_points(distance)
    punts_N = puntsNW_N + puntsN_NE
    punts_W = puntsS_SW + puntsSW_NW
    punts_S = puntsSE_S + puntsS_SW

    total_points = (
        len(puntsNE_SE)
        + len(punts_N)
        + len(punts_S)
        + len(punts_W)
    )

    time_traffic = 3600
    total_veh = total_points * j * time_traffic
    if total_veh > MAX_VEHICLES:
        time_traffic = round(MAX_VEHICLES / (total_points * j))

    for p in puntsNE_SE:
        final = random.choice(punts_W)
        W.adddemand_area2area2(
            p[1], p[0], distance / 111320 / 2,
            final[1], final[0], distance / 111320 / 2,
            0, time_traffic, traffic
        )

    for p in punts_N:
        final = random.choice(punts_S)
        W.adddemand_area2area2(
            p[1], p[0], distance / 111320 / 2,
            final[1], final[0], distance / 111320 / 2,
            0, time_traffic, traffic
        )

    for p in punts_W:
        final = random.choice(puntsNE_SE)
        W.adddemand_area2area2(
            p[1], p[0], distance / 111320 / 2,
            final[1], final[0], distance / 111320 / 2,
            0, time_traffic, traffic
        )

    for p in punts_S:
        final = random.choice(punts_N)
        W.adddemand_area2area2(
            p[1], p[0], distance / 111320 / 2,
            final[1], final[0], distance / 111320 / 2,
            0, time_traffic, traffic
        )

    os.makedirs("RESULTS", exist_ok=True)
    output_path = (
        f"RESULTS/simulation_results_TEST_AMB_PUNTS_RODEJANT_MAPA_"
        f"k{k}_j{j}_t{time_traffic}.parquet"
    )

    schema = pa.schema([
        ("edge", pa.dictionary(pa.int32(), pa.string())),
        ("num_veh", pa.int32()),
        ("time", pa.int32()),
        ("k", pa.int32()),
        ("j", pa.float32())
    ])

    parquet_writer = pq.ParquetWriter(
        output_path,
        schema,
        compression="snappy"
    )

    buffer_edge = []
    buffer_veh = []
    buffer_time = []
    buffer_k = []
    buffer_j = []

    current_time = 0
    steps_since_write = 0

    def log_link_data(W):
        nonlocal current_time, steps_since_write

        current_time += LOG_INTERVAL
        if current_time < MAX_TIME / 3:
            return

        for e in links:
            buffer_edge.append(e)
            buffer_veh.append(W.get_link(e).num_vehicles)
            buffer_time.append(current_time)
            buffer_k.append(k)
            buffer_j.append(j)

        steps_since_write += 1

        if steps_since_write >= WRITE_EVERY:
            table = pa.Table.from_arrays(
                [
                    pa.array(buffer_edge),
                    pa.array(buffer_veh),
                    pa.array(buffer_time),
                    pa.array(buffer_k),
                    pa.array(buffer_j)
                ],
                schema=schema
            )

            parquet_writer.write_table(table)

            buffer_edge.clear()
            buffer_veh.clear()
            buffer_time.clear()
            buffer_k.clear()
            buffer_j.clear()
            steps_since_write = 0

            del table

    W.user_function = log_link_data
    W.route_choice_principle = "DUE"
    W.exec_simulation()

    
    if buffer_edge:
        table = pa.Table.from_arrays(
            [
                pa.array(buffer_edge),
                pa.array(buffer_veh),
                pa.array(buffer_time),
                pa.array(buffer_k),
                pa.array(buffer_j)
            ],
            schema=schema
        )
        parquet_writer.write_table(table)
        del table

    parquet_writer.close()

    # Eliminar totes les dades d'una simulació previ a fer la següent, per no enmagatzemar indefinidament dades
    del W, nodes, links
    buffer_edge.clear()
    buffer_veh.clear()
    buffer_time.clear()
    buffer_k.clear()
    buffer_j.clear()
    gc.collect()


k = 275
j_start = 0.2

while k > 74.9:
    j = j_start
    while j < 2.1:
        run_simulation(k, j)
        j += 0.2
    k -= 25
