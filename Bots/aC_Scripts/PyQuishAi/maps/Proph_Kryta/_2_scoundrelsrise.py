from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_2_scoundrelsrise_ids = {
    "outpost_id": outpost_name_to_id["Gates of Kryta outpost"],  # 14
}

# 2) Outpost exit path (in outpost 'Gates of Kryta outpost')
_2_scoundrelsrise_outpost_path = [
    (-1453.6, 24938.46),
    (-4334.29, 26859.33),
]

# 3) Explorable segments
_2_scoundrelsrise_segments = [
    {
        # Scoundrel's Rise
        "map_id": explorable_name_to_id["Scoundrel's Rise"],  # 54
        "path": [
            (0, 0),
            (-470, -2966),
            (2763, -2033),
            (4006, -1526),
            (4030, -1364),
            (4333, -1079),
            (5013, -591),
            (4648, -167),
            (3978, 494),
            (2655, 1441),
            (2199, 2371),
            (2159, 2464),
            (2892, 2837),
            (3772, 3968),
            (3751, 4621),
            (5106, 4888),
            (6761, 4999),
            (7683, 6114),
            (6914, 7092),
            (6540, 7500),
            (4766, 8885),
            (4359, 8553),
            (3501, 7961),
            (2428, 5685),
            (2327, 5658),
            (791, 5064),
            (-37, 6023),
            (-672, 7194),
            (-2283, 7737),
            (-4571, 8588),
            (-5158, 8757),
            (-5340, 8925),
            (-3183, 8086),
            (-2535, 6465),
            (-2394, 5688),
            (-3686, 4096),
            (-3978, 3326),
            (-4439, 2268),
            (-3522, 4099),
            (-2551, 5576),
            (-668, 4943),
            (1202, 3009),
            (-4843, 1061),
        ],
    },
    {
        "map_id": explorable_name_to_id["Scoundrel's Rise"],  # 54
        "path": [],  # no further walking once you arrive
    },
]
