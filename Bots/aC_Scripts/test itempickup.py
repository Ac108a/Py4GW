# item_pickup_tester.py  — sticky pickup edition
from Py4GWCoreLib import *  # PyImGui, GLOBAL_CACHE, ConsoleLog, Console, Utils, Routines, etc.

MODULE_NAME = "ItemInteract Tester (Sticky)"

# add/replace these imports
from typing import Callable, Optional
from typing import Generator as Gen

# --- simple coroutine runner state ---
_active: Optional[Gen[None, None, None]] = None

# UI state
_coords_text = "-20000,10000"     # "x,y" for coord-based tests
_model_text  = "0x1"              # model id input (decimal or hex)
_radius      = 1200               # search radius (also used by Dump Nearby)
_timeout_ms  = 10000              # timeout for sticky loops
_tolerance   = 250                # reach tolerance (not strictly needed; kept for UI parity)

# ------------------ helpers ------------------

def _parse_xy(text: str):
    t = text.strip().replace(" ", "")
    xs, ys = t.split(",", 1)
    return int(xs), int(ys)

def _parse_int_or_hex(s: str) -> int:
    s = s.strip().lower()
    if s.startswith("0x"):
        return int(s, 16)
    return int(float(s))  # accepts "123" or "123.0"

def DebugDumpNearbyItemModels(radius=1500):
    px, py = GLOBAL_CACHE.Player.GetXY()
    try:
        from Py4GWCoreLib import AgentArray
        items = AgentArray.GetItemArray() or []
        gadgets = AgentArray.GetGadgetArray() or []
    except Exception:
        items, gadgets = [], []

    def _dist(aid):
        try:
            x, y = GLOBAL_CACHE.Agent.GetXY(aid)
            return Utils.Distance((px, py), (x, y))
        except Exception:
            return 9e9

    def _mid(aid):
        try:
            mid = GLOBAL_CACHE.Item.GetModelID(aid)
            if mid: return int(mid)
        except: pass
        try:
            mid = GLOBAL_CACHE.Agent.GetModelID(aid)
            if mid: return int(mid)
        except: pass
        return 0

    ConsoleLog("Yield", f"--- Nearby (<= {radius}) item/gadget model ids ---", Console.MessageType.Info)
    for lab, arr in (("Item", items), ("Gadget", gadgets)):
        for a in arr:
            d = _dist(a)
            if d <= radius:
                ConsoleLog("Yield", f"{lab}: id={a} model={_mid(a)} dist={int(d)}", Console.MessageType.Info)

# ------------- STICKY PICKUP CORE (no reliance on current target) -------------

def _nearest_item_near_xy(cx: float, cy: float, search_radius: float = 900.0) -> int:
    from Py4GWCoreLib import AgentArray
    live = AgentArray.GetItemArray() or []
    best = None  # (agent_id, dist)
    for aid in live:
        try:
            ix, iy = GLOBAL_CACHE.Agent.GetXY(aid)
            d = Utils.Distance((cx, cy), (ix, iy))
            if d <= search_radius and (best is None or d < best[1]):
                best = (aid, d)
        except Exception:
            continue
    return best[0] if best else 0

def _interact_by_id(agent_id: int) -> Gen[None, None, None]:
    if not agent_id:
        return
    try:
        # direct, no-target interact avoids target clashes with the build manager
        GLOBAL_CACHE.Player.Interact(agent_id, False)
        return
    except Exception:
        pass
    # fallback: change target then interact (slower, but safe)
    try:
        yield from Yield.Agents.ChangeTarget(agent_id)
        yield from Yield.Player.InteractTarget()
    except Exception:
        pass

def _nearest_item_by_model(model_id: int, search_radius: float = 1200.0) -> int:
    from Py4GWCoreLib import AgentArray
    px, py = GLOBAL_CACHE.Player.GetXY()
    live = AgentArray.GetItemArray() or []
    best = None
    for aid in live:
        try:
            if GLOBAL_CACHE.Agent.GetModelID(aid) != model_id:
                continue
            ix, iy = GLOBAL_CACHE.Agent.GetXY(aid)
            d = Utils.Distance((px, py), (ix, iy))
            if d <= search_radius and (best is None or d < best[1]):
                best = (aid, d)
        except Exception:
            continue
    return best[0] if best else 0

