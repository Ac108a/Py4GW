from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_6_saoshangtrail_ids = {
    "outpost_id": outpost_name_to_id["Seitung Harbor"],  # 250
}

# 2) Outpost exit path (in outpost 'Seitung Harbor')
_6_saoshangtrail_outpost_path = [
    (16589, 13096),
    (16200, 13500),
]

# 3) Explorable segments
_6_saoshangtrail_segments = [
    {
        # Saoshang Trail
        "map_id": explorable_name_to_id["Saoshang Trail"],  # 313
        "path": [
            (15519, 13409),
            (14502, 13165),
            (12763, 12433),
            (9805, 10947),
            (8691, 11878),
            (8329, 12867),
            (7215, 13842),
            (6003, 13827),
            (3584, 10280),
        ],
    },
    {
        "map_id": explorable_name_to_id["Saoshang Trail"],  # 313
        "path": [],  # no further walking once you arrive
    },
]
