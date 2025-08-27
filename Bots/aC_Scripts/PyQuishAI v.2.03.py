from Py4GWCoreLib import *
from aC_api import *
from HeroAI.cache_data import *
from aC_api.Titles import (display_faction, display_title_progress,sunspear_tiers, lightbringer_tiers, kurzick_tiers, luxon_tiers,luxon_regions, kurzick_regions, nightfall_regions, eotn_region_titles)
from PyQuishAi.runner_singleton import runner_fsm
from PyQuishAi.map_loader import get_regions
from PyQuishAi.StatsManager import RunInfo
from Bots.aC_Scripts.Consumable import ConsumablesSelectorFull

module_name = "PyQuishAI "
cache_data = CacheData()

# UI state
show_stats_window = False
selected_region = None
selected_run    = None
selected_chain  = [] 
last_valid_next_point = None
# Cache
_cached_regions = None

# === STATIC FRIENDLY NAME MAP ===
RUN_NAME_MAP = {
    "EOTN_Charr_Homelands": {
        "_1_dalada_uplands": "1 - Dalada Uplands",
    },
    "EOTN_Far_Silverpeaks": {
        "_1_ice_cliff_chasms": "1 - Ice Cliff Chasms",
        "_2_norrhart_domains": "2 - Norrhart Domains",
        "_3_varajar_fells": "3 - Varajar Fells",
    },
    "EOTN_Tarnished_Coast": {
        "_1_alcaziatangle": "1 - Alcazia Tangle",
        "_2_arborbay": "2 - Arbor Bay",
        "_3_magusstones": "3 - Magus Stones",
        "_4_rivenearth": "4 - Riven Earth",

    },
    "EOTN_Unlock_Outposts": {
        "_1_eotn_to_gunnars": "1 - EOTN -> Gunnar's Hold",
        "_2_gunnars_to_longeyes": "2 - Gunnar's Hold -> Longeyes",
        "_3_longeyes_to_doomlore": "3 - Longeyes -> Doomlore",
        "_4_gunnars_to_sifhalla": "4 - Gunnar's Hold -> Sifhalla",
        "_5_sifhalla_to_olafstead": "5 - Sifhalla -> Olafstead",
        "_6_olafstead_to_umbralgrotto": "6 - Olafstead -> Umbral Grotto",
        "_7_umbral_grotto_to_vlox": "7 - Umbral Grotto -> Vlox",
        "_8_vlox_to_gadds": "8 - Vlox -> Gadds",
        "_9_vlox_to_tarnished": "9 - Vlox -> Tarnished Coast",
        "_10_tarnished_to_rata": "10 - Tarnished Coast -> Rata Sum",

    },
    "Factions_EchovaldForest": {
        "_1_arborstone": "1 - Arborstone",
        "_2_drazachthicket": "2 - Drazach Thicket",
        "_3_ferndale": "3 - Ferndale",
        "_4_melandrushope": "4 - Melandru's Hope",
        "_5_morostavtrail": "5 - Morostav Trail",
        "_6_mourningveilfalls": "6 - Mourning Veil Falls",
        "_7_theeternalgrove": "7 - The Eternal Grove",
    },
    "Factions_KainengCity": {
        "_1_bukdekbyway": "1 - Bukdek Byway",
        "_2_nahpuiquarter": "2 - Nahpui Quarter",
        "_3_pongmeivalley": "3 - Pongmei Valley",
        "_4_raisupalace": "4 - Raisu Palace",
        "_5_shadowspassage": "5 - Shadow's Passage",
        "_6_shenzuntunnels": "6 - Shenzun Tunnels",
        "_7_sunjiangdistrict": "7 - Sunjiang District",
        "_8_tahnnakitemple": "8 - Tahnnakai Temple",
        "_9_wajjunbazaar": "9 - Wajjun Bazaar",
        "_10_xaquangskyway": "10 - Xaquang Skyway",
    },
    "Factions_ShingJeaIsland": {
        "_1_haijulagoon": "1 - Haiju Lagoon",
        "_2_jayabluffs": "2 - Jaya Bluffs",
        "_3_kinyaprovince": "3 - Kinya Province",
        "_4_ministerchosestate": "4 - Minister Cho's Estate",
        "_5_sanjiangpeninsula": "5 - Sanjiang Peninsula",
        "_6_saoshangtrail": "6 - Saoshang Trail",
        "_7_sunquavale": "7 - Sunquale",
        "_8_zendaijun": "8 - Zendaijun",
    },
    "Factions_TheJadeSea": {
        "_1_archipelagos": "1 - Archipelagos",
        "_2_boreasseabed": "2 - Boreas Seabed",
        "_3_gyalahatchery": "3 - Gyala Hatchery",
        "_4_maishanghills": "4 - Maishang Hills",
        "_5_mountqinkai": "5 - Mount Qinkai",
        "_6_rheascrater": "6 - Rhea's Crater",
        "_7_silentsurf": "7 - Silent Surf",
        "_8_unwakingwaters": "8 - Unwaking Waters",
    },
    "NF_Istan": {
        "_1_cliffsofdohjok": "1 - Cliffs of Dohjok",
        "_2_fahranurthefirstcity": "2 - Fahranur the First City",
        "_3_issnurisles": "3 - Issnur Isles",
        "_4_lahtendabog": "4 - Lahtend Bog",
        "_5_mehtanikeys": "5 - Mehtani Keys",
        "_6_plainsofjarin": "6 - Plains of Jarin",
        "_7_zehlonreach": "7 - Zehlon Reach",
    },
    "NF_Kourna": {
        "_1_arkjokward": "1 - Arkjok Ward",
        "_2_bahdokcaverns": "2 - Bahdok Caverns",
        "_3_barbarousshore": "3 - Barbarous Shore",
        "_4_dejarinestate": "4 - Dejarin Estate",
        "_5_gandarathemoonfortress": "5 - Gandara, the Moon Fortress",
        "_6_jahaibluffs": "6 - Jaha Bluffs",
        "_7_margacoast": "7 - Marga Coast",
        "_8_sunwardmarches": "8 - Sunward Marches",
        "_9_thefloodplainofmahnkelon": "9 - The Floodplain of Mahnkelon",
        "_10_turaisprocession": "10 - Turai's Procession",
    },
    "NF_Vabbi": {
        "_1_forumhighlands": "Forum Highlands",
        "_2_gardenofseborhin": "Garden of Seborhin",
        "_3_holdingsofchokhin": "Holdings of Chokhin",
        "_4_resplendentmakuun": "Replendent Makuun",
        "_5_thehiddencityofahdashim": "The Hidden City of Ahdashim",
        "_6_themirroroflyss": "The Mirror of Lyss",
        "_7_vehjinmines": "Vehjin Mines",
        "_8_vehtendivalley": "Vehtendi Valley",
        "_9_wildernessofbahdza": "Wilderness of Bahdza",
        "_10_yatendicanyons": "Yatendi Canyons",
    },
    "Proph_Ascalon": {
        "_1_regentvalley": "1 - Regent Valley",
    },
    "Proph_CrystalDesert": {
        "_1_divinersascent": "1 - Diviner's Ascent",
        "_2_saltflats": "2 - Salt Flats",
        "_3_skywardreach": "3 - Skyward Reach",
        "_4_thearidsea": "4 - The Arid Sea",
        "_5_thescar": "5 - The Scar",
        "_6_vulturedrifts": "6 - Vulture Drifts",
    },
    "Proph_Kryta": {
        "_1_cursedlands": "1 - Cursed Lands",
        "_2_scoundrelsrise": "2 - Scoundrel's Rise",
        "_3_theblackcurtain": "3 - The Black Curtain",
        "_4_twinserpentlakes": "4 - Twin Serpent Lakes",
    },
    "Proph_Maguuma": {
        "_1_drytop": "1 - Dry Top",
        "_2_ettinsback": "2 - Ettin's Back",
        "_3_mamnoonlagoon": "3 - Mamnoon Lagoon",
        "_4_sagelands": "4 - Sagelands",
        "_5_silverwood": "5 - Silverwood",
        "_6_tangleroot": "6 - Tangleroot",
        "_7_thefalls": "7 - The Falls",
    },
    "Proph_NorthernShiverpeaks": {
        "_1_travelersvaley": "1 - Traveler's Valley",
    },
    "Proph_RingOfFireIsland": {
        "_1_perditionrock": "1 - Perdition Rock",
    },
    "Proph_SouthernShiverpeaks": {
        "_1_deldrimorbowl": "1 - Deldrimor Bowl",
        "_2_dreadnoughtsdrift": "2 - Dreadnought's Drift",
        "_3_grenthsfootprint": "3 - Grenth's Footprint",
        "_4_icefloe": "4 - Ice Floe",
        "_5_lornarspass": "5 - Lornar's Pass",
        "_6_snakedance": "6 - Snake Dance",
        "_7_spearheadpeak": "7 - Spearhead Peak",
        "_8_taluschute": "8 - Talus Chute",
        "_9_witmansfolly": "9 - Witman's Folly",
    },
}
def _use_consumable_bridge(label, upkeep_fn, *args, **kwargs):
    # Prefer the module helper if available
    try:
        from Bots.aC_Scripts.Consumable import ConsumablesSelectorFull
        use_fn = getattr(ConsumablesSelectorFull, "_use_consumable", None)
        if use_fn is not None:
            return (yield from use_fn(label, upkeep_fn, *args, **kwargs))
    except Exception:
        pass

    # Fallback: call upkeep, then record via runner_fsm if present
    result = (yield from upkeep_fn(*args, **kwargs))
    try:
        from PyQuishAi.runner_singleton import runner_fsm
        cs = getattr(runner_fsm, "chain_stats", None)
        if cs is not None:
            cs.record_consumable(label, 1)
    except Exception:
        pass
    return result

