from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_1_eotn_to_gunnars_ids = {
    "outpost_id": outpost_name_to_id["Eye of the North outpost"],  # 642
}

# 2) Outpost exit path (in outpost 'Eye of the North outpost')
_1_eotn_to_gunnars_outpost_path = [
    (332.8, 1432.14),
    (1203.26, 839.42),
]

# 3) Explorable segments
_1_eotn_to_gunnars_segments = [
    {
        # Ice Cliff Chasms
        "map_id": explorable_name_to_id["Ice Cliff Chasms"],  # 499
        "path": [
            (2324.802734, 5434.39746),
            (715.66925, 8835.476562),
            (504.575317, 11846.961914),
            (825.86853, 15970.333007),
            (173.692352, 20100.667968),
            (-2415.995361, 22778.201171),
            (-3309.545166, 24568.648437),
            (-3680.492919, 26832.4375),
            (-3818.726562, 27936.259765),
            (11973.490234, -12021.736328),
            (12131.014648, -9444.603515),
            (12851.580078, -7496.924804),
            (14836.394531, -6503.532714),
            (15347.208007, -6517.461914),
        ],
    },
    {
        "map_id": explorable_name_to_id["Ice Cliff Chasms"],  # 499
        "path": [],  # no further walking once you arrive
    },
]