def _sticky_pickup_by_model_via_XY(
    model_id: int,
    search_radius: float = 1200.0,
    timeout_ms: int = 12000,
    poll_ms: int = 75,
    reclick_ms: int = 350,
    settle_ms: int = 250
) -> Gen[None, None, bool]:
    from Py4GWCoreLib import AgentArray
    start = Utils.GetBaseTimestamp()
    last_click = 0
    last_seen_id = 0
    last_seen_xy = (0, 0)

    while Utils.GetBaseTimestamp() - start < timeout_ms:
        live = AgentArray.GetItemArray() or []
        if last_seen_id and last_seen_id not in live:
            yield from Routines.Yield.wait(settle_ms)
            ConsoleLog(MODULE_NAME, "Sticky-Model(Xy): success.", Console.MessageType.Info)
            return True

        # acquire nearest item with this model id (and remember its XY)
        cand = _nearest_item_by_model(model_id, search_radius=search_radius)
        if cand:
            last_seen_id = cand
            try:
                last_seen_xy = GLOBAL_CACHE.Agent.GetXY(cand)
            except Exception:
                pass

        # if we have a last_seen_xy, click those coords using the legacy call
        now = Utils.GetBaseTimestamp()
        if last_seen_xy != (0, 0) and now - last_click >= reclick_ms:
            ix, iy = last_seen_xy
            _ = (yield from Yield.Agents.InteractWithItemXY(int(ix), int(iy)))
            last_click = now

        yield from Routines.Yield.wait(poll_ms)

    ConsoleLog(MODULE_NAME, "Sticky-Model(Xy): timed out.", Console.MessageType.Warning)
    return False

def _sticky_pickup_nearest_via_XY(
    x: int,
    y: int,
    search_radius: float = 900.0,
    timeout_ms: int = 10000,
    poll_ms: int = 75,
    reclick_ms: int = 350,   # <= same cadence the legacy path uses; stays safe
    settle_ms: int = 250
) -> Gen[None, None, bool]:
    from Py4GWCoreLib import AgentArray
    start = Utils.GetBaseTimestamp()
    last_click = 0
    last_seen_id = 0

    while Utils.GetBaseTimestamp() - start < timeout_ms:
        live = AgentArray.GetItemArray() or []
        # success: last clicked/seen candidate vanished
        if last_seen_id and last_seen_id not in live:
            yield from Routines.Yield.wait(settle_ms)
            ConsoleLog(MODULE_NAME, "Sticky-Xy: success.", Console.MessageType.Info)
            return True

        # pick a candidate near (x,y) to watch for disappearance
        cand = _nearest_item_near_xy(x, y, search_radius=search_radius)
        if cand:
            last_seen_id = cand

        # re-click with LEGACY call on a gentle cadence
        now = Utils.GetBaseTimestamp()
        if now - last_click >= reclick_ms:
            # this is the ONLY interact we do — the known-stable one
            _ = (yield from Yield.Agents.InteractWithItemXY(x, y))
            last_click = now

        yield from Routines.Yield.wait(poll_ms)

    ConsoleLog(MODULE_NAME, "Sticky-Xy: timed out.", Console.MessageType.Warning)
    return False

# -------------------- test routines (generators) --------------------

def _run_interact_item_xy(x: int, y: int) -> Gen[None, None, None]:
    ConsoleLog(MODULE_NAME, f"Starting InteractWithItemXY at ({x}, {y})", Console.MessageType.Info)
    ok = (yield from Yield.Agents.InteractWithItemXY(x, y))
    ConsoleLog(MODULE_NAME, f"InteractWithItemXY finished: {ok}", Console.MessageType.Info)

def _run_pickup_nearest_sticky(x: int, y: int, radius: float, timeout_ms: int) -> Gen[None, None, None]:
    ConsoleLog(MODULE_NAME, f"Sticky (legacy-XY) nearest @({x},{y}) r={int(radius)} t={timeout_ms}ms", Console.MessageType.Info)
    ok = (yield from _sticky_pickup_nearest_via_XY(x, y, search_radius=radius, timeout_ms=timeout_ms))
    ConsoleLog(MODULE_NAME, f"Done: {ok}", Console.MessageType.Info)