def get_cached_regions():
    global _cached_regions
    if _cached_regions is None:
        _cached_regions = get_regions()
    return _cached_regions

def get_cached_runs_for_region(region: str):
    """Direct lookup from static map (no normalization/parsing)."""
    region_map = RUN_NAME_MAP.get(region, {})
    raw_runs = list(region_map.keys())        # filenames
    display_runs = list(region_map.values())  # friendly names
    return raw_runs, display_runs

def format_time(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02}:{secs:02}"

def parse_run_filename(region, run_filename):
    name = run_filename.lstrip("_")
    parts = name.split("_")
    order = int(parts[0]) if parts[0].isdigit() else 0
    origin = parts[1]
    destination = parts[-1]
    run_id = f"{region}__{run_filename}"
    return RunInfo(order, run_id, origin, destination, region, run_filename)

class ConsumablesHelper:
    def __init__(self):
        self.started = False

        # (key in ConsumablesSelectorFull.consumable_state,
        #  label for stats,
        #  upkeep coroutine,
        #  args tuple,
        #  kwargs dict)
        self._table = [
            ("Cupcake",            "Cupcake",            Routines.Yield.Upkeepers.Upkeep_BirthdayCupcake,     (), {}),
            ("Alcohol",            "Alcohol",            Routines.Yield.Upkeepers.Upkeep_Alcohol,             (), {"target_alc_level": 1, "disable_drunk_effects": True}),
            ("Morale",             "Morale",             Routines.Yield.Upkeepers.Upkeep_Morale,              (110,), {}),
            ("CitySpeed",          "CitySpeed",          Routines.Yield.Upkeepers.Upkeep_City_Speed,          (), {}),
            ("ArmorOfSalvation",   "ArmorOfSalvation",   Routines.Yield.Upkeepers.Upkeep_ArmorOfSalvation,    (), {}),
            ("EssenceOfCelerity",  "EssenceOfCelerity",  Routines.Yield.Upkeepers.Upkeep_EssenceOfCelerity,   (), {}),
            ("GrailOfMight",       "GrailOfMight",       Routines.Yield.Upkeepers.Upkeep_GrailOfMight,        (), {}),
            ("BlueRockCandy",      "BlueRockCandy",      Routines.Yield.Upkeepers.Upkeep_BlueRockCandy,       (), {}),
            ("GreenRockCandy",     "GreenRockCandy",     Routines.Yield.Upkeepers.Upkeep_GreenRockCandy,      (), {}),
            ("RedRockCandy",       "RedRockCandy",       Routines.Yield.Upkeepers.Upkeep_RedRockCandy,        (), {}),
            ("SliceOfPumpkinPie",  "SliceOfPumpkinPie",  Routines.Yield.Upkeepers.Upkeep_SliceOfPumpkinPie,   (), {}),
            ("BowlOfSkalefinSoup", "BowlOfSkalefinSoup", Routines.Yield.Upkeepers.Upkeep_BowlOfSkalefinSoup,  (), {}),
            ("CandyApple",         "CandyApple",         Routines.Yield.Upkeepers.Upkeep_CandyApple,          (), {}),
            ("CandyCorn",          "CandyCorn",          Routines.Yield.Upkeepers.Upkeep_CandyCorn,           (), {}),
            ("DrakeKabob",         "DrakeKabob",         Routines.Yield.Upkeepers.Upkeep_DrakeKabob,          (), {}),
            ("GoldenEgg",          "GoldenEgg",          Routines.Yield.Upkeepers.Upkeep_GoldenEgg,           (), {}),
            ("PahnaiSalad",        "PahnaiSalad",        Routines.Yield.Upkeepers.Upkeep_PahnaiSalad,         (), {}),
            ("WarSupplies",        "WarSupplies",        Routines.Yield.Upkeepers.Upkeep_WarSupplies,         (), {}),
        ]

    def run(self):
        while True:
            if not self.started:
                yield from Routines.Yield.wait(500)
                continue

            # basic guards (same style as TitleHelper loop)
            if not Routines.Checks.Map.MapValid():
                yield from Routines.Yield.wait(1000)
                continue
            if GLOBAL_CACHE.Agent.IsDead(GLOBAL_CACHE.Player.GetAgentID()):
                yield from Routines.Yield.wait(1000)
                continue

            s = ConsumablesSelectorFull.consumable_state

            # Table-driven application
            for key, label, fn, args, kwargs in self._table:
                if s.get(key, False):
                    yield from _use_consumable_bridge(label, fn, *args, **kwargs)

            # small idle between passes
            yield from Routines.Yield.wait(1000)

