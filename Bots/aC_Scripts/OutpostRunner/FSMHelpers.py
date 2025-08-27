from Py4GWCoreLib import *
from OutpostRunner.map_loader import load_map_data
from Py4GW_widget_manager import handler
import time  # used in travel_to_outpost
from typing import Iterable, Union, Tuple, Any, Sequence
from HeroAI.cache_data import CacheData

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
_SKILLCAST_PRE_MS_DEFAULT  = 1000     # wait after stopping, before action
_SKILLCAST_POST_MS_DEFAULT = 1500    # wait after restarting, after action

def _wrap_action_with_skill_pause(name, coro_fn, pre_ms=None, post_ms=None):
    pre = _SKILLCAST_PRE_MS_DEFAULT if pre_ms  is None else int(pre_ms)
    post= _SKILLCAST_POST_MS_DEFAULT if post_ms is None else int(post_ms)

    def _wrapped(x, y, payload):
        fsm = _get_runner_fsm()
        # Stop → (optional pre wait)
        try:
            if fsm: fsm._stop_skill_casting()
        except Exception:
            pass
        if pre > 0:
            yield from Routines.Yield.wait(pre)

        # Run the original action
        result = None
        try:
            result = (yield from coro_fn(x, y, payload))
        finally:
            # Start → (optional post wait) always, even if action fails
            try:
                if fsm: fsm._start_skill_casting()
            except Exception:
                pass
            if post > 0:
                yield from Routines.Yield.wait(post)
        return result
    return _wrapped

def register_special_action(name: str, coro_fn, *, pause_skills: bool = True, pre_ms=None, post_ms=None):
    """
    Register a special action (string -> coroutine fn).
    - If pause_skills is True (default), the action is wrapped so skill-casting is
      paused around it using the default pre/post waits (or overrides).
    - coro_fn signature: (x: float, y: float, payload: Any) -> generator
    """
    if pause_skills and name not in ("StopSkillCasting", "StartSkillCasting"):
        coro_fn = _wrap_action_with_skill_pause(name, coro_fn, pre_ms=pre_ms, post_ms=post_ms)
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
        mod = sys.modules.get("OutpostRunner.runner_singleton")
        if mod and getattr(mod, "runner_fsm", None) is not None:
            return mod.runner_fsm
        import importlib
        mod = importlib.import_module("OutpostRunner.runner_singleton")
        return getattr(mod, "runner_fsm", None)
    except Exception:
        return None

def _action_stop_skill_casting(x, y, payload):
    fsm = _get_runner_fsm()
    if not fsm:
        ConsoleLog("FSM", "[SpecialAction] StopSkillCasting: runner_fsm not ready", Console.MessageType.Warning)
        return
    try:
        fsm._stop_skill_casting()
        ConsoleLog("FSM", "[SpecialAction] StopSkillCasting", Console.MessageType.Info)
    finally:
        try:
            delay = int(payload) if payload is not None else 0
        except Exception:
            delay = 0
        if delay > 0:
            yield from Routines.Yield.wait(delay)

def _action_start_skill_casting(x, y, payload):
    fsm = _get_runner_fsm()
    if not fsm:
        ConsoleLog("FSM", "[SpecialAction] StartSkillCasting: runner_fsm not ready", Console.MessageType.Warning)
        return
    try:
        fsm._start_skill_casting()
        ConsoleLog("FSM", "[SpecialAction] StartSkillCasting", Console.MessageType.Info)
    finally:
        try:
            delay = int(payload) if payload is not None else 0
        except Exception:
            delay = 0
        if delay > 0:
            yield from Routines.Yield.wait(delay)

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


register_special_action("Interact",          _action_interact)          # wrapped
register_special_action("InteractDialog",    _action_interact)          # wrapped
register_special_action("InteractItem",      _action_interact_item)     # wrapped
register_special_action("PickUpItem",        _action_interact_item)     # wrapped
register_special_action("EnterMission",      _enter_challenge_default)  # wrapped
register_special_action("EnterChallenge",    _enter_challenge_default)  # wrapped

