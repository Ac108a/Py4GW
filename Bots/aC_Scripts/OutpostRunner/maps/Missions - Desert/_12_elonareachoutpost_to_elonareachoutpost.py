from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_1_elonareachoutpost_to_elonareachoutpost_ids = {
    "outpost_id": 118,
}

# 2) Outpost exit path
_1_elonareachoutpost_to_elonareachoutpost_outpost_path = [
    (15583, 6959, "EnterMission", 12000),
]

# 3) Segments
_1_elonareachoutpost_to_elonareachoutpost_segments = [
    {
        "map_id": 118,
        "path": [
            (14088, -514, "Interact"),
            (14117, 2562),
            (15654, 1699),
            (17572, 1505),
            (15654, 1699),
            (10510, 3434),
            (7543, 3253),
            (4888, 4133),
            (3366, 4906, "Interact"),


        ],
    },
    {
        "map_id": 118,
        "path": [],  # no further walking once you arrive
    },
]
