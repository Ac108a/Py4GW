from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_8_unwakingwaters_ids = {
    "outpost_id": outpost_name_to_id["Harvest Temple"],  # 277
}

# 2) Outpost exit path (in outpost 'Harvest Temple')
_8_unwakingwaters_outpost_path = [
    (3355.47, 3054.54),
    (3355.47, 2300.54),
]

# 3) Explorable segments
_8_unwakingwaters_segments = [
    {
        # Unwaking Waters (explorable area)
        "map_id": explorable_name_to_id["Unwaking Waters (explorable area)"],  # 227
        "path": [
            (3464, 1917),
            (3078.88, 5448.03),
            (797.97, 3818.96),
            (1027.28, 1349.43),
            (3400.14, -1050.81),
            (7306.71, -550.47),
            (10527.24, -630.89),
            (14328.43, 1316.61),
            (10590.52, 3601.1),
            (7283.98, 82.61),
            (7086.35, 1018.25),
            (9502.52, 4770.71),
            (9641.66, 4987.45),
            (11014.83, 7214.74),
            (5983.94, 7500.72),
            (1518.7, 8470.11),
            (-1412.39, 6396.44),
            (-5065.51, 4624.91),
            (-8647.6, 2369.4),
            (-4920.25, -135.66),
            (-3720.08, 1924.34),
            (-2685, -954.1),
            (-1820.3, 2831.6),
        ],
    },
    {
        "map_id": explorable_name_to_id["Unwaking Waters (explorable area)"],  # 227
        "path": [],  # no further walking once you arrive
    },
]
