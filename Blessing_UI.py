# Blessing_UI.py
import os
import tempfile
import configparser

from typing import Set
from Py4GWCoreLib import Player, Party, PyImGui
from Verify_Blessing import has_any_blessing
from Blessing_Core import BlessingRunner, FLAG_DIR

# -----------------------------------------------------------------------------
# 1) Run-flag INI coordination (shared by all clients)
# -----------------------------------------------------------------------------
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

# -----------------------------------------------------------------------------
# 2) UI configuration (you can load these from your INI as well)
# -----------------------------------------------------------------------------
cfg = _read_ini()
LEADER_UI     = cfg.getboolean("Settings",   "LeaderUI",    fallback=True)
PER_CLIENT_UI = cfg.getboolean("Settings",   "PerClientUI", fallback=False)
AUTO_RUN_ALL  = cfg.getboolean("BlessingRun","AutoRunAll",  fallback=True)

# -----------------------------------------------------------------------------
# 3) Shared temp-dir for per-client blessing flags
# -----------------------------------------------------------------------------
# Make sure all processes on this machine point at the same directory:
FLAG_DIR = os.path.join(tempfile.gettempdir(), "GuildWarsBlessFlags")
os.makedirs(FLAG_DIR, exist_ok=True)

# -----------------------------------------------------------------------------
# 4) FSM runner + shared-flag state
# -----------------------------------------------------------------------------
_runner     = BlessingRunner()
_running    = False
_last_flag  = False
_consumed   = False

def on_imgui_render(me: int):
    global _running, _last_flag, _consumed

    # --- A) Sync this client’s own flag file with its buff state ---
    my_id   = Player.GetAgentID()
    my_file = os.path.join(FLAG_DIR, f"{my_id}.flag")

    if has_any_blessing(my_id):
        if not os.path.exists(my_file):
            open(my_file, "w").close()
    else:
        if os.path.exists(my_file):
            os.remove(my_file)

    # --- B) Run-flag coordination ---
    flag = read_run_flag()
    if flag != _last_flag:
        _consumed  = False
        _last_flag = flag

    if flag and not _running and not _consumed:
        _runner.start()
        _running, _consumed = True, True

    if _running:
        done, _ = _runner.update()
        if done:
            # if leader in party-mode, leader clears the flag
            if AUTO_RUN_ALL and Party.GetPartyLeaderID() == me:
                write_run_flag(False)
            _running = False

    # --- C) Draw UI only for leader (or if per-client UI allowed) ---
    slots = Party.GetPlayers()
    if not slots:
        return
    is_leader = (Party.GetPartyLeaderID() == me)
    if not (LEADER_UI and is_leader) and not PER_CLIENT_UI:
        return

    # --- D) Read *all* client flag files to see who’s blessed ---
    blessed_ids: Set[int] = set()
    for fn in os.listdir(FLAG_DIR):
        if fn.endswith(".flag"):
            try:
                blessed_ids.add(int(fn[:-5]))
            except ValueError:
                pass

    # --- E) Render the window ---
    PyImGui.begin("Blessing Controller")
    PyImGui.text("Party Blessing Status:")
    PyImGui.separator()

    for slot in slots:
        ln = slot.login_number
        ag = Party.Players.GetAgentIDByLoginNumber(ln)
        nm = Party.Players.GetPlayerNameByLoginNumber(ln)
        role = "Leader" if ag == Party.GetPartyLeaderID() else "Ai Hero"
        mark = "Blessed" if ag in blessed_ids else "Unholy"
        PyImGui.text(f"[{ln}] {nm} ({role}) [{mark}]")

    PyImGui.separator()
    if not _running and PyImGui.button("Run Blessing Sequence"):
        if AUTO_RUN_ALL and not is_leader:
            # non-leaders do nothing on button press
            pass
        else:
            if AUTO_RUN_ALL and is_leader:
                # leader flips the shared flag (and starts locally)
                write_run_flag(True)
                _runner.start()
                _running = True
            else:
                # single-client / per-client mode
                _runner.start()
                _running = True

    if _running:
        PyImGui.text("Running blessing sequence...")

    PyImGui.end()

def main():
    me = Player.GetAgentID()
    on_imgui_render(me)