# toggles must not be wrapped (or they’d recurse)
register_special_action("StopSkillCasting",  _action_stop_skill_casting,  pause_skills=False)
register_special_action("StartSkillCasting", _action_start_skill_casting, pause_skills=False)

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
            yield from Routines.Yield.Movement.FollowPath(chunk, progress_callback=progress_cb)
            chunk.clear()

    for wp in path_points:
        x, y, action, payload = _parse_waypoint(wp)

        if action is None:
            chunk.append((x, y))
            continue

        yield from _flush_chunk()
        yield from Routines.Yield.Movement.FollowPath([(x, y)], progress_callback=progress_cb)

        coro = _SPECIAL_ACTIONS.get(action)
        if coro is None:
            ConsoleLog("FSM", f"[SpecialAction] '{action}' not registered; skipping.", Console.MessageType.Warning)
        else:
            ConsoleLog("FSM", f"[SpecialAction] Running '{action}' @ ({x:.0f}, {y:.0f})", Console.MessageType.Info)
            yield from coro(x, y, payload)

    if chunk:
        yield from Routines.Yield.Movement.FollowPath(chunk, progress_callback=progress_cb)

MyList = [
    "Skip Cinematics",
    "Titles",
    "Environment Upkeeper",
    "Messaging"
]

class OutpostRunnerFSMHelpers:
    def __init__(self):
        self.current_map_script = None
        self.current_map_data = None
        self.current_path_index = 0
        self.last_valid_next_point = None

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
        return {
            "outpost_path":     data["outpost_path"],
            "segments":         data["segments"],
            "ids":              data["ids"],
        }

    def travel_to_outpost(self, outpost_id):
        ConsoleLog("OutpostRunnerFSM", f"Initiating safe travel to outpost ID {outpost_id}")
        if GLOBAL_CACHE.Map.IsExplorable():
            # === STEP 1: Broadcast resign command to other accounts ===
            accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
            sender_email = GLOBAL_CACHE.Player.GetAccountEmail()
            for account in accounts:
                ConsoleLog("OutpostRunnerFSM", f"Resigning account: {account.AccountEmail}")
                GLOBAL_CACHE.ShMem.SendMessage(sender_email, account.AccountEmail, SharedCommandType.Resign, (0, 0, 0, 0))
            # === STEP 2: Wait for defeat to trigger Return To Outpost ===
            timeout = 60
            start_time = time.time()

            while time.time() - start_time < timeout:
                if (GLOBAL_CACHE.Map.IsMapReady() and GLOBAL_CACHE.Party.IsPartyLoaded() and GLOBAL_CACHE.Map.IsExplorable() and GLOBAL_CACHE.Party.IsPartyDefeated()):
                    GLOBAL_CACHE.Party.ReturnToOutpost()
                    break

                yield from Routines.Yield.wait(500)
            else:
                ConsoleLog("OutpostRunnerFSM", "Resign return timed out. Stopping bot.", Console.MessageType.Error)
                return

            # === STEP 3: Wait for outpost map to load ===
            timeout = 60
            start_time = time.time()

            while time.time() - start_time < timeout:
                if Routines.Checks.Map.MapValid() and GLOBAL_CACHE.Map.IsOutpost():
                    ConsoleLog("OutpostRunnerFSM", "Returned to outpost. Proceeding to travel...")
                    break

                yield from Routines.Yield.wait(500)
            else:
                ConsoleLog("OutpostRunnerFSM", "Failed to load outpost. Aborting travel.", Console.MessageType.Error)
                return

        # === STEP 4: Perform actual outpost travel ===
        ConsoleLog("OutpostRunnerFSM", f"Traveling to outpost ID {outpost_id}")
        yield from Routines.Yield.Map.TravelToOutpost(outpost_id)

    def wait_for_map_load(self, expected_map_id, timeout=30000):
        """Wait until we’re in the expected map."""
        return Routines.Yield.Map.WaitforMapLoad(expected_map_id, timeout=timeout)

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
            yield from Routines.Yield.Movement.FollowPath(points, progress_callback=cb)
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
            yield from Routines.Yield.Movement.FollowPath([(x, y)], progress_callback=cb)
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

        # Travel if needed (uses your safe resign→outpost flow)
        current = GLOBAL_CACHE.Map.GetMapID()
        if current != expected_map_id:
            yield from self.travel_to_outpost(expected_map_id)
            yield from self.wait_for_map_load(expected_map_id, timeout=15000)

        # Verify arrival
        if GLOBAL_CACHE.Map.GetMapID() != expected_map_id:
            ConsoleLog("OutpostRunnerFSM", f"Failed to arrive in {outpost_name}; skipping broadcast.", Console.MessageType.Warning)
            return False

        # Broadcast DonateToGuild to all accounts (including self)
        accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
        sender   = GLOBAL_CACHE.Player.GetAccountEmail()
        for acc in accounts:
            ConsoleLog("OutpostRunnerFSM", f"{announce_msg}: {acc.AccountEmail}", Console.MessageType.Info)
            GLOBAL_CACHE.ShMem.SendMessage(
                sender,
                acc.AccountEmail,
                SharedCommandType.DonateToGuild,
                (faction_enum, 0, 0, 0)
            )

        return True


    def _wait_for_donate_completion(self, timeout_ms: int = 60000):
        """
        Wait until there are no active/running DonateToGuild messages sent by *this* account
        to anyone. Exits early when all such messages are finished or removed.
        """
        sender = GLOBAL_CACHE.Player.GetAccountEmail()
        deadline = Utils.GetBaseTimestamp() + timeout_ms

        def any_donate_pending():
            msgs = GLOBAL_CACHE.ShMem.GetAllMessages()
            if not msgs:
                return False
            for idx, m in msgs:
                if not m:
                    continue
                try:
                    if (m.SenderEmail == sender and
                        m.Command == SharedCommandType.DonateToGuild and
                        (m.Active or m.Running)):
                        return True
                except Exception:
                    pass
            return False

        while Utils.GetBaseTimestamp() < deadline:
            if not any_donate_pending():
                ConsoleLog("OutpostRunnerFSM", "All DonateToGuild messages finished.", Console.MessageType.Info)
                return True
            yield from Routines.Yield.wait(250)

        ConsoleLog("OutpostRunnerFSM", "DonateToGuild wait timed out; continuing.", Console.MessageType.Warning)
        return False


    def auto_donate_faction(self, threshold: int = 30000):
        """
        First-step FSM hook:
        - If unspent Luxon or Kurzick >= threshold, travel to the correct outpost,
        broadcast DonateToGuild, and wait until all clients finish.
        - If neither meets threshold, no-op (fast return).
        """
        if not Routines.Checks.Map.MapValid():
            return

        from Py4GWCoreLib import Player
        p = Player.player_instance()
        lux_unspent = int(getattr(p, "current_luxon", 0) or 0)
        kur_unspent = int(getattr(p, "current_kurzick", 0) or 0)

        # Nothing to do?
        if lux_unspent < threshold and kur_unspent < threshold:
            ConsoleLog("OutpostRunnerFSM", f"Auto-donate: below threshold ({threshold}). L:{lux_unspent} K:{kur_unspent}", Console.MessageType.Debug)
            return

        # Pick the larger side (ensures it's >= threshold)
        if lux_unspent >= kur_unspent:
            chosen = LUXON
        else:
            chosen = KURZICK

        ConsoleLog("OutpostRunnerFSM", f"Auto-donate trigger: {chosen} (L:{lux_unspent} K:{kur_unspent} thr:{threshold})", Console.MessageType.Info)

        ok = (yield from self.BroadcastDonateToGuild(chosen))
        if ok:
            # Wait until every DonateToGuild message from this sender is finished
            yield from self._wait_for_donate_completion(timeout_ms=60000)