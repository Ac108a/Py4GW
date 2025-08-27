from FSM_helpers import FactionFSMHelpers
import Overwatch
from FollowPathAndAggro import FollowPathAndAggro
from StatsManager import RunInfo
import time

class FactionFarmFSM:
    def __init__(self):
        self.helpers = FactionFSMHelpers()
        #self.overwatch = Overwatch(self)
        self.current_mode = "Luxon"
        self.deposit_threshold = 5000
        self._fsm_steps = []
        self._current_idx = 0
        self._active = False
        self.current_state_name = "Idle"

    def configure(self, mode: str, threshold: int):
        self.current_mode = mode
        self.deposit_threshold = threshold

    def build_fsm(self):
        self._fsm_steps = []
        self._current_idx = 0

        # 1) Check threshold and deposit if needed
        self._fsm_steps.append(("CheckFactionThreshold", self.helpers.check_faction_threshold, self.deposit_threshold, self.current_mode))
        
        # 2) Travel to outpost for farming
        if self.current_mode == "Luxon":
            outpost_id = 389  # Cavalon
            map_outpost_path = [(-4268, 11628), (-5490, 13672)]
            explorable_path = "MountQinkai"
        else:
            outpost_id = 298  # House Zu Heltzer
            map_outpost_path = [(-9715,-3376),(-11645,-5155),(-12065,-7488)]
            explorable_path = "MorostavTrail"

        self._fsm_steps.append(("TravelToOutpost", self.helpers.travel_to_outpost, outpost_id))
        self._fsm_steps.append(("LeaveOutpost", self.helpers.follow_path, map_outpost_path))
        self._fsm_steps.append(("GetBlessing", self.helpers.get_blessing))
        self._fsm_steps.append(("FarmCombat", self.helpers.farm_combat_path, explorable_path))
        self._fsm_steps.append(("ResignReturn", self.helpers.resign_and_return))

    def start(self):
        self.build_fsm()
        #self.overwatch.start()
        self._active = True

    def stop(self):
        #self.overwatch.stop()
        self._active = False
        self._fsm_steps = []

    def update(self):
        if not self._active or self._current_idx >= len(self._fsm_steps):
            return

        state_name, fn, *args = self._fsm_steps[self._current_idx]
        self.current_state_name = state_name

        done = fn(*args)
        if done:
            self._current_idx += 1
            if self._current_idx >= len(self._fsm_steps):
                # Restart the FSM loop after finishing one run
                self.build_fsm()

    def get_current_state(self):
        return self.current_state_name
