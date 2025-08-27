from Py4GWCoreLib import *
from PyQuishAi.FSMHelpers import PyQuishAiFSMHelpers
import time

class PyQuishAiFSM:
    def __init__(self):
        self.fsm = FSM("PyQuishAiFSM")
        self.helpers = PyQuishAiFSMHelpers()
        self.skill_coroutine = None
        self.map_chain = []  # list of RunInfo objects
        self.chain_stats = None  # ChainStatistics instance
        self.auto_donate_enabled = False
        self.auto_donate_threshold = 30000
        self.run_active = False
        self.last_error = None
        self.loop_enabled = True        # set False if you want one-shot runs
        self.loop_delay_ms = 2000       # wait before restarting the chain
        self.loop_reset_stats = False    # reset ChainStatistics each loop
        self.ui_state = ""        # <- shown in GUI
        self._ui_hooked = False   # guard so we only wrap once
        # --- Safety monitors (death / stuck) ---
        self.dead_restart_secs = 120      # 2 minutes
        self.stuck_restart_secs = 240     # 4 minutes
        self._safety_active = False
        self._death_coro = None
        self._stuck_coro = None
        self._monitor_coros  = set()   # track which coroutines we added to GLOBAL_CACHE.Coroutines

    def ui_add_state(self, name, fn):
        """Wrap a normal state so we can show its name in the GUI."""
        def wrapped(*a, **k):
            self.ui_state = str(name)
            return fn(*a, **k)
        self.fsm.AddState(name, wrapped)

    def ui_add_yield(self, name, gen_fn):
        """Wrap a yield routine step so we can show its name in the GUI."""
        def wrapped(*a, **k):
            self.ui_state = str(name)
            gen = gen_fn(*a, **k)
            if gen is not None:
                yield from gen
        self.fsm.AddYieldRoutineStep(name, wrapped)

    def get_ui_state(self) -> str:
        """Return the last state label we entered (for the GUI)."""
        return getattr(self, "ui_state", "") or ""

    def set_map_chain(self, map_list):
        """
        Define the chain of map scripts to run sequentially.
        Example: ["_1_Eotn_To_Gunnars", "_2_Gunnars_To_Longeyes"]
        """
        self.map_chain = map_list
        if not self.map_chain:
            ConsoleLog("PyQuishAiFSM", "No map chain selected!")

    def build_fsm(self):
        """
        Build FSM steps dynamically based on map chain.
        Each map adds travel, wait, pathing, skill-casting phases.
        """
    
        if not self.map_chain:
            ConsoleLog("PyQuishAiFSM", "Cannot build FSM — no map chain defined!")
            return

        for idx, run_info in enumerate(self.map_chain):
            self._add_map_steps(run_info, idx)

        self.fsm.AddYieldRoutineStep("CompleteRun", self._complete_or_loop)

    def _add_map_steps(self, run_info, idx):
        """
        FSM map steps
        """
        data = self.helpers.load_map_script(run_info.id)
        outpost_id = data["ids"]["outpost_id"]

        # Mark start
        self.ui_add_state(f"[{idx}] Bot Started", lambda ri=run_info: ri.mark_started())
        # 1) Return to any outpost, then optional donate
        self.ui_add_yield(f"[{idx}] Returning To Outpost", lambda: self.helpers.travel_to_outpost(outpost_id))
        # 2) Wait for outpost map load
        self.ui_add_yield(f"[{idx}] Waiting For Outpost To Load", lambda oid=outpost_id: self.helpers.wait_for_map_load(oid))
        # 3) Leave outpost
        self.ui_add_yield(f"[{idx}] Leaving Outpost", lambda op=data["outpost_path"]: self.helpers.follow_path(op))
        # 5) Explorable segments
        segments = data.get("segments", [])
        for seg_i, seg in enumerate(segments):
            mid  = seg["map_id"]
            path = seg["path"]
            self.ui_add_yield(f"[{idx}.{seg_i}] Waiting For Map Loading MapID:{mid}", lambda m=mid: self.helpers.wait_for_map_load(m))
            self.ui_add_state(f"[{idx}] SafetyMonitors ON", self.start_safety_monitors)
            self.ui_add_yield(f"[{idx}.{seg_i}] Farming MapID:{mid}",    lambda p=path: self.helpers.follow_path_with_aggro(p))
            self.ui_add_yield(f"[{idx}.{seg_i}] ReverseSweepIfNeeded_{mid}", lambda p=path: self.helpers.reverse_sweep_if_not_vanquished(p))
        # 7) Mark finish
        self.ui_add_state(f"[{idx}] MarkFinished", lambda ri=run_info: ri.mark_finished())

        # Always return to an outpost at end of run
        self.ui_add_yield(f"[{idx}] Returning To Outpost", lambda: self.helpers.travel_to_outpost(outpost_id))
        self.ui_add_yield(f"[{idx}] Waiting For Any Outpost", self.helpers.wait_for_any_outpost)
        self.ui_add_state(f"[{idx}] SafetyMonitors OFF", self.stop_safety_monitors)
        #Donate if needed
        thr = int(getattr(self, "auto_donate_threshold", 30000))
        self.ui_add_yield("Donating Faction Points", lambda t=thr: self.helpers.auto_donate_faction(t))

        # 8) Stats rollup
        def _record_stats(ri=run_info, helpers=self.helpers, fsm=self):
            if fsm.chain_stats:
                ri.vanquish_attempted = bool(getattr(helpers, "vanquish_attempted_in_run", False))
                ri.vanquish_success   = bool(getattr(helpers, "vanquish_success_in_run", False))
                fsm.chain_stats.record_run_result(ri,failed=False,vanquish_attempted=ri.vanquish_attempted,vanquish_success=ri.vanquish_success)
        self.ui_add_state(f"[{idx}] MarkStats", _record_stats)

    def start(self):
        """
        Start the FSM execution.
        """

        #self.helpers.cache_and_disable_all_widgets()
        #self.helpers.enable_custom_widget_list()

        from PyQuishAi.StatsManager import ChainStatistics
        if self.chain_stats is None:
            self.chain_stats = ChainStatistics(list(self.map_chain))
            try:
                self.chain_stats.start_chain()
            except Exception:
                pass
        else:
            # keep totals; append fresh runs for this session
            try:
                self.chain_stats.runs.extend(list(self.map_chain))
            except Exception:
                pass

        ConsoleLog("PyQuishAiFSM", f"Starting PyQuishAi with {len(self.map_chain)} runs.")
        self.build_fsm()
        self.fsm.start()
        # Start Overwatch monitoring as a background coroutine
        self.run_active = True

    def reset(self):
        """
        HARD RESET:
        - Stop all coroutines
        - Reset FSM completely
        """
        ConsoleLog("PyQuishAiFSM", "Hard resetting FSM + all coroutines...")

        try:
            GLOBAL_CACHE.Coroutines.clear()
        except ValueError:
            pass
        ActionQueueManager().ResetAllQueues()

        #self.helpers.restore_cached_widgets()

        self.fsm = FSM("PyQuishAiFSM")
        self.run_active = False
        # Reset chain statistics (clear any running stats tracking)
        # self.chain_stats = None

    def reset_statistics(self):
        """Manually reset/clear only the accumulated statistics."""
        from PyQuishAi.StatsManager import ChainStatistics
        self.chain_stats = ChainStatistics(self.map_chain or [])
        # Start a fresh “session” timestamp so averages show immediately
        self.chain_stats.start_chain()

    def soft_reset_for_retry(self):
        """
        SOFT RESET used by Overwatch (do NOT stop overwatch itself)
        - Stop skill casting
        - Clear action queues
        - Reset FSM completely
        """
        ConsoleLog("PyQuishAiFSM", "Soft resetting FSM")
        ActionQueueManager().ResetAllQueues()
        
        # Replace FSM with a new clean instance
        self.fsm = FSM("PyQuishAiFSM")
        # Mark inactive until restarted
        self.run_active = False
    
    def resume_partial_chain(self):
        ConsoleLog("PyQuishAiFSM", f"Retrying run but keeping previous stats intact")
        self.build_fsm()  # rebuild FSM states for the retry chain
        self.fsm.start()
        self.run_active = True

    def _finish_run(self):
        ConsoleLog("PyQuishAiFSM", "Run completed successfully.", Console.MessageType.Info)
        if self.chain_stats:
            self.chain_stats.finish_chain()

    def _complete_or_loop(self):
        """
        Final step: either finish and stop, or loop the same chain again.
        When looping, keep ChainStatistics unless loop_reset_stats is True.
        """
        ConsoleLog("PyQuishAiFSM", "Run completed successfully.", Console.MessageType.Info)

        # If looping is disabled -> old behavior (finalize and stop)
        if not getattr(self, "loop_enabled", False):
            if self.chain_stats:
                self.chain_stats.finish_chain()
            #self.helpers.restore_cached_widgets()
            return

        # --- Loop enabled ---
        # Optional: finalize the last pass if caller wants a per-loop boundary.
        if getattr(self, "loop_reset_stats", False) and self.chain_stats:
            self.chain_stats.finish_chain()

        # small pause before restarting
        yield from Routines.Yield.wait(int(getattr(self, "loop_delay_ms", 10000)))

        # Fresh RunInfo objects for the next pass
        next_runs = self._clone_current_chain_runs()

        if getattr(self, "loop_reset_stats", False):
            # Start with a brand-new accumulator
            from PyQuishAi.StatsManager import ChainStatistics
            self.chain_stats = ChainStatistics(next_runs)
            self.chain_stats.start_chain()
        else:
            # Keep the same accumulator; DON’T touch chain_start.
            # Just append the new run set so totals keep growing.
            if self.chain_stats:
                self.chain_stats.runs.extend(next_runs)

        # Swap map_chain to the new run objects and restart FSM
        self.map_chain = next_runs
        self.soft_reset_for_retry()   # clears FSM graph; keeps overwatch running
        self.resume_partial_chain()   # rebuilds states and restarts FSM

    def _clone_current_chain_runs(self):
        """Make a fresh RunInfo list (same ids/order/display) for the next loop."""
        from PyQuishAi.StatsManager import RunInfo
        new_runs = []
        for r in (self.map_chain or []):
            nr = RunInfo(r.order, r.id, r.origin, r.destination, r.region, r.run_name)
            try:
                nr.display = r.display
            except Exception:
                pass
            new_runs.append(nr)
        return new_runs

    def start_safety_monitors(self):
        if self._safety_active:
            ConsoleLog("Overwatch", "Safety monitors already active; ignoring start.", Console.MessageType.Debug)
            return

        self._safety_active = True

        # (re)create fresh generator objects every start
        self._death_coro = self._death_monitor_loop()
        self._stuck_coro = self._stuck_monitor_loop()

        pool = GLOBAL_CACHE.Coroutines
        added = []

        for name, co in (("death", self._death_coro), ("stuck", self._stuck_coro)):
            if not co:
                continue
            if co not in pool:
                pool.append(co)
                self._monitor_coros.add(co)
                added.append(f"{name}#{id(co)}")
            else:
                ConsoleLog("Overwatch", f"{name} monitor already in pool (id={id(co)}).", Console.MessageType.Warning)

        ConsoleLog(
            "Overwatch",
            f"Safety monitors started ({" ,".join(added) if added else 'none added'}). pool_size={len(pool)}",
            Console.MessageType.Warning
        )

    def stop_safety_monitors(self):
        if not self._safety_active and not self._monitor_coros:
            ConsoleLog("Overwatch", "Safety monitors already stopped; nothing to do.", Console.MessageType.Debug)
            return

        self._safety_active = False

        pool = GLOBAL_CACHE.Coroutines
        removed, missing = [], []


        for co in list(self._monitor_coros):
            if co in pool:
                try:
                    pool.remove(co)
                    removed.append(f"id={id(co)}")
                except Exception:
                    missing.append(f"id={id(co)} (race)")
            else:
                missing.append(f"id={id(co)}")

            try:
                co.close()
            except Exception:
                pass

            self._monitor_coros.discard(co)

        self._death_coro = None
        self._stuck_coro = None

        ConsoleLog("Overwatch",f"Safety monitors stopped. removed=[{', '.join(removed)}] missing=[{', '.join(missing)}] pool_size={len(pool)}",Console.MessageType.Warning)

    def _restart_like_gui(self):
        chain_copy = list(self.map_chain or [])
        ConsoleLog("Overwatch", "Overwatch: triggering full restart (Stop → Start).", Console.MessageType.Warning)
        self.reset()                     # clears coroutines, stats, states
        if chain_copy:
            self.set_map_chain(chain_copy)
            self.start()

    def _death_monitor_loop(self):
        def _gen():
            dead_since = None
            while self._safety_active:
                if not Routines.Checks.Map.MapValid():
                    dead_since = None
                    yield from Routines.Yield.wait(1000); continue

                aid = GLOBAL_CACHE.Player.GetAgentID()
                if GLOBAL_CACHE.Agent.IsDead(aid):
                    if dead_since is None:
                        dead_since = time.time()
                    elif (time.time() - dead_since) >= self.dead_restart_secs:
                        ConsoleLog("Overwatch",f"Overwatch: We are dead >{self.dead_restart_secs}s - resetting run.",Console.MessageType.Warning)
                        self._restart_like_gui()
                        return  # this coroutine will be cleared by reset()
                else:
                    dead_since = None

                yield from Routines.Yield.wait(1000)
        return _gen()

    def _stuck_monitor_loop(self):
        def _gen():
            prev_pos = GLOBAL_CACHE.Player.GetXY() or (0.0, 0.0)
            still_since = time.time()
            while self._safety_active:
                if not Routines.Checks.Map.MapValid():
                    prev_pos = GLOBAL_CACHE.Player.GetXY() or prev_pos
                    still_since = time.time()
                    yield from Routines.Yield.wait(1000); continue

                current_pos = GLOBAL_CACHE.Player.GetXY() or prev_pos
                if current_pos == prev_pos:
                    if (time.time() - still_since) >= self.stuck_restart_secs:
                        ConsoleLog("Overwatch",f"Overwatch: Player stuck >{self.stuck_restart_secs}s - resetting run.",Console.MessageType.Warning)
                        self._restart_like_gui()
                        return
                else:
                    prev_pos = current_pos
                    still_since = time.time()

                yield from Routines.Yield.wait(1000)
        return _gen()