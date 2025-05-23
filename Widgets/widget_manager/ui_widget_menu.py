from Py4GWCoreLib import PyImGui, ImGui, Utils, ConsoleLog, IconsFontAwesome5, Py4GW
from .handler import handler
from .config_scope import use_account_settings
from . import state

def draw_widget_popup_menus():
    categorized_widgets = {}
    for name, info in handler.widgets.items():
        data = handler.widget_data_cache.get(name, {})
        if data.get("hidden", False) and not state.show_hidden_widgets:
            continue
        cat = data.get("category", "Miscellaneous")
        sub = data.get("subcategory") or "General"
        categorized_widgets.setdefault(cat, {}).setdefault(sub, []).append(name)

    cat_color = Utils.RGBToNormal(200, 255, 150, 255)

    for cat, subs in categorized_widgets.items():
        if PyImGui.begin_menu(cat):
            for sub, names in subs.items():
                if PyImGui.begin_menu(sub):
                    if not PyImGui.begin_table(f"Widgets_{cat}_{sub}", 2, PyImGui.TableFlags.Borders):
                        PyImGui.end_menu()
                        continue

                    for name in names:
                        info = handler.widgets[name]
                        PyImGui.table_next_row()
                        PyImGui.table_set_column_index(0)
                        enabled = bool(info.get("enabled", False))
                        if not isinstance(info.get("enabled"), bool):
                            ConsoleLog("WidgetManager", f"[{name}] invalid 'enabled' value: {info.get('enabled')} ({type(info.get('enabled'))})", Py4GW.Console.MessageType.Warning)
                        new_enabled = PyImGui.checkbox(name, enabled)
                        if new_enabled != info["enabled"]:
                            info["enabled"] = new_enabled
                            handler._write_setting(name, "enabled", str(new_enabled), to_account=use_account_settings())

                        PyImGui.table_set_column_index(1)
                        if info["enabled"]:
                            PyImGui.push_style_color(PyImGui.ImGuiCol.Text, cat_color)
                        info["configuring"] = ImGui.toggle_button(IconsFontAwesome5.ICON_COG + f"##Configure{name}", info["configuring"])
                        if info["enabled"]:
                            PyImGui.pop_style_color(1)

                    PyImGui.end_table()
                    PyImGui.end_menu()  # close sub
            PyImGui.end_menu()  # close cat

