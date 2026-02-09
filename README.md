# Barcelona Traffic Simulation

This project simulates traffic in the **city of Barcelona** under different scenarios. Each scenario defines a specific area of the city and includes both the full simulated network and a reduced network where traffic data is collected.

---

## 📁 Project Structure

Each scenario is stored in its own folder:

* `eixample/`
* `hospital_clinic/`
* `hospital_del_mar/`
* `hospital_sant_pau/`

Inside each scenario folder you will find **two `.kml` files**:

* **`<scenario>.kml`**
  Contains the **subset of edges** where traffic data is collected.

* **`<scenario>_full_edges.kml`**
  Contains the **full simulated network** used during the simulation.

> ℹ️ The full simulated scenario is intentionally larger than the data collection area. This helps eliminate instabilities caused by vehicles entering the simulation near the measurement boundaries.

---

## ➕ Adding a New Scenario

To simulate a new area in Barcelona:

1. Create a **new folder** with the scenario name.
2. Add the corresponding:

   * `<scenario>.kml`
   * `<scenario>_full_edges.kml`
3. Add the required rows for the new scenario in:

   * `Code/parameters.ini`

---

## ▶️ Running a Scenario

Follow these steps to run a simulation:

### 1️⃣ Select the Scenario

Open:

```
Code/parameters.ini
```

Set the scenario name **in lowercase**:

```
zone = eixample
```

---

### 2️⃣ Set the Simulation Number

In the same `parameters.ini` file, modify:

```
sim_num = X
```

* This value determines how results are stored.
* ⚠️ If the value is repeated, **existing data will be overwritten**.

---

### 3️⃣ Configure Simulation Parameters

Open:

```
Code/UXSIM_Barcelona.py
```

Modify the following parameters:

#### a) Scenario Loading

* `get_edges_and_junctions_parquet`

  * `True` → First time running this scenario
  * `False` → Scenario already processed

* `load_from_previously_saved`

  * `True` → Load an existing scenario
  * `False` → Create a new one

#### b) Traffic Settings

* `traffic` → Vehicles per second
* `time_traffic` → Duration of traffic generation
* `points` → Number of routes

#### c) Output & Visualization Options

Simulation results are **always saved as `.parquet` files**. Additionally, you can enable:

* 🗺️ **Maps with all edges**
  Uncomment the **first** `get_mapa_all_edges`

* 🗺️ **Maps with important edges only**
  Uncomment the **second** `get_mapa_all_edges`

* 🎞️ **Map GIF (every X minutes)**
  Uncomment `create_map_gif`

* 🚗 **UXSIM animated GIF with vehicles**
  Uncomment `W.analyzer.network_fancy`

---

### 4️⃣ Run the Simulation

Execute the simulation script after configuring all parameters.

---

### 5️⃣ Access the Results

All outputs are stored inside the selected scenario folder, organized as follows:

* `MAPA/` → Generated maps
* `GIF/` → Animated GIFs
* `RESULTS/` → Simulation data (`.parquet` files)

---