import os
import PyImGui
from Py4GWCoreLib import *

show_consumables_selector = False

consumable_state = {
    "Cupcake": False,
    "Alcohol": False,
    "Morale": False,
    "CitySpeed": False,
    "ArmorOfSalvation": False,
    "EssenceOfCelerity": False,
    "GrailOfMight": False,
    "BlueRockCandy": False,
    "GreenRockCandy": False,
    "RedRockCandy": False,
    "SliceOfPumpkinPie": False,
    "BowlOfSkalefinSoup": False,
    "CandyApple": False,
    "CandyCorn": False,
    "DrakeKabob": False,
    "GoldenEgg": False,
    "PahnaiSalad": False,
    "WarSupplies": False,
}

# one icon per category, reusing your existing item-texture convention
ICON_MODEL = {
    "Cupcake":              ModelID.Birthday_Cupcake,
    "Alcohol":              ModelID.Hunters_Ale,
    "Morale":               ModelID.Honeycomb,
    "CitySpeed":            ModelID.Sugary_Blue_Drink,
    "ArmorOfSalvation":     ModelID.Armor_Of_Salvation,
    "EssenceOfCelerity":    ModelID.Essence_Of_Celerity,
    "GrailOfMight":         ModelID.Grail_Of_Might,
    "BlueRockCandy":        ModelID.Blue_Rock_Candy,
    "GreenRockCandy":       ModelID.Green_Rock_Candy,
    "RedRockCandy":         ModelID.Red_Rock_Candy,
    "SliceOfPumpkinPie":    ModelID.Slice_Of_Pumpkin_Pie,
    "BowlOfSkalefinSoup":   ModelID.Bowl_Of_Skalefin_Soup,
    "CandyApple":           ModelID.Candy_Apple,
    "CandyCorn":            ModelID.Candy_Corn,
    "DrakeKabob":           ModelID.Drake_Kabob,
    "GoldenEgg":            ModelID.Golden_Egg,
    "PahnaiSalad":          ModelID.Pahnai_Salad,
    "WarSupplies":          ModelID.War_Supplies,

}
# === Paths and Constants ===

def _texture_path(model_id):
    base_path = os.path.abspath(os.path.join(os.getcwd(), '..', '..'))
    folder = os.path.join(base_path, "Textures", "Item Models")
    # Preferred convention (spaces)
    fn_spaces  = f"[{model_id.value}] - {model_id.name.replace('_', ' ')}.png"
    p_spaces   = os.path.join(folder, fn_spaces)
    # Some files (like Slice_of_Pumpkin_Pie) use underscores
    fn_unders  = f"[{model_id.value}] - {model_id.name}.png"
    p_unders   = os.path.join(folder, fn_unders)
    if os.path.exists(p_spaces):
        return p_spaces
    if os.path.exists(p_unders):
        return p_unders
    # Last resort: find by ID regardless of the trailing name
    try:
        for fname in os.listdir(folder):
            if fname.startswith(f"[{model_id.value}] - ") and fname.lower().endswith(".png"):
                return os.path.join(folder, fname)
    except Exception:
        pass
    # Fall back to the spaces path so failures look consistent
    return p_spaces

def draw_consumables_selector_window():
    global show_consumables_selector

    expanded, show_consumables_selector = PyImGui.begin_with_close(
        "Choose Consumables", show_consumables_selector, PyImGui.WindowFlags.AlwaysAutoResize
    )
    if not show_consumables_selector:
        PyImGui.end()
        return

    items = [
        # Summon / core PvE
        ("ArmorOfSalvation",   ICON_MODEL["ArmorOfSalvation"],   "Armor of Salvation"),
        ("EssenceOfCelerity",  ICON_MODEL["EssenceOfCelerity"],  "Essence of Celerity"),
        ("GrailOfMight",       ICON_MODEL["GrailOfMight"],       "Grail of Might"),
        # Speed candies
        ("BlueRockCandy",      ICON_MODEL["BlueRockCandy"],      "Blue Rock Candy"),
        ("GreenRockCandy",     ICON_MODEL["GreenRockCandy"],     "Green Rock Candy"),
        ("RedRockCandy",       ICON_MODEL["RedRockCandy"],       "Red Rock Candy"),
        # Sweets / food
        ("Cupcake",            ICON_MODEL["Cupcake"],            "Birthday Cupcake"),
        ("SliceOfPumpkinPie",  ICON_MODEL["SliceOfPumpkinPie"],  "Slice of Pumpkin Pie"),
        ("BowlOfSkalefinSoup", ICON_MODEL["BowlOfSkalefinSoup"], "Bowl of Skalefin Soup"),
        ("CandyApple",         ICON_MODEL["CandyApple"],         "Candy Apple"),
        ("CandyCorn",          ICON_MODEL["CandyCorn"],          "Candy Corn"),
        ("DrakeKabob",         ICON_MODEL["DrakeKabob"],         "Drake Kabob"),
        ("GoldenEgg",          ICON_MODEL["GoldenEgg"],          "Golden Egg"),
        ("PahnaiSalad",        ICON_MODEL["PahnaiSalad"],        "Pahnai Salad"),
        # Faction buff
        ("WarSupplies",        ICON_MODEL["WarSupplies"],        "War Supplies"),
        # Context group (keep last like before)
        ("Alcohol",            ICON_MODEL["Alcohol"],            "Any Alcohol"),
        ("Morale",             ICON_MODEL["Morale"],             "Any Morale Boost"),
        ("CitySpeed",          ICON_MODEL["CitySpeed"],          "Any City Speed"),
    ]

    for i, (key, model_id, tip) in enumerate(items):
        PyImGui.push_id(key)
        selected = consumable_state[key]
        new_selected = ImGui.image_toggle_button(key, _texture_path(model_id), selected, 40, 40)
        consumable_state[key] = new_selected

        # optional: show a hover tooltip since we removed labels
        if PyImGui.is_item_hovered():
            PyImGui.set_tooltip(tip)  # or BeginTooltip/EndTooltip if your wrapper uses that

        PyImGui.pop_id()

        ITEMS_PER_ROW = 3
        # stay on same line unless we're at the end of a row (every 3rd item)
        if (i % ITEMS_PER_ROW) != (ITEMS_PER_ROW - 1) and i < len(items) - 1:
            PyImGui.same_line(0, 6)

    PyImGui.end()

#def main():
#    draw_consumables_selector_window()