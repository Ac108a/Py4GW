from Py4GWCoreLib import *
from PyQuishAi.map_loader import load_map_data
from Py4GW_widget_manager import handler
import time  # used in travel_to_outpost
from HeroAI.cache_data import CacheData
from Widgets.Blessed import Get_Blessed
from typing import Iterable, Union, Tuple, Any, Sequence, Optional, Dict, Callable


# Faction keys for donation helpers
LUXON   = "luxon"
KURZICK = "kurzick"

Waypoint = Union[
    Tuple[float, float],
    Tuple[float, float, str],
    Tuple[float, float, str, Any],
    Sequence[Any],
]

# --- Special Actions Registry ---
_SPECIAL_ACTIONS = {}
cached_enabled_widgets = []
# --- Pathing pause gate used by FollowPath(custom_pause_fn) ---
_PATHING_PAUSE_PRE_MS_DEFAULT = 3000
_PATHING_PAUSE_POST_MS_DEFAULT = 6000
_PATHING_PAUSE_UNTIL = 0

def _request_pathing_pause(ms: int):
    """Extend the global pause window so FollowPath() stays paused for ms."""
    global _PATHING_PAUSE_UNTIL
    try:
        ms = int(ms)
    except Exception:
        ms = 0
    now = Utils.GetBaseTimestamp()
    _PATHING_PAUSE_UNTIL = max(_PATHING_PAUSE_UNTIL, now + max(0, ms))

def _is_pathing_paused() -> bool:
    """Return True while a pause window is active."""
    return Utils.GetBaseTimestamp() < _PATHING_PAUSE_UNTIL

def _wrap_action_with_pathing_pause(name, coro_fn, pre_ms=None, post_ms=None):
    """
    Wrap any special action with a small pathing pause before/after.
    We don't use skill-casting in this bot, so we do not touch it at all.
    """
    pre  = _PATHING_PAUSE_PRE_MS_DEFAULT  if pre_ms  is None else int(pre_ms)
    post = _PATHING_PAUSE_POST_MS_DEFAULT if post_ms is None else int(post_ms)

    def _wrapped(x, y, payload):
        # Tell FollowPath(custom_pause_fn) to pause briefly before we act
        if pre > 0:
            _request_pathing_pause(pre)
            yield from Routines.Yield.wait(pre)
        try:
            return (yield from coro_fn(x, y, payload))
        finally:
            # And pause briefly after the action
            if post > 0:
                _request_pathing_pause(post)
                yield from Routines.Yield.wait(post)
    return _wrapped

def register_special_action(name: str, coro_fn, *, pause_pathing: bool = True, pre_ms=None, post_ms=None):
    """
    Register a special action (string -> coroutine fn).
    - If pause_pathing is True (default), the action is wrapped so pathing is
      paused around it using the default pre/post waits (or overrides).
    - coro_fn signature: (x: float, y: float, payload: Any) -> generator
    """
    if pause_pathing and name not in ("PausePathing", "StartPathing"):
        coro_fn = _wrap_action_with_pathing_pause(name, coro_fn, pre_ms=pre_ms, post_ms=post_ms)
    _SPECIAL_ACTIONS[name] = coro_fn

def _enter_challenge_default(x, y, payload):
    # Minimal default: enter mission/challenge and wait a bit.
    ConsoleLog("FSM", f"[SpecialAction] Entering challenge at ({x:.0f}, {y:.0f}) with payload: {payload}", Console.MessageType.Info)    
    GLOBAL_CACHE.Map.EnterChallenge()
    wait_for = 3000 if payload is None else int(payload)
    return (yield from Routines.Yield.wait(wait_for))

def _action_interact_item(x, y, payload):
    # payload ignored; simple item pickup
    return (yield from Yield.Agents.InteractWithItemXY(x, y))

# Late getter to avoid circular imports
def _get_runner_fsm():
    try:
        import sys
        mod = sys.modules.get("PyQuishAi.runner_singleton")
        if mod and getattr(mod, "runner_fsm", None) is not None:
            return mod.runner_fsm
        import importlib
        mod = importlib.import_module("PyQuishAi.runner_singleton")
        return getattr(mod, "runner_fsm", None)
    except Exception:
        return None

def _coerce_dialog_ids(payload):
    """Return a flat list[int] from payload (int/str/list/tuple), supporting hex like '0x85'."""
    if payload in (None, "", 0, "0"):
        return []

    def _one(v):
        if isinstance(v, int):
            return [v]
        if isinstance(v, str):
            parts = v.split(",") if "," in v else [v]
            out = []
            for p in parts:
                s = p.strip()
                if not s:
                    continue
                try:
                    out.append(int(s, 16) if s.lower().startswith("0x") else int(s))
                except Exception:
                    pass
            return out
        return []

    if isinstance(payload, (list, tuple)):
        ids = []
        for item in payload:
            ids.extend(_one(item))
        return ids

    return _one(payload)

