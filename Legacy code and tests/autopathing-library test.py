import Py4GW
from Py4GWCoreLib import *
import math
import time

stop_requested = False
path_handler = None
movement_handler = None
aggro_handler = None
target_xy_text = ""  

class FollowPathAndAggro:
    def __init__(self, path_handler, follow_handler, aggro_range=1250, log_actions=False):
        self.path_handler       = path_handler
        self.follow_handler     = follow_handler
        self.aggro_range        = aggro_range
        self.log_actions        = log_actions
        self._last_scanned_enemy = None
        # ── THROTTLING STATE ───────────────────────────────────────────
        # only re-scan if we've moved this far (¾ of aggro_range)
        self._scan_move_thresh   = aggro_range * 0.75
        # track the last position we scanned at
        self._last_scan_pos      = Player.GetXY()
        # also still guard by time interval (ms)
        self._scan_interval_ms   = 500
        self._enemy_scan_timer   = Timer()
        # for ChangeTarget/Move dedupe
        self._last_target_id     = None
        self._last_move_target   = None
        # instrumentation counters & timer
        self._stats_start_time      = time.time()
        self.enemy_array_fetches    = 0
        self.change_target_calls    = 0
        self.move_calls             = 0
        self._stats_interval_secs   = 30.0

        self._last_enemy_check      = Timer()
        self._current_target_enemy  = None
        self._mode                  = 'path'
        self._current_path_point    = None
        self.status_message         = "Waiting to begin..."

    def _throttled_scan(self):
        curr_pos   = Player.GetXY()
        dist_moved = Utils.Distance(curr_pos, self._last_scan_pos)

        if (dist_moved >= self._scan_move_thresh
                or self._enemy_scan_timer.HasElapsed(self._scan_interval_ms)):
            # re-do the heavy call
            self._last_scanned_enemy = self._find_nearest_enemy()
            self._last_scan_pos      = curr_pos
            self._enemy_scan_timer.Reset()

        return self._last_scanned_enemy

    def _find_nearest_enemy(self):
        # instrumentation
        self.enemy_array_fetches += 1

        my_pos = Player.GetXY()
        enemies = [
            e for e in AgentArray.GetEnemyArray()
            if Agent.IsAlive(e) and Utils.Distance(my_pos, Agent.GetXY(e)) <= self.aggro_range
        ]
        if not enemies:
            return None
        return AgentArray.Sort.ByDistance(enemies, my_pos)[0]

    def _approach_enemy(self):
        if not self._current_target_enemy or not Agent.IsAlive(self._current_target_enemy):
            self._current_target_enemy = self._find_nearest_enemy()
            if not self._current_target_enemy:
                self._mode = 'path'
                self.status_message = "No enemies nearby."
                return

        if self._enemy_scan_timer.HasElapsed(self._scan_interval_ms):
            new_enemy = self._find_nearest_enemy()
            if new_enemy:
                self._current_target_enemy = new_enemy
            self._enemy_scan_timer.Reset()

        if not self._current_target_enemy:
            self._mode = 'path'
            self.status_message = "Returning to path mode."
            return

        try:
            tx, ty = Agent.GetXY(self._current_target_enemy)
        except Exception:
            self._mode = 'path'
            self.status_message = "Error getting target position."
            return

        # ── target only if it’s a new one ───────────────────────────
        if self._current_target_enemy != self._last_target_id:
            Player.ChangeTarget(self._current_target_enemy)
            self.change_target_calls += 1
            self._last_target_id = self._current_target_enemy

        # ── move only if the coords differ ──────────────────────────
        new_move = (int(tx), int(ty))
        if new_move != self._last_move_target:
            Player.Move(*new_move)
            self.move_calls += 1
            self._last_move_target = new_move

        self.status_message = f"Approaching target at ({int(tx)}, {int(ty)})"
        my_pos = Player.GetXY()
        if Utils.Distance(my_pos, (tx, ty)) <= Range.Area.value:
            self.status_message = "In combat range."

    def _advance_to_next_point(self):
        if not self.follow_handler.is_following():
            next_point = self.path_handler.advance()
            if not next_point:
                # SAFETY: No next point found
                self.status_message = "No valid next waypoint! Stopping pathing."
                if self.log_actions:
                    ConsoleLog("FollowPathAndAggro", "PathHandler returned None – halting movement.", Console.MessageType.Warning)
                
                # Optional fallback: reset to start or nearest point
                if hasattr(self.path_handler, "reset"):
                    self.path_handler.reset()  # resets to first node
                    retry_point = self.path_handler.advance()
                    if retry_point:
                        self._current_path_point = retry_point
                        self.follow_handler.move_to_waypoint(*retry_point)
                        self.status_message = f"Path reset → moving to {retry_point}"
                        ConsoleLog("FollowPathAndAggro", f"Path reset after failure, moving to {retry_point}", Console.MessageType.Warning)
                return  # do nothing else this tick
            
            # If we got a valid next_point
            self._current_path_point = next_point
            self.follow_handler.move_to_waypoint(*next_point)
            self.status_message = f"Moving to {next_point}"
            if self.log_actions:
                ConsoleLog("FollowPathAndAggro", f"Moving to {next_point}", Console.MessageType.Info)
        else:
            # SAFETY: make sure _current_path_point is valid
            if not self._current_path_point:
                self.status_message = "Lost current path point, hang on a second"
                if self.log_actions:
                    pass
                self.follow_handler._following = False
                return
            
            px, py = Player.GetXY()
            tx, ty = self._current_path_point
            if Utils.Distance((px, py), (tx, ty)) <= 250:
                self.follow_handler._following = False
                self.follow_handler.arrived    = True
                self.status_message            = "Arrived at waypoint."

    def _maybe_log_stats(self):
        elapsed = time.time() - self._stats_start_time
        if elapsed >= self._stats_interval_secs:
            ConsoleLog(
                "FollowPathAndAggro",
                f"[Stats over {int(elapsed)}s] fetches={self.enemy_array_fetches}, "
                f"changeTarget={self.change_target_calls}, move={self.move_calls}",
                Console.MessageType.Info
            )
            # reset
            self._stats_start_time     = time.time()
            self.enemy_array_fetches   = 0
            self.change_target_calls   = 0
            self.move_calls            = 0

    def update(self):
        # periodically emit stats
        self._maybe_log_stats()

        if CacheData().in_looting_routine:
            self.status_message = "Waiting for looting to finish..."
            self.follow_handler.update()
            return

        if self._mode == 'path':
            target = self._throttled_scan()
            if target:
                self._current_target_enemy = target
                self._last_enemy_check.Reset()
                self._mode = 'combat'
                self.status_message = "Switching to combat mode."
                if self.log_actions:
                    ConsoleLog("FollowPathAndAggro", "Switching to COMBAT mode", Console.MessageType.Warning)
            else:
                self._advance_to_next_point()

        elif self._mode == 'combat':
            if not self._current_target_enemy or not Agent.IsAlive(self._current_target_enemy):
                self._mode                  = 'path'
                self._current_target_enemy  = None
                self.status_message         = "Combat done. Switching to path mode."
                return

            # ── unified, throttled scan ──────────────────────────────
            self._current_target_enemy = self._throttled_scan()
            if not self._current_target_enemy:
                self._mode = 'path'
                self.status_message = "No enemies (throttled)—returning to path."
                return

            try:
                tx, ty = Agent.GetXY(self._current_target_enemy)
            except Exception:
                self._mode                 = 'path'
                self._current_target_enemy = None
                self.status_message        = "Enemy fetch failed. Returning to path."
                return

            # ── target only if it’s a new one ───────────────────────────
            if self._current_target_enemy != self._last_target_id:
                Player.ChangeTarget(self._current_target_enemy)
                self.change_target_calls += 1
                self._last_target_id = self._current_target_enemy

            # ── move only if the coords differ ──────────────────────────
            new_move = (int(tx), int(ty))
            if new_move != self._last_move_target:
                Player.Move(*new_move)
                self.move_calls += 1
                self._last_move_target = new_move

            self.status_message = f"Closing in on enemy at ({int(tx)}, {int(ty)})"

        # always let follow-handler tick
        self.follow_handler.update()




