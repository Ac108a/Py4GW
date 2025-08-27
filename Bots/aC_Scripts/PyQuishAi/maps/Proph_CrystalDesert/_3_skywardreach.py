from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_3_skywardreach_ids = {
    "outpost_id": outpost_name_to_id["Augury Rock outpost"],  # 38
}

# 2) Outpost exit path (in outpost 'Augury Rock outpost')
_3_skywardreach_outpost_path = [
    (-15225.14, 1966.78),
    (-15233.08, 2352.49),
]

# 3) Explorable segments
_3_skywardreach_segments = [
    {
        # Skyward Reach
        "map_id": explorable_name_to_id["Skyward Reach"],  # 115
        "path": [
            (-12517, 4131),
            (-11612, -1888),
            (-11216, -5092),
            (-7847, -8855),
            (-4358, -10956),
            (-620, -14121),
            (2951, -16579),
            (5878, -17416),
        ],
    },
    {
        "map_id": explorable_name_to_id["Skyward Reach"],  # 115
        "path": [],  # no further walking once you arrive
    },
]
