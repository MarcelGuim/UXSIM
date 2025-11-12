from uxsim import *
# Simulation main
W = World(
    name="simple_demo",
    deltan=5,
    tmax=7200,
    print_mode=1, save_mode=1, show_mode=1,
    random_seed=0
)
W.route_pref_for_vehs = 0
# Scenario definition
W.load_scenario("sfnetwork.uxsim_scenario")
edges = W.get_link()
# Simulation execution
W.exec_simulation()

# Results analysis
W.analyzer.print_simple_stats()

W.analyzer.network_anim(animation_speed_inverse=15, timestep_skip=8, detailed=0, network_font_size=0)

W.adddemand(orig="orig1", dest="dest", t_start=0, t_end=1000, flow=0.45)
W.adddemand(orig="orig2", dest="dest", t_start=400, t_end=1000, flow=0.6)
