import os, configparser
from Py4GWCoreLib import Player, Party, PyImGui
from Blessing_Core import BlessingRunner
import Verify_Blessing

INI_PATH = os.path.join(os.getcwd(), "Blessed_Config.ini")

def _read_ini() -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    cp.read(INI_PATH)
    return cp

def read_run_flag() -> bool:
    return _read_ini().getboolean("BlessingRun", "Enabled", fallback=False)

def write_run_flag(val: bool):
    cp = _read_ini()
    if not cp.has_section("BlessingRun"):
        cp.add_section("BlessingRun")
    cp.set("BlessingRun", "Enabled", str(val))
    with open(INI_PATH, "w") as f:
        cp.write(f)

cfg = _read_ini()
LEADER_UI     = cfg.getboolean("Settings",   "LeaderUI",    fallback=True)
PER_CLIENT_UI = cfg.getboolean("Settings",   "PerClientUI", fallback=False)
AUTO_RUN_ALL  = cfg.getboolean("BlessingRun","AutoRunAll",  fallback=True)

_runner    = BlessingRunner()
_running   = False
_last_flag = False
_consumed  = False

def get_party_players_info():
    slots = Party.GetPlayers()
    leader = Party.GetPartyLeaderID()
    info = []
    for slot in slots:
        ln = slot.login_number
        ag = Party.Players.GetAgentIDByLoginNumber(ln)
        nm = Party.Players.GetPlayerNameByLoginNumber(ln)
        info.append({
            "login":        ln,
            "name":         nm,
            "is_leader":    (ag == leader),
            "has_blessing": bool(Verify_Blessing.find_first_active_blessing(ag))
        })
    return info

def on_imgui_render(me: int):
    global _running, _last_flag, _consumed

    # Detect shared‐flag toggles
    flag = read_run_flag()
    if flag != _last_flag:
        _consumed  = False
        _last_flag = flag

    # If flag is set and not yet consumed, start FSM
    if flag and not _running and not _consumed:
        _runner.start()
        _running  = True
        _consumed = True

    # Advance FSM
    if _running:
        done, success = _runner.update()
        if done:
            # Leader clears the flag after all finish
            if AUTO_RUN_ALL and Party.GetPartyLeaderID() == me:
                write_run_flag(False)
            _running = False

    # Draw only for leader (or if per-client UI is allowed)
    slots = Party.GetPlayers()
    if not slots:
        return
    is_leader = (Party.GetPartyLeaderID() == me)
    if not (LEADER_UI and is_leader) and not PER_CLIENT_UI:
        return

    PyImGui.begin("Blessing Controller")
    PyImGui.text("Party Blessing Status:")
    PyImGui.separator()

    # List every party member and re-check blessing by agent ID
    for slot in slots:
        ln = slot.login_number
        ag = Party.Players.GetAgentIDByLoginNumber(ln)
        nm = Party.Players.GetPlayerNameByLoginNumber(ln)
        role = "Leader" if ag == Party.GetPartyLeaderID() else "Ai Hero"
        blessed = bool(Verify_Blessing.find_first_active_blessing(ag))
        mark = "Blessed" if blessed else "Unholy"
        PyImGui.text(f"[{ln}] {nm} ({role}) [{mark}]")

    PyImGui.separator()
    # Run‐sequence button
    if not _running and PyImGui.button("Run Blessing Sequence"):
        if AUTO_RUN_ALL and not is_leader:
            # non‐leaders do nothing in party mode
            pass
        else:
            if AUTO_RUN_ALL and is_leader:
                # Leader in party mode: flip flag *and* start locally
                write_run_flag(True)
                _runner.start()
                _running = True
            else:
                # Single‐client mode
                _runner.start()
                _running = True

    if _running:
        PyImGui.text("Running blessing sequence...")

    PyImGui.end()

def main():
    me = Player.GetAgentID()
    on_imgui_render(me)
