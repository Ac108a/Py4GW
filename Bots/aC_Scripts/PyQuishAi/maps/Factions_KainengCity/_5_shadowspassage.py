from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_5_shadowspassage_ids = {
    "outpost_id": outpost_name_to_id["Dragons Throat outpost"],  # 274
}

# 2) Outpost exit path (in outpost 'Dragons Throat outpost')
_5_shadowspassage_outpost_path = [
    (-12290, 7648),
    (-12193, 8409),
    (-12182, 8800),
]

# 3) Explorable segments
_5_shadowspassage_segments = [
    {
        # Shadow's Passage
        "map_id": explorable_name_to_id["Shadow's Passage"],  # 232
        "path": [
            (3396, 16639),
            (2094, 18885),
            (61, 18889),
            (-682, 13737),
            (-3699, 14519),
            (-4255, 16101),
        ],
    },
    {
        "map_id": explorable_name_to_id["Shadow's Passage"],  # 232
        "path": [],  # no further walking once you arrive
    },
]
