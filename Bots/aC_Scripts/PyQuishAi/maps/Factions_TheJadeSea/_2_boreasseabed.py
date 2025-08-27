from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_2_boreasseabed_ids = {
    "outpost_id": outpost_name_to_id["Zos Shivros Channel outpost"],  # 273
}

# 2) Outpost exit path (in outpost 'Zos Shivros Channel outpost')
_2_boreasseabed_outpost_path = [
    (3476, 6599),
    (3510, 7400),
]

# 3) Explorable segments
_2_boreasseabed_segments = [
    {
        # Boreas Seabed (explorable area)
        "map_id": explorable_name_to_id["Boreas Seabed (explorable area)"],  # 247
        "path": [
            (15139, -7063),
            (18288, -9106),
            (19930, -6525),
            (21821, -8140),
            (19603, -5849),
            (18616, -2516),
            (15500, -993),
            (12532, -1995),
            (9383, -1539),
            (7684, -1887),
            (7961, -4050),
            (11091, -6237),
            (7554, -7600),
            (2925, -6527),
            (-634, -5828),
            (-1275, -9005),
            (-5928, -5322),
            (-10598, -3114),
            (-9772, 1067),
            (-9158, 3230),
            (-10241, 5109),
            (-7839, 4851),
            (-10869, 7276),
            (-11256, 9728),
            (-8200, 9981),
            (-3190, 9801),
            (-2424, 8451),
            (-1763, 3630),
            (-4181, 113),
            (1951, -984),
            (3271, 957),
            (4828, 5135),
            (8367, 8549),
            (10923, 5254),
            (14184, 4152),
            (17822, 2507),
            (14220, 8099),
            (15520, 10111),
            (17418, 8581),
            (18973, 8433),
            (19623, 8179),
            (21803, 8558),
            (22850, 8471),
            (24070, 8805),
            (25243, 10408),
        ],
    },
    {
        "map_id": explorable_name_to_id["Boreas Seabed (explorable area)"],  # 247
        "path": [],  # no further walking once you arrive
    },
]
