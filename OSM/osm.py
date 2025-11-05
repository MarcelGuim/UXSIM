from uxsim import *
from uxsim.OSMImporter import OSMImporter



W = World(
    name="",
    deltan=5,
    tmax=7200,
    print_mode=1, save_mode=1, show_mode=0,
    random_seed=0
)

#nodes, links = OSMImporter.import_osm_data(bbox=(139.583, 35.570, 139.881, 35.817), custom_filter='["highway"~"motorway"]')
nodes, links = OSMImporter.import_osm_data(bbox=(1.9745977467234008,41.2738696217509, 1.9820328298739145, 41.27252301703546), custom_filter='["highway"~"motorway"~"trunk"~"primary"~"secondary"~"residential"~"tertiary"]')

OSMImporter.osm_network_visualize(nodes, links, show_link_name=0)
OSMImporter.osm_network_visualize(nodes, links, show_link_name=0, xlim=[139.75, 139.76], ylim=[35.60, 35.615], figsize=(6,6))