RECHECK_INTERVAL_MS = 500 # Used for followpathandaggro 
ARRIVAL_TOLERANCE = 250  # Used for path point arrival

# --------------------------------------------------------------------------------------------------
# NEW THEME COLORS (rename to English‐friendly names)
# --------------------------------------------------------------------------------------------------

# 1) Window & Frame backgrounds (dark charcoal, slightly translucent)
window_bg_color       = Color(28,  28,  28, 230).to_tuple_normalized()
frame_bg_color        = Color(48,  48,  48, 230).to_tuple_normalized()
frame_hover_color     = Color(68,  68,  68, 230).to_tuple_normalized()
frame_active_color    = Color(58,  58,  58, 230).to_tuple_normalized()

# 2) Body text (off‐white for maximum readability)
body_text_color       = Color(139, 131, 99, 255).to_tuple_normalized()

# 3) Disabled text (mid‐gray for grayed‐out buttons)
disabled_text_color   = Color(140, 140, 140, 255).to_tuple_normalized()

# 4) Separator lines (medium‐gray)
separator_color       = Color(90,  90,  90, 255).to_tuple_normalized()

# 5) Header text (use the same bright off‐white as body, or tweak to slightly brighter)
header_color          = Color(136, 117, 44, 255).to_tuple_normalized()  # “Statistics:” style: pale gold
#    You can change (251,241,166) to any off‐white / pale‐yellow RGB you like.

