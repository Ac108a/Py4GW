    def follow_path_with_aggro(
        self,
        path_coords,
        *,
        aggro_range: float = Range.Area.value,
        seek_radius: float = 2500.0,
        max_step_ms: int = 450,
        loot_grace_ms: int = 2000
    ):
        """
        Follow a path while hunting, but also run special actions placed on waypoints:
        (x, y)                      -> normal waypoint
        (x, y, "Action")            -> run registered action once when we reach it
        (x, y, "Action", payload)   -> run action with payload
        """

        # --- build aligned arrays: xy[] and actions[] (same length/indexing) ---
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

        # progress callback (same semantics as follow_path)
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

        cd = CacheData()

        # --- NEW: autopathing state for “chase” (ONLY used to move when hunting) ---
        ap = AutoPathing()
        pending_chase: Dict[str, Optional[Tuple[float, float]]] = {"pos": None}
        CHASE_MAX_POINTS = 10  # skip hunt if path longer than this

        # --- DEBUG: live autopath overlay (optional) ---
        DEBUG_AUTOPATH = True
        debug_path3d: list[tuple[float, float, float]] = []
        overlay_started = False

        def _draw_path3d(points, rgba=(255, 255, 0, 255)):
            if not points or len(points) < 2:
                return
            color = Color(*rgba).to_dx_color()
            for i in range(len(points) - 1):
                x1, y1, _ = points[i]
                x2, y2, _ = points[i + 1]
                z1 = DXOverlay.FindZ(x1, y1) - 125
                z2 = DXOverlay.FindZ(x2, y2) - 125
                DXOverlay().DrawLine3D(x1, y1, z1, x2, y2, z2, color, False)

        def _autopath_overlay():
            while True:
                try:
                    if DEBUG_AUTOPATH and debug_path3d:
                        _draw_path3d(debug_path3d)
                except Exception:
                    pass
                yield
        # --- end overlay ---

        # --- path cursor + skip control ---
        cursor = 0
        restart_requested = False
        new_cursor = 0          # next start index after a skip
        last_seg_seen = -1
        near_since_ts = 0
        threshold = seek_radius * 0.5  # “close enough”

        # --- run-once guard for actions we’ve already executed ---
        executed_actions: set[int] = set()

        # --- pre-hook: run action at the FIRST waypoint (index 0), if any ---
        if flat_xy and actions and actions[0][0] and 0 not in executed_actions:
            x0, y0 = flat_xy[0]
            act0, payload0 = actions[0]

            # walk to the first point
            cb0 = make_progress_cb(0, 1)
            yield from Routines.Yield.Movement.FollowPath(
                [(x0, y0)],
                progress_callback=cb0,
                custom_pause_fn=_is_pathing_paused
            )

            # run the action once
            coro0 = _SPECIAL_ACTIONS.get(act0)
            if coro0:
                ConsoleLog("FSM", f"[SpecialAction] {act0} @ ({int(x0)}, {int(y0)})", Console.MessageType.Info)
                yield from coro0(x0, y0, payload0)
            else:
                ConsoleLog("FSM", f"[SpecialAction] '{act0}' not registered; skipping.", Console.MessageType.Warning)
            executed_actions.add(0)

        def run_actions(from_idx: int, to_idx: int):
            """Execute actions for indices [from_idx, to_idx) exactly once."""
            lo = max(0, from_idx)
            hi = min(len(flat_xy), to_idx)
            for i in range(lo, hi):
                act, payload = actions[i]
                if not act or i in executed_actions:
                    continue
                coro = _SPECIAL_ACTIONS.get(act)
                x, y = flat_xy[i]
                if not coro:
                    ConsoleLog("FSM", f"[SpecialAction] '{act}' not registered; skipping.", Console.MessageType.Warning)
                    executed_actions.add(i)
                    continue
                ConsoleLog("FSM", f"[SpecialAction] {act} @ ({int(x)}, {int(y)})", Console.MessageType.Info)
                yield from coro(x, y, payload)
                executed_actions.add(i)

        # --- helpers used by the hunter/pause logic (UNCHANGED) ---
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
            # kept for compatibility; no longer used for movement when hunting
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

        def maybe_request_skip_ahead():
            """
            Skip only when we’ve truly progressed along the *current* segment.
            We increment cursor by exactly +1 after dwelling near the end of the segment,
            or when we’re within threshold of the next waypoint itself.
            """
            nonlocal new_cursor, restart_requested, last_seg_seen, near_since_ts

            if cursor >= len(flat_xy) - 1:
                return

            px, py = GLOBAL_CACHE.Player.GetXY()
            x1, y1 = flat_xy[cursor]
            x2, y2 = flat_xy[cursor + 1]

            vx, vy = (x2 - x1), (y2 - y1)
            wx, wy = (px - x1), (py - y1)
            denom = (vx * vx + vy * vy) or 1.0
            t = (wx * vx + wy * vy) / denom
            t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
            qx = x1 + t * vx
            qy = y1 + t * vy

            d_seg  = Utils.Distance((px, py), (qx, qy))
            d_next = Utils.Distance((px, py), (x2, y2))

            near_end = (t >= 0.85 and d_seg <= threshold) or (d_next <= threshold * 0.75)
            if near_end:
                now = Utils.GetBaseTimestamp()
                if last_seg_seen != cursor:
                    last_seg_seen = cursor
                    near_since_ts = now
                elif now - near_since_ts >= 250:
                    new_cursor = cursor + 1
                    restart_requested = True
            else:
                if last_seg_seen == cursor:
                    last_seg_seen = -1
                    near_since_ts = 0

        # pause state
        last_move_tick = 0
        last_scan_tick = 0
        target_id = 0
        in_combat = False
        pause_until = 0

        # exit condition toggled by maybe_request_skip_ahead()
        def exit_condition():
            return restart_requested

        # --- pause callback (UNCHANGED semantics) ---
        def pause_fn():
            # global pathing pause (used by special actions)
            if _is_pathing_paused():
                maybe_request_skip_ahead()
                return True

            nonlocal target_id, in_combat, pause_until, last_scan_tick
            nonlocal pending_chase, restart_requested, new_cursor
            now = Utils.GetBaseTimestamp()

            # 1) Looting or loot-grace → keep paused; evaluate skip-ahead
            if cd.in_looting_routine or (pause_until and now < pause_until):
                maybe_request_skip_ahead()
                return True

            # 2) While in aggro → let HeroAI fight; evaluate skip-ahead
            enemies = GLOBAL_CACHE.AgentArray.GetEnemyArray()
            if cd.InAggro(enemies, aggro_range=aggro_range):
                in_combat = True
                maybe_request_skip_ahead()
                return True

            # 3) Combat just ended → grace pause; evaluate skip-ahead
            if in_combat:
                in_combat = False
                pause_until = now + loot_grace_ms
                maybe_request_skip_ahead()
                return True

            # 4) No combat: scan/step toward closest pack inside seek radius
            if now - last_scan_tick >= 250:
                target_id = nearest_enemy_within(seek_radius)
                last_scan_tick = now

            if target_id:
                # === CHANGE: always autopath for the *move* toward the enemy ===
                ax, ay = GLOBAL_CACHE.Agent.GetXY(target_id)
                pending_chase["pos"] = (ax, ay)     # queue autopath chase
                restart_requested = True            # exit FollowPath so outer loop runs chase
                new_cursor = cursor                 # do not advance along the route
                maybe_request_skip_ahead()          # keep original skip behavior
                return True

            return False

        # --- outer loop: re-run FollowPath when we decide to skip ahead / chase ---
        while cursor < len(flat_xy):
            restart_requested = False
            new_cursor = cursor

            subpath = flat_xy[cursor:]
            cb = make_progress_cb(cursor, len(subpath))

            # walk until done or until exit_condition triggers
            yield from Routines.Yield.Movement.FollowPath(
                path_points=subpath,
                progress_callback=cb,
                custom_pause_fn=pause_fn,
                custom_exit_condition=exit_condition
            )

            # --- handle a queued autopath chase (computed outside pause_fn) ---
            if pending_chase["pos"]:
                try:
                    px, py = GLOBAL_CACHE.Player.GetXY()
                    z  = GLOBAL_CACHE.Agent.GetZPlane(GLOBAL_CACHE.Player.GetAgentID())
                    tx, ty = pending_chase["pos"]
                    path3d = yield from ap.get_path(
                        (px, py, z), (tx, ty, z),
                        smooth_by_los=True,   # smooth path; decision to hunt unchanged
                        margin=100.0,
                        step_dist=500.0
                    )
                except Exception:
                    path3d = []

                pending_chase = {"pos": None}

                # DEBUG overlay: show the path while we chase
                debug_path3d = path3d or []
                if DEBUG_AUTOPATH and not overlay_started:
                    try:
                        GLOBAL_CACHE.Coroutines.append(_autopath_overlay())
                        overlay_started = True
                    except Exception:
                        pass

                # no path or > N points ⇒ likely “behind mountain”; skip hunt this time
                if not path3d or len(path3d) > CHASE_MAX_POINTS:
                    debug_path3d = []   # clear overlay
                    continue

                # Follow the short auto-path toward the target and then resume the route
                path2d = [(x, y) for (x, y, *_ ) in path3d]
                yield from Routines.Yield.Movement.FollowPath(
                    path2d,
                    progress_callback=None,
                    custom_pause_fn=_is_pathing_paused
                )

                debug_path3d = []       # clear overlay after we’ve walked it
                continue

            if restart_requested and new_cursor > cursor:
                # we advanced to new_cursor → run actions for the waypoints we just reached
                # (cursor+1 .. new_cursor inclusive)
                yield from run_actions(cursor + 1, new_cursor + 1)
                cursor = new_cursor
                continue

            # finished the subpath: execute any remaining actions on the tail
            yield from run_actions(cursor + 1, len(flat_xy))

            # --- VANQUISH probe for this segment ---
            try:
                if GLOBAL_CACHE.Map.IsVanquishable() and GLOBAL_CACHE.Party.IsHardMode():
                    killed = GLOBAL_CACHE.Map.GetFoesKilled()
                    remaining = GLOBAL_CACHE.Map.GetFoesToKill()
                    total = max(0, killed + remaining)
                    if total > 0:
                        self.vanquish_attempted_in_run = True
                        if remaining == 0:
                            self.vanquish_success_in_run = True
            except Exception:
                pass

            break