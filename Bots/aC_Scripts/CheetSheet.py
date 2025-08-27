from Py4GWCoreLib import *
from Py4GWCoreLib import GLOBAL_CACHE, Utils, Range
from HeroAI.cache_data import CacheData
import time

stop_requested = False
path_handler = None
movement_handler = None
aggro_handler = None
target_xy_text = ""  

def follow_path_with_aggro_coroutine(
    path_points,
    aggro_range: float = Range.Area.value,      # when we consider "engaged"
    seek_radius: float = 3500.0,                # how far off the player to look for packs
    max_step_ms: int = 150,                     # throttle approach move commands
    loot_grace_ms: int = 1200                   # short stand-still after combat ends
):
    cd = CacheData()

    # --- state used by the pause logic ---
    last_move_tick = 0
    last_scan_tick = 0
    target_id = 0
    in_combat = False
    pause_until = 0  # timestamp used for loot grace after combat

    def nearest_enemy_within(radius: float):
        """Pick the closest valid hostile within 'radius' of player."""
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
        """Issue a short approach move toward the enemy (non-yielding)."""
        nonlocal last_move_tick
        now = Utils.GetBaseTimestamp()
        if now - last_move_tick < max_step_ms:
            return
        px, py = GLOBAL_CACHE.Player.GetXY()
        ax, ay = GLOBAL_CACHE.Agent.GetXY(aid)
        d = Utils.Distance((px, py), (ax, ay))
        # aim to stop just inside aggro_range
        stop_at = max(d - (aggro_range - 50.0), 0.0)
        if stop_at <= 0.0:
            return
        # small step in the direction of the enemy
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

    # --- the pause callback passed into FollowPath ---
    def pause_fn():
        nonlocal target_id, in_combat, pause_until, last_scan_tick
        now = Utils.GetBaseTimestamp()

        # 1) If we are in looting or inside the grace window, keep pausing
        if cd.in_looting_routine or (pause_until and now < pause_until):
            return True

        # 2) If we are currently in aggro, keep pausing and let HeroAI fight
        enemies = GLOBAL_CACHE.AgentArray.GetEnemyArray()
        if cd.InAggro(enemies, aggro_range=aggro_range):
            in_combat = True
            return True

        # 3) Combat just ended → start a short grace window for loot to trigger
        if in_combat:
            in_combat = False
            pause_until = now + loot_grace_ms
            return True

        # 4) No combat: scan for a nearby pack to approach
        if now - last_scan_tick >= 250:  # light scan throttle
            target_id = nearest_enemy_within(seek_radius)
            last_scan_tick = now

        if target_id:
            # If we’re *not yet* in aggro, nudge closer toward the pack
            if not cd.InAggro(enemies, aggro_range=aggro_range):
                approach_enemy(target_id)
            # Stay paused while we’re closing/engaging
            return True

        # 5) Nothing to do → resume path
        return False

    # Walk the path, pausing whenever pause_fn() says so.
    # While paused, the callback above issues approach moves (non-yielding),
    # then waits through combat + looting before we continue the path.
    yield from Routines.Yield.Movement.FollowPath(
        path_points=path_points,
        custom_pause_fn=pause_fn
    )




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


    if PyImGui.begin("Cheet Sheet", PyImGui.WindowFlags.AlwaysAutoResize):

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
            PyImGui.text_colored("format: -20344, 10632", (255, 255, 0, 255))  # subtle hint

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
                    global stop_requested
                    path2d = [(px, py) for (px, py, _) in result_path]
                    mover = Routines.Yield.Movement.FollowPath(path2d)
                    while True:
                        if stop_requested:
                            return
                        try:
                            yield next(mover)
                        except StopIteration:
                            return
                GLOBAL_CACHE.Coroutines.append(follow_path_coroutine())
            if PyImGui.button("Follow Path FIGHTING") and result_path:
                stop_requested = False  # reset before launch

                def follow_path_fighting_coroutine():
                    global stop_requested
                    # convert 3D nav result to 2D (x,y) for the movement routine
                    path2d = [(px, py) for (px, py, _) in result_path]

                    # drive the generator manually so we can stop on demand
                    mover = follow_path_with_aggro_coroutine(path_points=path2d)
                    while True:
                        if stop_requested:
                            return
                        try:
                            yield next(mover)
                        except StopIteration:
                            return

                GLOBAL_CACHE.Coroutines.append(follow_path_fighting_coroutine())
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

if __name__ == "__main__":
    main()