def _run_pickup_by_model(mid: int, radius: float, timeout_ms: int) -> Gen[None, None, None]:
    ConsoleLog(MODULE_NAME, f"Sticky (legacy-XY) by model {mid} r={int(radius)} t={timeout_ms}ms", Console.MessageType.Info)
    ok = (yield from _sticky_pickup_by_model_via_XY(mid, search_radius=radius, timeout_ms=timeout_ms))
    ConsoleLog(MODULE_NAME, f"Done: {ok}", Console.MessageType.Info)

# -------------------- runner --------------------

def _start(coro: Generator):
    global _active
    _active = coro

def _step():
    global _active
    if _active is None:
        return
    try:
        next(_active)
    except StopIteration:
        ConsoleLog(MODULE_NAME, "Routine completed.", Console.MessageType.Debug)
        _active = None
    except Exception as e:
        ConsoleLog(MODULE_NAME, f"Routine error: {e}", Console.MessageType.Error)
        _active = None

# -------------------- UI / main --------------------

def main():
    global _coords_text, _model_text, _radius, _timeout_ms, _tolerance, _active

    PyImGui.begin("Item / Quest Pickup Tester", PyImGui.WindowFlags.AlwaysAutoResize)

    # Section 1: InteractWithItemXY (legacy) + Sticky Nearest
    PyImGui.text("Legacy vs. Sticky (Nearest @ Coords)")
    _coords_text = PyImGui.input_text("Coords (x,y)", _coords_text, 64)
    PyImGui.same_line(0, 5)
    if PyImGui.button("Use Target"):
        tid = GLOBAL_CACHE.Player.GetTargetID()
        if tid:
            tx, ty = GLOBAL_CACHE.Agent.GetXY(tid)
            _coords_text = f"{int(tx)},{int(ty)}"
        else:
            ConsoleLog(MODULE_NAME, "No current target.", Console.MessageType.Warning)

    if _active is None:
        PyImGui.separator()
        PyImGui.text("Actions:")
        if PyImGui.button("Start InteractXY (legacy)"):
            try:
                x, y = _parse_xy(_coords_text)
                _start(_run_interact_item_xy(x, y))
            except Exception as e:
                ConsoleLog(MODULE_NAME, f"Bad coords '{_coords_text}': {e}", Console.MessageType.Error)
        PyImGui.same_line(0, 10)
        if PyImGui.button("Start Sticky Nearest @ Coords"):
            try:
                x, y = _parse_xy(_coords_text)
                _start(_run_pickup_nearest_sticky(x, y, float(_radius), int(_timeout_ms)))
            except Exception as e:
                ConsoleLog(MODULE_NAME, f"Bad coords '{_coords_text}': {e}", Console.MessageType.Error)

    PyImGui.separator()

    # Section 2: Sticky Pickup by Model ID
    PyImGui.text("Sticky Pickup by Model ID")
    _model_text = PyImGui.input_text("Model ID (dec or hex 0x..)", _model_text, 32)
    _radius     = PyImGui.input_int("Search radius", int(_radius))
    _timeout_ms = PyImGui.input_int("Timeout (ms)", int(_timeout_ms))
    _tolerance  = PyImGui.input_int("Tolerance (unused)", int(_tolerance))

    PyImGui.same_line(0, 10)
    if PyImGui.button("Dump Nearby Models"):
        DebugDumpNearbyItemModels(radius=int(_radius))

    if _active is None:
        if PyImGui.button("Start Sticky PickupByModelId"):
            try:
                mid = _parse_int_or_hex(_model_text)
                _start(_run_pickup_by_model(mid, float(_radius), int(_timeout_ms)))
            except Exception as e:
                ConsoleLog(MODULE_NAME, f"Bad model id '{_model_text}': {e}", Console.MessageType.Error)
    else:
        PyImGui.text("Status: RUNNING")
        if PyImGui.button("Stop"):
            ConsoleLog(MODULE_NAME, "Routine aborted by user.", Console.MessageType.Warning)
            _active = None

    PyImGui.end()
    _step()

if __name__ == "__main__":
    main()
