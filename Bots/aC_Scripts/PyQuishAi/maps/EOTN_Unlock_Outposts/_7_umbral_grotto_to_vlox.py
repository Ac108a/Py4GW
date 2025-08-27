from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_7_umbral_grotto_to_vlox_ids = {
    "outpost_id": outpost_name_to_id["Umbral Grotto"],  # 639
}

# 2) Outpost exit path (in outpost 'Umbral Grotto')
_7_umbral_grotto_to_vlox_outpost_path = [
    (-24463.52, 11560.54),
    (-26128.985, 10676.18),
]

# 3) Explorable segments
_7_umbral_grotto_to_vlox_segments = [
    {
        # Vloxen Excavations (level 1)
        "map_id": explorable_name_to_id["Vloxen Excavations (level 1)"],  # 604
        "path": [
            (-13807.78125, 16442.71875),
            (-14953.253906, 13218.502929),
            (-17230.427734, 9955.362304),
            (-16309.177734, 7241.766113),
            (-16266.636718, 5037.34082),
            (-17457.251953, 1882.958984),
            (-17889.46875, -1212.505981),
            (-16952.267578, -3971.341308),
            (-16952.267578, -3971.341308),
            (-17606.107421, -7403.375),
            (-16884.861328, -10819.688476),
            (-18920.699218, -11642.852539),
            (-19454.87304, -11828.13085),
            (-19921.515625, -11963.304687),
        ],
    },
    {
        "map_id": explorable_name_to_id["Vloxen Excavations (level 1)"],  # 604
        "path": [],  # no further walking once you arrive
    },
]