def _action_interact(x: float, y: float, payload):
    """
    Interact with agent at (x,y).
    If payload contains dialog ids, send them in order (default 500ms between).
    """
    ok = (yield from Routines.Yield.Agents.InteractWithAgentXY(x, y))
    if not ok:
        ConsoleLog("FSM", f"[SpecialAction] Interact failed at ({int(x)},{int(y)}).", Console.MessageType.Warning)
        return

    dialog_ids = _coerce_dialog_ids(payload)
    if not dialog_ids:
        # just interact; nothing else
        return

    for did in dialog_ids:
        GLOBAL_CACHE.Player.SendDialog(did)
        yield from Routines.Yield.wait(500)   # tiny pause between dialogs

def _action_bless(x: float, y: float, payload):

    try:
        Get_Blessed()
    except Exception as e:
        ConsoleLog("FSM", f"[Bless] Get_Blessed() raised: {e}", Console.MessageType.Warning)

    yield from Routines.Yield.wait(300)

# Register the action name you’re using in map files:
register_special_action("Bless",             _action_bless)             # wrapped
register_special_action("Interact",          _action_interact)          # wrapped
register_special_action("InteractDialog",    _action_interact)          # wrapped
register_special_action("InteractItem",      _action_interact_item)     # wrapped
register_special_action("PickUpNearestItem", _action_interact_item)     # wrapped
register_special_action("EnterMission",      _enter_challenge_default)  # wrapped
register_special_action("EnterChallenge",    _enter_challenge_default)  # wrapped
# toggles must not be wrapped (or they’d recurse)

def _parse_waypoint(wp):
    """
    Accepts:
      (x, y)
      (x, y, "Action")
      (x, y, "Action", payload)
    Returns: (x, y, action_name_or_None, payload_or_None)
    """
    if not isinstance(wp, (list, tuple)) or len(wp) < 2:
        raise ValueError(f"Invalid waypoint: {wp}")
    x, y = float(wp[0]), float(wp[1])
    action = None
    payload = None
    if len(wp) >= 3 and isinstance(wp[2], str):
        action = wp[2]
        if len(wp) >= 4:
            payload = wp[3]
    return x, y, action, payload

def follow_path_with_specials(path_points, progress_cb=None):
    """
    Yield-based runner that:
      - Follows normal path chunks (no action)
      - When encountering an action waypoint, flushes the chunk, moves to that waypoint, runs the action coroutine, then continues.
    Compatible with plain (x, y) lists (does nothing special).
    """
    chunk = []

    def _flush_chunk():
        if chunk:
            yield from Routines.Yield.Movement.FollowPath(chunk, progress_callback=progress_cb, custom_pause_fn=_is_pathing_paused)
            chunk.clear()

    for wp in path_points:
        x, y, action, payload = _parse_waypoint(wp)

        if action is None:
            chunk.append((x, y))
            continue

        yield from _flush_chunk()

        # move to the action waypoint itself
        yield from Routines.Yield.Movement.FollowPath([(x, y)], progress_callback=progress_cb, custom_pause_fn=_is_pathing_paused)

        coro = _SPECIAL_ACTIONS.get(action)
        if coro is None:
            ConsoleLog("FSM", f"[SpecialAction] '{action}' not registered; skipping.", Console.MessageType.Warning)
        else:
            ConsoleLog("FSM", f"[SpecialAction] Running '{action}' @ ({x:.0f}, {y:.0f})", Console.MessageType.Info)
            yield from coro(x, y, payload)

    if chunk:
        yield from Routines.Yield.Movement.FollowPath(chunk, progress_callback=progress_cb, custom_pause_fn=_is_pathing_paused)

MyList = [
    "Skip Cinematics",
    "Titles",
    "Environment Upkeeper",
    "Messaging"
]