# Globals for testing
path = []
result_path = []
x, y = 6698, 16095

start_process_time = time.time()
elapsed_time = 0.0
pathing_object = AutoPathing()
path_requested = False

# Config options
smooth_by_los = True
smooth_by_chaikin = False
margin = 100.0
step_dist = 500.0
chaikin_iterations = 1

def _parse_xy(text: str):
    """Accepts '-20344, 10632' or '-20344 10632' (comma/space/semicolon)."""
    s = text.strip().replace(",", " ").replace(";", " ")
    parts = [p for p in s.split() if p]
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None

def main():
    def draw_path(points, rgba):
        if points and len(points) >= 2:
            color = Color(*rgba).to_dx_color()
            for i in range(len(points) - 1):
                x1, y1, z1 = points[i]
                x2, y2, z2 = points[i + 1]
                z1 = DXOverlay.FindZ(x1, y1) - 125
                z2 = DXOverlay.FindZ(x2, y2) - 125
                DXOverlay().DrawLine3D(x1, y1, z1, x2, y2, z2, color, False)

    global result_path, x, y, start_process_time, pathing_object, path_requested, elapsed_time
    global smooth_by_los, smooth_by_chaikin, margin, step_dist, chaikin_iterations


    if PyImGui.begin("Pathing Test", PyImGui.WindowFlags.AlwaysAutoResize):

        player_pos = GLOBAL_CACHE.Player.GetXY()

        global target_xy_text, x, y
        if not target_xy_text:
            target_xy_text = f"{x}, {y}"

        # Single input: "-20344, 10632" (also accepts space- or semicolon-separated)
        target_xy_text = PyImGui.input_text("Target (x, y)", target_xy_text)

        parsed = _parse_xy(target_xy_text)
        if parsed is not None:
            x, y = parsed
        else:
            PyImGui.same_line()
            PyImGui.text_colored("← format: -20344, 10632", 1.0, 0.4, 0.4, 1.0)  # subtle hint
            
        PyImGui.separator()
        smooth_by_los = PyImGui.checkbox("Smooth by LOS", smooth_by_los)
        margin = PyImGui.input_float("LOS Margin", margin)
        step_dist = PyImGui.input_float("LOS Step Dist", step_dist)

        if PyImGui.button("Search Path"):
            start_process_time = time.time()
            path_requested = True
            def search_path_coroutine():
                global result_path, path_requested, elapsed_time
                zplane = GLOBAL_CACHE.Agent.GetZPlane(GLOBAL_CACHE.Player.GetAgentID())
                result_path = yield from pathing_object.get_path(
                    (player_pos[0], player_pos[1], zplane),
                    (x, y, zplane),
                    smooth_by_los=smooth_by_los,
                    margin=margin,
                    step_dist=step_dist,
                    smooth_by_chaikin=smooth_by_chaikin,
                    chaikin_iterations=chaikin_iterations
                )
                path_requested = False
                yield
                elapsed_time = time.time() - start_process_time
                

            GLOBAL_CACHE.Coroutines.append(search_path_coroutine())

        PyImGui.separator()
        if path_requested:
            PyImGui.text("Searching for path...")
        else:
            if result_path:
                PyImGui.text(f"Path found with {len(result_path)} points")
                PyImGui.text(f"NavMesh load time: {elapsed_time:.2f} seconds")
            global stop_requested  
            if PyImGui.button("Follow Path") and result_path:
                def follow_path_coroutine():
                    path2d = [(x, y) for (x, y, _) in result_path]
                    yield from Routines.Yield.Movement.FollowPath(path2d)
                    yield
                GLOBAL_CACHE.Coroutines.append(follow_path_coroutine())
            if PyImGui.button("Follow Path FIGHTING") and result_path:
                stop_requested = False  # ✅ Reset before launching coroutine
                GLOBAL_CACHE.Coroutines.append(follow_path_with_aggro_coroutine())
            PyImGui.same_line(0,5)
            if PyImGui.button("Stop"):
                stop_requested = True

                if PyImGui.collapsing_header("Path Points", PyImGui.TreeNodeFlags.DefaultOpen):
                    for i, point in enumerate(result_path):
                        PyImGui.text(f"Point {i}: ({point[0]:.1f}, {point[1]:.1f}, {point[2]:.1f})")
            else:
                PyImGui.text("No path found or search not initiated.")

        PyImGui.end()

    draw_path(result_path, (255, 255, 0, 255))  # Yellow


def follow_path_with_aggro_coroutine():
    global aggro_handler, stop_requested

    path2d = [(x, y) for (x, y, _) in result_path]
    global path_handler, movement_handler

    path_handler = Routines.Movement.PathHandler(path2d)
    movement_handler = Routines.Movement.FollowXY()
    aggro_handler = FollowPathAndAggro(path_handler, movement_handler, aggro_range=2500, log_actions=True)

    while not Routines.Movement.IsFollowPathFinished(path_handler, movement_handler) and not stop_requested:
        aggro_handler.update()
        yield from Routines.Yield.wait(150)

    # ✅ Cleanup
    ConsoleLog("AggroHandler", "Path complete or stopped by user.", Console.MessageType.Info)
    aggro_handler = None
    stop_requested = False

if __name__ == "__main__":
    main()