# 6) Icon accent color (a more “exciting” golden‐teal that fits the palette)
icon_color            = Color(177, 152, 55, 255).to_tuple_normalized()

# 7) Neutral button colors (light gray → slightly brighter on hover → slightly darker on active)
neutral_button        = Color(33, 51, 58, 255).to_tuple_normalized()  # default button
neutral_button_hover  = Color(140, 140, 140, 255).to_tuple_normalized()  # hovered
neutral_button_active = Color( 90,  90,  90, 255).to_tuple_normalized()  # pressed

# 8) Combo‐box header (still a dark green tint, if you prefer; otherwise gray)
header_bg_color       = Color(33, 51, 58, 255).to_tuple_normalized()
header_hover_color    = Color(33, 51, 58, 255).to_tuple_normalized()
header_active_color   = Color(95, 145,  95, 255).to_tuple_normalized()


# --------------------------------------------------------------------------------------------------
# UPDATED DrawWindow() WITH EVERY ICON & HEADING COLORED
# --------------------------------------------------------------------------------------------------

def DrawWindow():
    global show_stats_window, selected_region, selected_run, selected_chain
    if not PyImGui.begin(module_name, PyImGui.WindowFlags.AlwaysAutoResize):
        PyImGui.end()
        return

    # 2) Push “global” style colors: WindowBg, FrameBg, FrameBgHovered, FrameBgActive, Text, Separator
    PyImGui.push_style_color(PyImGui.ImGuiCol.WindowBg,       window_bg_color)   # push #1
    PyImGui.push_style_color(PyImGui.ImGuiCol.FrameBg,        frame_bg_color)    # push #2
    PyImGui.push_style_color(PyImGui.ImGuiCol.FrameBgHovered, frame_hover_color) # push #3
    PyImGui.push_style_color(PyImGui.ImGuiCol.FrameBgActive,  frame_active_color)# push #4
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text,           body_text_color)   # push #5
    PyImGui.push_style_color(PyImGui.ImGuiCol.Separator,      separator_color)   # push #6

    # 3) Push “combo header” colors (if you still want a greenish tint for dropdowns):
    PyImGui.push_style_color(PyImGui.ImGuiCol.Header,         header_bg_color)   # push #7
    PyImGui.push_style_color(PyImGui.ImGuiCol.HeaderHovered,  header_hover_color)# push #8
    PyImGui.push_style_color(PyImGui.ImGuiCol.HeaderActive,   header_active_color)# push #9

    # 4) Push “button accent” colors (now neutral grays)
    PyImGui.push_style_color(PyImGui.ImGuiCol.Button,         neutral_button)         # push #10
    PyImGui.push_style_color(PyImGui.ImGuiCol.ButtonHovered,  neutral_button_hover)   # push #11
    PyImGui.push_style_color(PyImGui.ImGuiCol.ButtonActive,   neutral_button_active)  # push #12

    # --------------------------------
    # BEGIN DRAWING ALL WIDGETS
    # --------------------------------

    # ---- Start / Stop Button ----
    #   Renders in neutral gray by default; changes on hover/press.
    # --- Start / Stop (PuQuishAi) ---
    fsm_active = bool(runner_fsm.map_chain and (runner_fsm.skill_coroutine or runner_fsm.overwatch._active))
    btn_label = ("Start bot " + IconsFontAwesome5.ICON_PLAY_CIRCLE if not fsm_active else "Stop bot  " + IconsFontAwesome5.ICON_STOP_CIRCLE)
    if PyImGui.button("Start PuQuishAi", width=160):
        if selected_chain:
            runner_fsm.set_map_chain(sorted(selected_chain, key=lambda r: r.order))
            runner_fsm.start()
        else:
            ConsoleLog("PuQuishAi", "No runs in chain!", Console.MessageType.Warning)
    PyImGui.same_line(0, 8)
    if PyImGui.button("Stop", width=80):
        runner_fsm.reset()
        runner_fsm.map_chain = []

    PyImGui.separator()

    # --- Consumable helper ---
    helper = consumables_helper  
    was_running = helper.started
    label = "Cons: ON" if was_running else "Cons: OFF"

    if was_running:
        PyImGui.push_style_color(PyImGui.ImGuiCol.Text, (0.20, 0.90, 0.20, 1.0))

    clicked = PyImGui.button(label)

    if was_running:
        PyImGui.pop_style_color(1)

    if clicked:
        helper.started = not was_running
        if helper.started:
            ConsoleLog("FSM", "Starting consumable upkeep...", Console.MessageType.Debug)
        else:
            ConsoleLog("FSM", "Consumable upkeep stopped.", Console.MessageType.Debug)

    PyImGui.same_line(0, 10)
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, (1.0, 1.0, 0.3, 1.0))
    if PyImGui.button("Options"):
        ConsumablesSelectorFull.show_consumables_selector = True
    PyImGui.pop_style_color(1)
    PyImGui.same_line(0, 5)
    PyImGui.text(f"Drunk Level: {Effects.GetAlcoholLevel()}")

    if ConsumablesSelectorFull.show_consumables_selector:
        ConsumablesSelectorFull.draw_consumables_selector_window()

    PyImGui.separator()

    # ---- Select Region (Icon + Heading) ----
    #   Icon in punchy accent color:
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, icon_color)       # push #14
    PyImGui.text(IconsFontAwesome5.ICON_GLOBE_EUROPE)
    PyImGui.pop_style_color(1)

    #   Heading “Select Region:” in pale‐gold
    PyImGui.same_line(0, 3)
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, header_color)     # push #15
    PyImGui.text("Select Region:")
    PyImGui.pop_style_color(1)

    #   Combo itself uses frame_bg_color + body_text_color (already pushed)

    # --- Region & Run dropdowns (always visible; 1:1 with PuQuishAi) ---
    regions = get_cached_regions()
    if not regions:
        PyImGui.text("No regions found.")
    else:
        # Region combo
        if not selected_region or selected_region not in regions:
            selected_region = regions[0]

        r_idx = regions.index(selected_region)
        new_r_idx = PyImGui.combo("##Region", r_idx, regions)
        if new_r_idx != r_idx:
            selected_region = regions[new_r_idx]
            selected_run = None  # reset run when region changes

        # Runs for selected region
        runs_raw, runs_display = get_cached_runs_for_region(selected_region)
        if not runs_raw:
            PyImGui.text("No runs found in this region.")
        else:
            # Run combo
            if not selected_run or selected_run not in runs_raw:
                selected_run = runs_raw[0]

            sel_idx = runs_raw.index(selected_run)
            new_idx = PyImGui.combo("##Run", sel_idx, runs_display)
            if new_idx != sel_idx:
                selected_run = runs_raw[new_idx]

            # Add selected run to chain
            if PyImGui.button("Add run to Chain"):
                ri = parse_run_filename(selected_region, selected_run)
                ri.display = RUN_NAME_MAP[selected_region][selected_run]  # friendly label
                if not any(r.id == ri.id for r in selected_chain):
                    selected_chain.append(ri)

            PyImGui.same_line(0, 6)

            # Add ALL runs in region
            if PyImGui.button("Add All in Region"):
                added = 0
                for rf in runs_raw:
                    ri = parse_run_filename(selected_region, rf)
                    ri.display = RUN_NAME_MAP[selected_region][rf]
                    if not any(r.id == ri.id for r in selected_chain):
                        selected_chain.append(ri)
                        added += 1
                ConsoleLog("PuQuishAi", f"Added {added} run(s) from {selected_region}.", Console.MessageType.Debug)


    # --- Current Chain (same presentation as PuQuishAi) ---
    PyImGui.separator()
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, header_color)
    PyImGui.text("Current Chain:")
    PyImGui.pop_style_color(1)

    if selected_chain:
        for idx, r in enumerate(sorted(selected_chain, key=lambda rr: rr.order)):
            PyImGui.text(r.display)
            PyImGui.same_line(0, 6)
            if PyImGui.small_button(f"Remove##{idx}"):
                selected_chain.pop(idx)
    else:
        PyImGui.text("No runs in chain.")

    PyImGui.separator()

    # ---- Current State ----
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, header_color)
    PyImGui.text("Current State:")
    PyImGui.pop_style_color(1)

    state_name = ""
    if hasattr(runner_fsm, "fsm") and runner_fsm.fsm:
        # if your FSM class exposes another getter, swap this line accordingly
        state_name = getattr(runner_fsm.fsm, "GetCurrentStateName", lambda: "")()

    PyImGui.text(state_name or "-")
    if runner_fsm.last_error:
        PyImGui.text_colored(f"Last error: {runner_fsm.last_error}", (1.0, 0.3, 0.3, 1.0))

    PyImGui.separator()

    if PyImGui.button("Open Statistics…"):
        show_stats_window = True

    # --- Always-visible bot HUD ---
    try:
        if getattr(runner_fsm, "run_active", False) and runner_fsm.chain_stats:
            # Total time (hh:mm:ss)
            secs_total = runner_fsm.chain_stats.total_chain_time()
            hh = int(secs_total // 3600)
            mm = int((secs_total % 3600) // 60)
            ss = int(secs_total % 60)
            PyImGui.text(f"Total Time: {hh:02}:{mm:02}:{ss:02}")

            # Current run (mm:ss)
            current = None
            for r in runner_fsm.chain_stats.runs:
                if r.started and not r.finished:
                    current = r
                    break
            run_secs = current.get_duration() if current else 0
            PyImGui.text(f"Current Run: {int(run_secs // 60):02}:{int(run_secs % 60):02}")

            # Vanquish status line
            from aC_api import draw_vanquish_status
            draw_vanquish_status("Vanquish Progress")
    except Exception:
        pass

    # --- Auto donate faction (GUI) ---
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, header_color)
    PyImGui.text("Auto Donate Faction:")
    PyImGui.pop_style_color(1)

    # Toggle
    enabled = bool(getattr(runner_fsm, "auto_donate_enabled", False))
    runner_fsm.auto_donate_enabled = PyImGui.checkbox("Enable auto-donate", enabled)

    # Threshold (narrow, fixed width)
    thr = int(getattr(runner_fsm, "auto_donate_threshold", 30000))

    # Prefer set_next_item_width; fall back to push/pop if needed
    pushed_width = False
    if hasattr(PyImGui, "set_next_item_width"):
        PyImGui.set_next_item_width(120)           # keep the input narrow
    else:
        if hasattr(PyImGui, "push_item_width"):
            PyImGui.push_item_width(120); pushed_width = True

    # input_int(label, value, min_value, step_fast, flags) -> int
    new_thr = PyImGui.input_int("Threshold", thr, 5000, 10000, 0)
    if pushed_width and hasattr(PyImGui, "pop_item_width"):
        PyImGui.pop_item_width()

    # Clamp + store if changed
    if new_thr < 5000:
        new_thr = 5000
    if new_thr != thr:
        runner_fsm.auto_donate_threshold = int(new_thr)

    PyImGui.same_line(0, 5)

    # Tooltip on its own line so it doesn't force width
    PyImGui.text("(?)")
    if PyImGui.is_item_hovered():
        PyImGui.begin_tooltip()
        PyImGui.text("When enabled, before the chain starts the bot donates Luxon/Kurzick if unspent ≥ threshold.")
        PyImGui.text("It travels to Cavalon/House zu Heltzer automatically, broadcasts DonateToGuild,")
        PyImGui.text("and waits until all clients finish.")
        PyImGui.end_tooltip()

    PyImGui.separator()

    # ---- Title / Allegiance (Icon + Heading) ----
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, icon_color)         # push #21
    PyImGui.text(IconsFontAwesome5.ICON_TROPHY)
    PyImGui.pop_style_color(1)

    PyImGui.same_line(0, 5)
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, header_color)      # push #22
    PyImGui.text("Title / Allegiance:")
    PyImGui.pop_style_color(1)

    # Now use display_title_progress(...) as before
    region = selected_region
    if region in kurzick_regions:
        display_faction("Kurzick", 5, Player.GetKurzickData, kurzick_tiers)
    elif region in luxon_regions:
        display_faction("Luxon", 6, Player.GetLuxonData, luxon_tiers)
    elif region in nightfall_regions:
        display_title_progress("Sunspear Title", 17, sunspear_tiers)
        display_title_progress("Lightbringer Title", 20, lightbringer_tiers)
    elif region in eotn_region_titles:
        for title_id, title_name, tier_data in eotn_region_titles[region]:
            display_title_progress(title_name, title_id, tier_data)

    PyImGui.separator()

    # --------------------------------
    # POP ALL THE STYLE COLORS WE PUSHED (in reverse order)
    # --------------------------------
    # We pushed 22 times (counts 1..22). Pop in reverse groups:
    PyImGui.pop_style_color(3)   # unwinds neutral_button, neutral_button_hover, neutral_button_active (#10,#11,#12)
    PyImGui.pop_style_color(3)   # unwinds header_bg_color, header_hover_color, header_active_color (#7,#8,#9)
    PyImGui.pop_style_color(6)   # unwinds window_bg_color, frame_bg_color, frame_hover_color, frame_active_color, body_text_color, separator_color (#1..#6)
    # (Note: the 13–22 pushes were popped inline, so no need to pop them here.)

    PyImGui.end()

