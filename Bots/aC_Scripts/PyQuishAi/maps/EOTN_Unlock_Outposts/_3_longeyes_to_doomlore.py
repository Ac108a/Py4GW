from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_3_longeyes_to_doomlore_ids = {
    "outpost_id": outpost_name_to_id["Longeyes Ledge"],  # 650
}

# 2) Outpost exit path (in outpost 'Longeyes Ledge')
_3_longeyes_to_doomlore_outpost_path = [
    (-22469.26, 13327.51),
    (-21791.32, 12595.53),
]

# 3) Explorable segments
_3_longeyes_to_doomlore_segments = [
    {
        # Grothmar Wardowns
        "map_id": explorable_name_to_id["Grothmar Wardowns"],  # 649
        "path": [
            (-18582.023437, 10399.527343),
            (-13987.378906, 10078.552734),
            (-10700.551757, 9990.495117),
            (-7340.849121, 9353.873046),
            (-4436.99707, 8518.824218),
            (-445.930755, 8262.40332),
            (3324.289062, 8156.203613),
            (7149.32666, 8494.817382),
            (11733.867187, 7774.760253),
            (15031.326171, 9167.790039),
            (18174.601562, 10689.784179),
            (20369.773437, 12352.75),
            (22427.097656, 14882.499023),
            (24355.289062, 15175.175781),
            (25188.230468, 15229.357421),
            (-16292.620117, -715.887329),
            (-13617.916992, 405.243469),
            (-13256.524414, 2634.142089),
            (-15958.702148, 6655.416015),
            (-14465.992187, 9742.127929),
            (-13779.127929, 11591.517578),
            (-14929.544921, 13145.501953),
            (-15581.598632, 13865.58496),
        ],
    },
    {
        "map_id": explorable_name_to_id["Grothmar Wardowns"],  # 649
        "path": [],  # no further walking once you arrive
    },
]
