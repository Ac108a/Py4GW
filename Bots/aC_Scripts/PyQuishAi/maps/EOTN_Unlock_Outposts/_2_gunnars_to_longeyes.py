from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_2_gunnars_to_longeyes_ids = {
    "outpost_id": outpost_name_to_id["Gunnar's Hold"],  # 644
}

# 2) Outpost exit path (in outpost 'Gunnar's Hold')
_2_gunnars_to_longeyes_outpost_path = [
    (15886.2, -6687.81),
    (15183.19, -6381.95),
]

# 3) Explorable segments
_2_gunnars_to_longeyes_segments = [
    {
        # Norrhart Domains
        "map_id": explorable_name_to_id["Norrhart Domains"],  # 548
        "path": [
            (14233.820312, -3638.702636),
            (14944.690429, 1197.740966),
            (14855.548828, 4450.144531),
            (17964.738281, 6782.413574),
            (19127.484375, 9809.458984),
            (21742.705078, 14057.231445),
            (19933.86914, 15609.05957),
            (16294.676757, 16369.736328),
            (16392.476562, 16768.855468),
            (-11232.550781, -16722.859375),
            (-7655.780273, -13250.316406),
            (-6672.132324, -13080.853515),
            (-5497.732421, -11904.576171),
            (-3598.337646, -11162.589843),
            (-3013.92749, -9264.664062),
            (-1002.166198, -8064.565429),
            (3533.099609, -9982.698242),
            (7472.125976, -10943.370117),
            (12984.513671, -15341.864257),
            (17305.523437, -17686.404296),
            (19048.208984, -18813.695312),
            (19634.173828, -19118.777343),
        ],
    },
    {
        "map_id": explorable_name_to_id["Norrhart Domains"],  # 548
        "path": [],  # no further walking once you arrive
    },
]