class PyQuishAiFSMHelpers:
    def __init__(self):
        self.current_map_script = None
        self.current_map_data = None
        self.current_path_index = 0
        self.last_valid_next_point = None

    # ---- Debug HUD helpers ----
    def _path_hud_enabled(self) -> bool:
        return getattr(self, "_path_hud_on", True)

    def set_path_hud(self, enabled: bool = True):
        setattr(self, "_path_hud_on", bool(enabled))

    def _render_path_hud(self, dbg: Dict[str, Any], force: bool = False):
        """Throttled console 'panel' with the most useful live info."""
        try:
            now = Utils.GetBaseTimestamp()
            last = dbg.get("last_hud_ts", 0)
            if not force and now - last < 750:   # ~0.75s cadence
                return
            dbg["last_hud_ts"] = now

            total   = dbg.get("total", 0)
            cursor  = dbg.get("cursor", 0)
            state   = dbg.get("state", "init")
            next_i  = dbg.get("next_idx", 0)
            next_xy = dbg.get("next_xy", (0, 0))
            visited = dbg.get("visited", [])
            specials= dbg.get("specials", [])
            done_sp = dbg.get("executed_count", 0)
            all_sp  = sum(1 for s in specials if s)

            # Small window around cursor
            lo = max(0, cursor - 3)
            hi = min(total, cursor + 4)
            window = []
            for i in range(lo, hi):
                mark = "Visited" if visited[i] else "."
                spec = specials[i] or ""
                if spec:
                    spec = f"{spec}"
                window.append(f"{i}:{mark}{('/'+spec) if spec else ''}")

            ConsoleLog("FSM","[HUD] idx {}/{}  next {} ({:.0f},{:.0f})  state={}  specials {}/{} | [{}]".format(cursor, total, next_i, next_xy[0], next_xy[1], state, done_sp, all_sp, "  ".join(window)),Console.MessageType.Debug)
        except Exception:
            pass

    def load_map_script(self, script_name):
        """
        Given a chain entry like:
            "Eye_Of_The_North__1_Eotn_To_Gunnars"
        (note the DOUBLE-underscore between region and run),
        split it properly and delegate to map_loader.
        """
        if "__" in script_name:
            region, run = script_name.split("__", 1)
        else:
            region, run = script_name.split("_", 1)

        data = load_map_data(region, run)
        self.current_map_data = data

        # Reset per-run vanquish flags
        self.vanquish_attempted_in_run = False
        self.vanquish_success_in_run = False

        return {
            "outpost_path":     data["outpost_path"],
            "segments":         data["segments"],
            "ids":              data["ids"],
        }

    def travel_to_outpost(self, outpost_id):
        ConsoleLog("PyQuishAiFSM", f"Initiating safe travel to outpost ID {outpost_id}")
        if GLOBAL_CACHE.Map.IsExplorable():
            while not Routines.Checks.Map.MapValid():
                yield from Routines.Yield.wait(250)
            # === STEP 1: Broadcast resign command to other accounts ===
            accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
            sender_email = GLOBAL_CACHE.Player.GetAccountEmail()
            for account in accounts:
                ConsoleLog("PyQuishAiFSM", f"Resigning account: {account.AccountEmail}")
                GLOBAL_CACHE.ShMem.SendMessage(sender_email, account.AccountEmail, SharedCommandType.Resign, (0, 0, 0, 0))
            # === STEP 2: Wait for defeat to trigger Return To Outpost ===
            timeout = 20
            start_time = time.time()

            while time.time() - start_time < timeout:
                if (GLOBAL_CACHE.Map.IsMapReady() and GLOBAL_CACHE.Party.IsPartyLoaded() and GLOBAL_CACHE.Map.IsExplorable() and GLOBAL_CACHE.Party.IsPartyDefeated()):
                    GLOBAL_CACHE.Party.ReturnToOutpost()
                    break

                yield from Routines.Yield.wait(500)
            else:
                ConsoleLog("PyQuishAiFSM", "Resign return timed out. Stopping bot.", Console.MessageType.Error)
                return

            # === STEP 3: Wait for outpost map to load ===
            timeout = 20
            start_time = time.time()

            while time.time() - start_time < timeout:
                if Routines.Checks.Map.MapValid() and GLOBAL_CACHE.Map.IsOutpost():
                    ConsoleLog("PyQuishAiFSM", "Returned to outpost. Proceeding to travel...")
                    break

                yield from Routines.Yield.wait(500)
            else:
                ConsoleLog("PyQuishAiFSM", "Failed to load outpost. Aborting travel.", Console.MessageType.Error)
                return

            # === STEP 4: Perform actual outpost travel (optional) ===
            # If caller passes None/0, we *only* ensure we're in an outpost
            # (via resign/return above) and skip explicit map travel.
        if not outpost_id:
            ConsoleLog("PyQuishAiFSM","Outpost ID not provided; staying in the current outpost (no travel).",Console.MessageType.Info)
            return
        else:
            ConsoleLog("PyQuishAiFSM", f"Traveling to outpost ID {outpost_id}")
            yield from Routines.Yield.Map.TravelToOutpost(outpost_id)

    def wait_for_map_load(self, expected_map_id, timeout=15000):
        """Wait until we’re in the expected map."""
        return Routines.Yield.Map.WaitforMapLoad(expected_map_id, timeout=timeout)
    
    def wait_for_any_outpost(self, timeout=15000):
        """
        Wait until we're in *any* outpost. Useful after travel_to_outpost(0)
        where we don't know the exact map id. timeout in ms.
        """
        import time
        deadline = time.time() + (timeout / 1000.0)
        while time.time() < deadline:
            if Routines.Checks.Map.MapValid() and GLOBAL_CACHE.Map.IsOutpost():
                return
            yield from Routines.Yield.wait(2050)
        ConsoleLog("PyQuishAiFSM", "Timeout waiting for outpost.", Console.MessageType.Warning)

    def follow_path(self, path_coords):
        """
        Follow a path that may contain special-action waypoints:
        (x, y)                              -> normal waypoint
        (x, y, "Action")                    -> run registered action at that point
        (x, y, "Action", payload)           -> run action with payload

        Keeps self.current_path_index and self.last_valid_next_point updated
        exactly as before, even though we execute the path in chunks.
        """
        flat_xy: list[Tuple[float, float]] = []
        for wp in (path_coords or []):
            if isinstance(wp, (list, tuple)) and len(wp) >= 2:
                flat_xy.append((float(wp[0]), float(wp[1])))

        chunk_start = 0

        def make_progress_cb(start, length):
            def _cb(progress: float):
                if length <= 0:
                    return
                idx_in_chunk = max(0, min(length - 1, int(progress * length)))
                idx = start + idx_in_chunk
                self.current_path_index = idx + 1
                if 0 <= idx < len(flat_xy):
                    self.last_valid_next_point = flat_xy[idx]
            return _cb

        def parse_wp(wp: Waypoint):
            action = None
            payload = None
            if not (isinstance(wp, (list, tuple)) and len(wp) >= 2):
                raise ValueError(f"Invalid waypoint: {wp}")
            if len(wp) >= 3 and isinstance(wp[2], str):
                action = wp[2]
                if len(wp) >= 4:
                    payload = wp[3]
            return (float(wp[0]), float(wp[1])), action, payload

        def flush_chunk(points):
            nonlocal chunk_start
            if not points:
                return
            cb = make_progress_cb(chunk_start, len(points))
            yield from Routines.Yield.Movement.FollowPath(points, progress_callback=cb, custom_pause_fn=_is_pathing_paused)
            chunk_start += len(points)

        buffer_chunk = []
        for wp in (path_coords or []):
            (x, y), action, payload = parse_wp(wp)

            if action is None:
                buffer_chunk.append((x, y))
                continue
            if buffer_chunk:
                yield from flush_chunk(buffer_chunk)
                buffer_chunk = []

            cb = make_progress_cb(chunk_start, 1)
            yield from Routines.Yield.Movement.FollowPath([(x, y)], progress_callback=cb, custom_pause_fn=_is_pathing_paused)
            chunk_start += 1

            coro = _SPECIAL_ACTIONS.get(action)
            if coro:
                ConsoleLog("FSM", f"[SpecialAction] {action} @ ({int(x)}, {int(y)})", Console.MessageType.Info)
                yield from coro(x, y, payload)
            else:
                ConsoleLog("FSM", f"[SpecialAction] '{action}' not registered; skipping.", Console.MessageType.Warning)

        # trailing normals
        if buffer_chunk:
            yield from flush_chunk(buffer_chunk)

    def follow_path_with_aggro(
        self,
        path_coords,
        *,
        aggro_range: float = Range.Area.value,
        seek_radius: float = 2000,
        max_step_ms: int = 450,
        loot_grace_ms: int = 2000,
        external_exit_check: Optional[Callable[[], bool]] = None
    ):
        """
        Deterministic aggro pathing with specials:
        • Walks chunk-by-chunk to the *next* special index, executes it, repeats.
        • Never relies on mid-run handoffs to catch specials, so nothing is skipped.
        • Full console HUD: visited[], specials[], next target, and state.
        • Loud logs for chase/backtrack/pause reasons.
        """

        # ---------- Normalize to parallel arrays ----------
        flat_xy: list[Tuple[float, float]] = []
        actions: list[Tuple[Optional[str], Any]] = []
        for wp in (path_coords or []):
            if isinstance(wp, (list, tuple)) and len(wp) >= 2:
                x, y = float(wp[0]), float(wp[1])
                act = None
                payload = None
                if len(wp) >= 3 and isinstance(wp[2], str):
                    act = wp[2]
                    if len(wp) >= 4:
                        payload = wp[3]
                flat_xy.append((x, y))
                actions.append((act, payload))

        n_points = len(flat_xy)
        specials_names = [(a or None) for (a, _) in actions]
        total_specials = sum(1 for a in specials_names if a)

        ConsoleLog("FSM", f"[AggroPath] START — {n_points} points, {total_specials} specials", Console.MessageType.Info)

        # ---------- Debug HUD model ----------
        dbg = {
            "total": n_points,
            "visited": [False] * n_points,
            "specials": specials_names[:],
            "cursor": 0,
            "state": "init",
            "next_idx": 0,
            "next_xy": flat_xy[0] if n_points else (0.0, 0.0),
            "executed_count": 0,
            "last_hud_ts": 0,
        }
        self._last_path_debug = dbg
        if self._path_hud_enabled():
            self._render_path_hud(dbg, force=True)

        # ---------- Progress callback ----------
        def make_progress_cb(start, length):
            def _cb(progress: float):
                if length <= 0:
                    return
                idx_in_chunk = max(0, min(length - 1, int(progress * length)))
                idx = start + idx_in_chunk
                dbg["cursor"] = idx
                if 0 <= idx < n_points:
                    dbg["visited"][idx] = True
                    self.current_path_index = idx + 1
                    self.last_valid_next_point = flat_xy[idx]
                    dbg["next_idx"] = min(n_points - 1, idx + 1)
                    dbg["next_xy"] = flat_xy[dbg["next_idx"]]
                if self._path_hud_enabled():
                    self._render_path_hud(dbg)
            return _cb

        # ---------- Local helpers ----------
        cd = CacheData()
        ap = AutoPathing()
        executed_actions: set[int] = set()

        last_move_tick = 0
        last_scan_tick = 0
        target_id = 0
        in_combat = False
        pause_until = 0

        def nearest_enemy_within(radius: float) -> int:
            px, py = GLOBAL_CACHE.Player.GetXY()
            enemies = GLOBAL_CACHE.AgentArray.GetEnemyArray()
            best, best_d = 0, 9e9
            if not enemies:
                return 0
            for a in enemies:
                if not GLOBAL_CACHE.Agent.IsAlive(a):
                    continue
                ax, ay = GLOBAL_CACHE.Agent.GetXY(a)
                d = Utils.Distance((px, py), (ax, ay))
                if d <= radius and d < best_d:
                    best, best_d = a, d
            return best

        def approach_enemy(aid: int):
            nonlocal last_move_tick
            now = Utils.GetBaseTimestamp()
            if now - last_move_tick < max_step_ms:
                return
            px, py = GLOBAL_CACHE.Player.GetXY()
            ax, ay = GLOBAL_CACHE.Agent.GetXY(aid)
            d = Utils.Distance((px, py), (ax, ay))
            stop_at = max(d - (aggro_range - 50.0), 0.0)
            if stop_at <= 0.0:
                return
            vx, vy = (ax - px), (ay - py)
            mag = (vx * vx + vy * vy) ** 0.5 or 1.0
            nx = px + vx / mag * stop_at
            ny = py + vy / mag * stop_at
            try:
                GLOBAL_CACHE.Player.ChangeTarget(aid)
            except Exception:
                pass
            GLOBAL_CACHE.Player.Move(nx, ny)
            last_move_tick = now

        # Pause function used by FollowPath
        def pause_fn() -> bool:
            nonlocal target_id, in_combat, pause_until, last_scan_tick
            # Pathing pause around specials
            if _is_pathing_paused():
                dbg["state"] = "paused"
                if self._path_hud_enabled():
                    self._render_path_hud(dbg)
                return True

            now = Utils.GetBaseTimestamp()

            # Loot or grace
            if cd.in_looting_routine or (pause_until and now < pause_until):
                dbg["state"] = "looting" if cd.in_looting_routine else "grace"
                if self._path_hud_enabled():
                    self._render_path_hud(dbg)
                return True

            # Aggro?
            enemies = GLOBAL_CACHE.AgentArray.GetEnemyArray()
            if cd.InAggro(enemies, aggro_range=aggro_range):
                dbg["state"] = "combat"
                in_combat = True
                if self._path_hud_enabled():
                    self._render_path_hud(dbg)
                return True

            # Combat just ended → short grace to pick up loot
            if in_combat:
                in_combat = False
                pause_until = now + loot_grace_ms
                dbg["state"] = "grace"
                if self._path_hud_enabled():
                    self._render_path_hud(dbg)
                return True

            # Scan for a nearby pack to approach
            if now - last_scan_tick >= 250:
                target_id = nearest_enemy_within(seek_radius)
                last_scan_tick = now

            if target_id:
                px, py = GLOBAL_CACHE.Player.GetXY()
                ax, ay = GLOBAL_CACHE.Agent.GetXY(target_id)
                nav = ap.get_navmesh()
                los = True
                try:
                    if nav:
                        los = nav.has_line_of_sight((px, py), (ax, ay))
                except Exception:
                    los = True

                if los:
                    dbg["state"] = "chase(LOS)"
                    if not cd.InAggro(enemies, aggro_range=aggro_range):
                        approach_enemy(target_id)
                    if self._path_hud_enabled():
                        self._render_path_hud(dbg)
                    return True
                else:
                    # When LOS is blocked, Autopath chunk will be inserted *between* specials.
                    dbg["state"] = "chase(A*)"
                    if self._path_hud_enabled():
                        self._render_path_hud(dbg, force=True)
                    # Returning True lets FollowPath yield; the outer loop will do an A* hop.
                    return True

            dbg["state"] = "walk"
            if self._path_hud_enabled():
                self._render_path_hud(dbg)
            return False

        def exit_condition() -> bool:
            # Let caller abort early if they want (e.g., reverse sweep controller).
            if external_exit_check is None:
                return False
            try:
                return bool(external_exit_check())
            except Exception:
                return False

        # ---------- Main deterministic loop (chunk to next special) ----------
        cursor = 0
        while cursor < n_points:
            # A) If a target is set but no LOS, do a short autopath hop, then continue.
            if target_id:
                try:
                    px, py = GLOBAL_CACHE.Player.GetXY()
                    z  = GLOBAL_CACHE.Agent.GetZPlane(GLOBAL_CACHE.Player.GetAgentID())
                    ax, ay = GLOBAL_CACHE.Agent.GetXY(target_id)
                    path3d = yield from ap.get_path((px, py, z), (ax, ay, z), smooth_by_los=True, margin=100.0, step_dist=500.0)
                except Exception:
                    path3d = []
                if path3d:
                    ConsoleLog("FSM", f"[AggroPath] A* hop with {len(path3d)} pts…", Console.MessageType.Debug)
                    path2d = [(x, y) for (x, y, *_ ) in path3d]
                    yield from Routines.Yield.Movement.FollowPath(path2d, progress_callback=None, custom_pause_fn=_is_pathing_paused)
                    if self._path_hud_enabled():
                        self._render_path_hud(dbg, force=True)
                    # clear the target — we’ll rescan in pause_fn
                    target_id = 0

            # B) Find next unexecuted special at/after cursor
            next_sp = None
            for i in range(cursor, n_points):
                if actions[i][0] and i not in executed_actions:
                    next_sp = i
                    break

            # C) Walk to (and include) that special — or finish tail if none left
            end_idx = (next_sp + 1) if next_sp is not None else n_points
            if cursor < end_idx:
                subpath = flat_xy[cursor:end_idx]
                cb = make_progress_cb(cursor, len(subpath))
                yield from Routines.Yield.Movement.FollowPath(
                    path_points=subpath,
                    progress_callback=cb,
                    custom_pause_fn=pause_fn,
                    custom_exit_condition=exit_condition
                )

            # If caller asked us to exit (e.g., vanquish sweep), stop now.
            if external_exit_check is not None:
                try:
                    if external_exit_check():
                        ConsoleLog("FSM", "[AggroPath] External exit check requested stop.", Console.MessageType.Info)
                        break
                except Exception:
                    pass

            # D) If there was a special at end_idx - 1, execute it now
            if next_sp is not None and next_sp not in executed_actions:
                x, y = flat_xy[next_sp]
                act, payload = actions[next_sp]
                ConsoleLog("FSM", f"[SpecialAction] {act} @ ({int(x)}, {int(y)})", Console.MessageType.Info)
                coro = _SPECIAL_ACTIONS.get(act)
                if coro:
                    yield from coro(x, y, payload)
                else:
                    ConsoleLog("FSM", f"[SpecialAction] '{act}' not registered; skipping.", Console.MessageType.Warning)
                executed_actions.add(next_sp)
                dbg["executed_count"] = len(executed_actions)
                if self._path_hud_enabled():
                    self._render_path_hud(dbg, force=True)

            # Advance past whatever we just walked/executed
            cursor = end_idx

            # E) Vanquish probe (info only)
            try:
                if GLOBAL_CACHE.Map.IsVanquishable() and GLOBAL_CACHE.Party.IsHardMode():
                    killed = int(GLOBAL_CACHE.Map.GetFoesKilled() or 0)
                    remaining = int(GLOBAL_CACHE.Map.GetFoesToKill() or 0)
                    total = max(0, killed + remaining)
                    if total > 0:
                        self.vanquish_attempted_in_run = True
                        if remaining == 0:
                            self.vanquish_success_in_run = True
            except Exception:
                pass

        ConsoleLog("FSM", "[AggroPath] END", Console.MessageType.Info)

    def get_next_path_point(self):
        """Returns the current active path point based on progress (XY only)."""
        if not self.current_map_data:
            return self.last_valid_next_point

        def xy_only(seq: Iterable[Waypoint]) -> list[Tuple[float, float]]:
            out: list[Tuple[float, float]] = []
            for wp in (seq or []):
                if isinstance(wp, (list, tuple)) and len(wp) >= 2:
                    out.append((float(wp[0]), float(wp[1])))
            return out

        all_points: list[Tuple[float, float]] = []
        if self.current_map_data.get("outpost_path"):
            all_points.extend(xy_only(self.current_map_data["outpost_path"]))
        if self.current_map_data.get("segments"):
            for seg in self.current_map_data["segments"]:
                all_points.extend(xy_only(seg.get("path", [])))

        if not all_points:
            return self.last_valid_next_point

        idx = min(self.current_path_index, len(all_points) - 1)
        self.last_valid_next_point = all_points[idx]
        return all_points[idx]
    
    def enable_custom_widget_list(self):
        """Enable only the widgets in ALWAYS_ENABLE_WIDGETS list."""
        for widget_name in MyList:
            handler.enable_widget(widget_name)
            ConsoleLog("WidgetHandler", f"'{widget_name}' is Enabled", Console.MessageType.Info)

    def cache_and_disable_all_widgets(self):
        global cached_enabled_widgets
        cached_enabled_widgets = handler.list_enabled_widgets()
        ConsoleLog("WidgetHandler", f"Currently enabled widgets: {cached_enabled_widgets}", Console.MessageType.Debug)

        for widget_name in cached_enabled_widgets:
            handler.disable_widget(widget_name)
        ConsoleLog("WidgetHandler", f"Disabled {len(cached_enabled_widgets)} widgets", Console.MessageType.Info)

    def reverse_sweep_if_not_vanquished(self, path_coords):
        """
        If the current map is vanquishable, in Hard Mode, and foes remain,
        do a one-pass reverse sweep from last waypoint back to the first.
        Uses plain XY waypoints (no specials) to avoid re-triggering actions.
        """
        try:
            if not (GLOBAL_CACHE.Map.IsVanquishable() and GLOBAL_CACHE.Party.IsHardMode()):
                return
            killed = int(GLOBAL_CACHE.Map.GetFoesKilled() or 0)
            remaining = int(GLOBAL_CACHE.Map.GetFoesToKill() or 0)
            total = max(0, killed + remaining)
            if total <= 0 or remaining <= 0:
                return  # nothing to do
        except Exception:
            return  # if counters aren't available, fail quietly

        # Build a reversed XY-only path (strip any specials)
        reversed_xy = []
        for wp in (path_coords or []):
            if isinstance(wp, (list, tuple)) and len(wp) >= 2:
                reversed_xy.append((float(wp[0]), float(wp[1])))
        reversed_xy.reverse()
        if not reversed_xy:
            return

        ConsoleLog("FSM", f"[Vanquish] Remaining foes: {remaining}. Starting reverse sweep…", Console.MessageType.Info)
        # Reuse hunter logic (works fine with XY-only)
        yield from self.follow_path_with_aggro(reversed_xy, external_exit_check=lambda: (GLOBAL_CACHE.Map.GetFoesToKill() or 0) == 0)

        # Update vanquish flags for stats (best-effort)
        try:
            killed2    = int(GLOBAL_CACHE.Map.GetFoesKilled() or 0)
            remaining2 = int(GLOBAL_CACHE.Map.GetFoesToKill() or 0)
            total2     = max(0, killed2 + remaining2)
            if total2 > 0:
                self.vanquish_attempted_in_run = True
                if remaining2 == 0:
                    self.vanquish_success_in_run = True
        except Exception:
            pass

    def restore_cached_widgets(self):
        global cached_enabled_widgets
        if not cached_enabled_widgets:
            ConsoleLog("WidgetHandler", "No cached widgets to restore!", Console.MessageType.Warning)
            return

        for widget_name in cached_enabled_widgets:
            handler.enable_widget(widget_name)

        ConsoleLog("WidgetHandler", f"Restored {len(cached_enabled_widgets)} widgets", Console.MessageType.Info)
        cached_enabled_widgets = []

    def BroadcastDonateToGuild(self, faction: str):
        """
        Travel to the correct outpost and broadcast DonateToGuild for that faction.
        faction: "luxon" or "kurzick" (case-insensitive).
        Returns True if broadcast happened, False otherwise.
        """
        if not Routines.Checks.Map.MapValid():
            ConsoleLog("OutpostRunnerFSM", "Map invalid; not broadcasting DonateToGuild.", Console.MessageType.Warning)
            return False
        key = (faction or "").strip().lower()
        if key in ("lux", "luxon"):
            expected_map_id = 193   # Cavalon
            outpost_name    = "Cavalon"
            faction_enum    = 1     # Messaging.DonateToGuild expects 1 for Luxon
            announce_msg    = "Donating Luxon faction to Guild"
        elif key in ("kur", "kurzick"):
            expected_map_id = 77    # House zu Heltzer
            outpost_name    = "House zu Heltzer"
            faction_enum    = 2     # Messaging.DonateToGuild expects 2 for Kurzick
            announce_msg    = "Donating Kurzick faction to Guild"
        else:
            ConsoleLog("OutpostRunnerFSM", f"Unknown faction '{faction}' (use 'luxon' or 'kurzick').", Console.MessageType.Warning)
            return False

        # Travel if needed
        current = GLOBAL_CACHE.Map.GetMapID()
        if current != expected_map_id:
            yield from self.travel_to_outpost(expected_map_id)
            yield from self.wait_for_map_load(expected_map_id, timeout=15000)
            yield from Routines.Yield.wait(3000)  # brief settle

        # Verify arrival
        if GLOBAL_CACHE.Map.GetMapID() != expected_map_id:
            ConsoleLog("OutpostRunnerFSM", f"Failed to arrive in {outpost_name}; skipping broadcast.", Console.MessageType.Warning)
            return False

        # Gather accounts and split: others first, self last
        accounts = GLOBAL_CACHE.ShMem.GetAllAccountData() or []
        sender   = GLOBAL_CACHE.Player.GetAccountEmail()

        others = [a for a in accounts if getattr(a, "AccountEmail", None) and a.AccountEmail != sender]
        me     = [a for a in accounts if getattr(a, "AccountEmail", None) and a.AccountEmail == sender]

        # 500ms base delay
        BASE_DELAY_MS = 500

        # Send to everyone else first (staggered)
        for i, acc in enumerate(others):
            ConsoleLog("OutpostRunnerFSM", f"{announce_msg}: {acc.AccountEmail}", Console.MessageType.Info)
            GLOBAL_CACHE.ShMem.SendMessage(sender, acc.AccountEmail, SharedCommandType.DonateToGuild, (faction_enum, 0, 0, 0))

            if i + 1 < len(others):
                jitter = 25 if (i & 1) else 0
                yield from Routines.Yield.wait(BASE_DELAY_MS + jitter)

        # trigger our own donation last
        if me:
            ConsoleLog("OutpostRunnerFSM", f"{announce_msg}: {sender} (self, last)", Console.MessageType.Info)
            GLOBAL_CACHE.ShMem.SendMessage(sender, sender, SharedCommandType.DonateToGuild, (faction_enum, 0, 0, 0))

        return True

    def _wait_for_donate_completion(self, timeout_ms: int = 60000):
        """
        Simple completion: we're done when the 'active' unspent faction drops below 5,000.
        'Active' = the side with the larger unspent balance at the start (or any side >= 5,000).
        No message polling; just watch the Player counters.
        """
        from Py4GWCoreLib import Player
        CHUNK = 5000                 # donation/swap unit; done when unspent < 5k
        SAMPLE_MS = 250              # poll cadence
        STABILIZE_MS = 500           # tiny settle after crossing threshold

        deadline = Utils.GetBaseTimestamp() + timeout_ms

        # snapshot starting balances
        p = Player.player_instance()
        lux = int(getattr(p, "current_luxon", 0) or 0)
        kur = int(getattr(p, "current_kurzick", 0) or 0)

        # if we're already below 5k on both, nothing to wait for
        if lux < CHUNK and kur < CHUNK:
            return True

        # choose the "active" side to watch (the one we intended to spend)
        active = "lux" if lux >= kur else "kur"

        last_val = lux if active == "lux" else kur

        while Utils.GetBaseTimestamp() < deadline:
            # refresh
            p = Player.player_instance()
            lux = int(getattr(p, "current_luxon", 0) or 0)
            kur = int(getattr(p, "current_kurzick", 0) or 0)
            curr = lux if active == "lux" else kur

            # success criterion: active side dropped below 5k
            if curr < CHUNK:
                # brief settle to let UI/counters catch up
                settle_by = Utils.GetBaseTimestamp() + STABILIZE_MS
                while Utils.GetBaseTimestamp() < settle_by:
                    yield from Routines.Yield.wait(SAMPLE_MS)
                ConsoleLog("OutpostRunnerFSM", "Donation complete (unspent < 5,000).", Console.MessageType.Info)
                return True

            # (optional) detect progress; purely informational
            if curr != last_val:
                ConsoleLog("OutpostRunnerFSM", f"Unspent {active} -> {curr}", Console.MessageType.Debug)
                last_val = curr

            yield from Routines.Yield.wait(SAMPLE_MS)

        ConsoleLog("OutpostRunnerFSM", "Donate wait timed out; continuing.", Console.MessageType.Warning)
        return False

    def auto_donate_faction(self, threshold: int = 30000):
        """
        First-step FSM hook:
        - If unspent Luxon or Kurzick >= threshold, travel to the correct outpost,
        broadcast DonateToGuild (others first, self last), wait for *our own* donation,
        and record actual donated amount to ChainStatistics (this account only).
        - If neither meets threshold, no-op.
        """
        if not Routines.Checks.Map.MapValid():
            return

        from Py4GWCoreLib import Player
        TITLE_MAX = 10_000_000
        CHUNK = 5000

        p = Player.player_instance()
        lux_unspent = int(getattr(p, "current_luxon", 0) or 0)
        kur_unspent = int(getattr(p, "current_kurzick", 0) or 0)
        lux_total   = int(getattr(p, "total_earned_luxon", 0) or 0)
        kur_total   = int(getattr(p, "total_earned_kurzick", 0) or 0)

        # Nothing to do?
        if lux_unspent < threshold and kur_unspent < threshold:
            ConsoleLog("OutpostRunnerFSM", f"Auto-donate: below threshold ({threshold}). L:{lux_unspent} K:{kur_unspent}", Console.MessageType.Debug)
            return

        # Pick the larger side (ensures it's >= threshold)
        if lux_unspent >= kur_unspent:
            chosen = LUXON      # "luxon"
            pre_unspent = lux_unspent
            pre_total   = lux_total
        else:
            chosen = KURZICK    # "kurzick"
            pre_unspent = kur_unspent
            pre_total   = kur_total

        # We only count as "donation" (not swap) if title isn't maxed at the time
        will_donate = pre_total < TITLE_MAX

        ConsoleLog("OutpostRunnerFSM",
                f"Auto-donate trigger: {chosen} (L:{lux_unspent} K:{kur_unspent} thr:{threshold})",
                Console.MessageType.Info)

        # Travel + broadcast (others first, self last)
        ok = (yield from self.BroadcastDonateToGuild(chosen))
        if not ok:
            return

        # Wait only for *our* donation to finish
        yield from self._wait_for_donate_completion(timeout_ms=60000)

        # Snapshot after the donate/swap finished
        p = Player.player_instance()
        post_unspent = int(getattr(p, "current_luxon"  if chosen == LUXON else "current_kurzick", 0) or 0)

        # Compute how much actually left our unspent pool
        delta = max(0, pre_unspent - post_unspent)

        # Snap to 5k chunks (deposit/swap unit)
        if delta >= CHUNK:
            delta = (delta // CHUNK) * CHUNK

        # Record stats only if this was a *donation* (not swaps at max title)
        if will_donate and delta > 0:
            try:
                # late import to avoid circular refs
                import sys, importlib
                mod = sys.modules.get("PyQuishAi.runner_singleton") or importlib.import_module("PyQuishAi.runner_singleton")
                fsm = getattr(mod, "runner_fsm", None)
                if fsm and getattr(fsm, "chain_stats", None):
                    fsm.chain_stats.record_donation(chosen, delta)  # "luxon"|"kurzick", amount
                    ConsoleLog("OutpostRunnerFSM", f"Recorded donation: {chosen} {delta:,}", Console.MessageType.Info)
            except Exception:
                pass
        else:
            if delta > 0:
                ConsoleLog("OutpostRunnerFSM", f"Faction spent ({delta:,}) but not counted as donation (title maxed).", Console.MessageType.Debug)
