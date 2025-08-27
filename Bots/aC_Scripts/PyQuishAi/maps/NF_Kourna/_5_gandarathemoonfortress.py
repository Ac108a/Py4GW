from Py4GWCoreLib.enums import outpost_name_to_id, explorable_name_to_id

# 1) IDs
_5_gandarathemoonfortress_ids = {
    "outpost_id": outpost_name_to_id["Pogahn Passage outpost"],  # 426
}

# 2) Outpost exit path (in outpost 'Pogahn Passage outpost')
_5_gandarathemoonfortress_outpost_path = [

    (3860, -1719),
    (2706, -4708),
    (2580, -4950),
]

# 3) Explorable segments
_5_gandarathemoonfortress_segments = [
    {
        # Gandara, the Moon Fortress
        "map_id": explorable_name_to_id["Gandara, the Moon Fortress"],  # 382
        "path": [
            (6818, 15641, "Bless"),
            (5425, 16446),
            (3246, 13158),
            (-2989, 14295),
            (-4304, 11465),
            (-1938, 11165),
            (-2396, 14301),
            (-6098, 15735),
            (-7412, 14230, "Bless"),
            (-10125, 14233),
            (-10210, 9811),
            (-12946, 12759),
            (-18180, 12670),
            (-23168, 14844),
            (-25047, 14113),
            (-23478, 10876),
            (-24154, 8734),
            (-23050, 4721),
            (-24672, 3577),
            (-24585, 3991),
            (-19619, 5662),
            (-22286, 9017),
            (-21070, 10317),
            (-18532, 12319),
            (-19967, 8553),
            (-15516, 9981),
            (-12782, 12508),
            (-11391, 10947),
            (-10171, 9954),
            (-10155, 12817),
            (-5469, 12312),
            (-2614, 14338),
            (3843, 12063),
            (6063, 10744),
            (9786, 11064),
            (11645, 10250),
            (12199, 7117),
            (15633, 9747),
            (14905, 13634),
            (19445, 9837),
            (22045, 9376),
            (21646, 6598),
            (22185, 4098),
            (21294, 3045),
            (18447, 6224),
        ],
    },
    {
        "map_id": explorable_name_to_id["Gandara, the Moon Fortress"],  # 382
        "path": [],  # no further walking once you arrive
    },
]
