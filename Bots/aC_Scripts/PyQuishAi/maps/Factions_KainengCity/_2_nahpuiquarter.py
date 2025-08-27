from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_2_nahpuiquarter_ids = {
    "outpost_id": outpost_name_to_id["Senjis Corner"],  # 51
}

# 2) Outpost exit path (in outpost 'Senjis Corner')
_2_nahpuiquarter_outpost_path = [
    (7574, -16106),
    (7400, -17000),
]

# 3) Explorable segments
_2_nahpuiquarter_segments = [
    {
        # Nahpui Quarter (explorable area)
        "map_id": explorable_name_to_id["Nahpui Quarter (explorable area)"],  # 265
        "path": [
            (10479, 12811),
            (10822, 11027),
            (15752, 10208),
            (19168, 6476),
            (18820, 4312),
            (15750, 2658),
            (14424, 2980),
            (14161, 5095),
            (12705, 5053),
            (12182, 2170),
            (11191, 2208),
            (11383, 6704),
            (7828, 6949),
            (6098, 7481),
            (7255, 5866),
            (7676, 3013),
            (9120, 1898),
            (8731, -953),
            (7041, -2578),
            (6766, -3769),
            (5559, -3803),
            (4281, -1961),
            (4808, -165),
            (4232, -1973),
            (5464, -3772),
            (6995, -3727),
            (7107, -2365),
            (10203, 850),
            (12413, 2402),
            (13003, 5214),
            (14315, 4919),
            (15544, -1093),
            (16140, -3882),
            (17113, 457),
            (20091, 1796),
            (20143, 227),
            (16584, -577),
            (16294, -5446),
            (18386, -5813),
            (20464, -8531),
            (18762, -11101),
            (14985, -11488),
            (12752, -10501),
            (13416, -6539),
            (12413, -3364),
            (13840, -2163),
        ],
    },
    {
        "map_id": explorable_name_to_id["Nahpui Quarter (explorable area)"],  # 265
        "path": [],  # no further walking once you arrive
    },
]