# === Instantiate & wire into your app loop (same as TitleHelper) ===
consumables_helper = ConsumablesHelper()
consumables_runner = consumables_helper.run()

def _fmt_hms(seconds: float) -> str:
    seconds = int(seconds or 0)
    return f"{seconds//3600:02}:{(seconds%3600)//60:02}:{seconds%60:02}"

def draw_statistics_window():
    global show_stats_window
    if not show_stats_window:
        return
    expanded, show_stats_window = PyImGui.begin_with_close("Run Statistics", show_stats_window, PyImGui.WindowFlags.AlwaysAutoResize)
    if not expanded:
        PyImGui.end()
        return

    cs = getattr(runner_fsm, "chain_stats", None)
    if not (cs and runner_fsm.run_active):
        PyImGui.text("No active stats.")
        PyImGui.end()
        return

    # Totals / rates
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, (0.85, 0.75, 0.3, 1.0))
    PyImGui.text("Overview")
    PyImGui.pop_style_color(1)

    PyImGui.text(f"Total runtime:  {_fmt_hms(cs.total_chain_time())}")
    PyImGui.text(f"Runs completed: {cs.runs_completed():,}")
    PyImGui.text(f"Runs failed:     {cs.runs_failed():,}")
    PyImGui.text(f"Avg run time:    {_fmt_hms(cs.avg_run_time_seconds())}")
    PyImGui.text(f"Faction/hr:      {cs.avg_faction_per_hour():,.0f}")
    PyImGui.separator()

    # Donations
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, (0.85, 0.75, 0.3, 1.0))
    PyImGui.text("Donations")
    PyImGui.pop_style_color(1)
    PyImGui.text(f"Kurzick donated: {cs.donations.get('kurzick', 0):,}")
    PyImGui.text(f"Luxon donated:   {cs.donations.get('luxon', 0):,}")
    PyImGui.text(f"Total donated:   {cs.total_faction_donated:,}")
    PyImGui.separator()

    # Per-map
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, (0.85, 0.75, 0.3, 1.0))
    PyImGui.text("Per Map")
    PyImGui.pop_style_color(1)
    for run in sorted(cs.runs, key=lambda r: r.order):
        p = cs.per_map.get(run.id, None)
        if not p:
            continue
        label = run.display or run.id
        PyImGui.text(label)
        PyImGui.same_line(0, 8)
        PyImGui.text(f"S:{p['success']} F:{p['fails']}  Vanq:{p['vanquished']} / Not:{p['not_vanquished']}  Avg:{_fmt_hms((p['total_time']/p['runs']) if p['runs'] else 0)}")

    PyImGui.separator()

    # Consumables
    PyImGui.push_style_color(PyImGui.ImGuiCol.Text, (0.85, 0.75, 0.3, 1.0))
    PyImGui.text("Consumables Used")
    PyImGui.pop_style_color(1)
    if cs.consumables:
        for name, cnt in sorted(cs.consumables.items()):
            PyImGui.text(f"{name}: {cnt:,}")
    else:
        PyImGui.text("—")

    PyImGui.end()

# BEWARE OLD STATES
def main():
    if not Routines.Checks.Map.MapValid():
        return
    DrawWindow()
    if show_stats_window:
        draw_statistics_window()
    runner_fsm.fsm.update()
    try:
        next(consumables_runner)
    except StopIteration:
        pass
        