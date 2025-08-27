from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_5_mountqinkai_ids = {
    "outpost_id": outpost_name_to_id["Aspenwood Gate - Luxon"],  # 389
}

# 2) Outpost exit path (in outpost 'Aspenwood Gate - Luxon')
_5_mountqinkai_outpost_path = [
    (-4268, 11628),
    (-5490, 13672),
]

# 3) Explorable segments
_5_mountqinkai_segments = [
    {
        # Mount Qinkai
        "map_id": explorable_name_to_id["Mount Qinkai"],  # 200
        "path": [
            (-8551, -9895, "Bless"),
            (-13046, -9347),
            (-17348, -9895),
            (-17929, -10300),
            (-14702, -6671),
            (-11080, -6126),
            (-13426, -2344),
            (-15055, -3226),
            (-9448, -283),
            (-9918, 2826),
            (-8721, 7682),
            (-3749, 8053),
            (-7474, -1144),
            (-9666, 2625),
            (-5895, -3959),
            (-3509, -8000),
            (-195, -9095),
            (6298, -8707),
            (3981, -3295),
            (496, -2581),
            (2069, 1127),
            (5859, 1599),
            (6412, 6572),
            (10507, 8140),
            (14403, 6938),
            (18080, 3127),
            (13518, -35),
            (13450, -6084),
            (13764, -4816),
            (13450, -6084),
            (15390, -8892),
            (13764, -4816),
        ],
    },
    {
        "map_id": explorable_name_to_id["Mount Qinkai"],  # 200
        "path": [],  # no further walking once you arrive
    },
]
