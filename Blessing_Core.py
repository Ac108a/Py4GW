import math, time
from Py4GWCoreLib import *
from enum import Enum, auto
from typing import Optional, Tuple, List, Dict
from Py4GWCoreLib import Agent, AgentArray, Player, Console
from Py4GW_widget_manager import get_widget_handler
from Py4GWCoreLib.Blessing_dialog_helper import is_npc_dialog_visible, click_dialog_button
from Verify_Blessing import has_any_blessing

_widget_handler = get_widget_handler()

class BlessingNpc(Enum):
    Sunspear_Scout          = (4778, 4776)
    Wandering_Priest        = (5384, 5383)
    Vabbian_Scout           = (5632,)
    Ghostly_Scout           = (5547,)
    Ghostly_Priest          = (5615)
    Whispers_Informants     = (5218, 5683)
    Kurzick_Priest          = (593, 912)
    Luxon_Priest            = (1947, 3641)
    Beacons_of_Droknar      = (5865,)
    Ascalonian_Refugees     = (1986, 1987, 6044, 6045)
    Asuran_Krewe            = (6755, 6756)
    Norn_Hunters            = (6374, 6380)

    def __init__(self, *mids: int):
        self.model_ids = mids

# Only non‐Norn NPCs need pre-defined click sequences
DIALOG_SEQUENCES: Dict[BlessingNpc, List[int]] = {
    BlessingNpc.Sunspear_Scout:     [1], #ok
    BlessingNpc.Wandering_Priest:   [1], #ok
    BlessingNpc.Ghostly_Scout:      [1],
    BlessingNpc.Kurzick_Priest:   [1, 2, 1, 1],
    BlessingNpc.Luxon_Priest:     [1, 2, 1, 1],
}

def get_blessing_npc() -> Tuple[Optional[BlessingNpc], Optional[int]]:
    me_x, me_y = Player.GetXY()
    best: Tuple[Optional[BlessingNpc], Optional[int]] = (None, None)
    best_dist = float('inf')
    for member in BlessingNpc:
        for agent in AgentArray.GetAgentArray():
            if Agent.GetModelID(agent) in member.model_ids:
                ax, ay = Agent.GetXY(agent)
                d = math.dist((me_x, me_y), (ax, ay))
                if d < best_dist:
                    best_dist, best = d, (member, agent)
    if best[1] is not None:
        Player.ChangeTarget(best[1])
    return best

class _Mover:
    def __init__(self):
        self.agent: Optional[int] = None
        self.dist = 0.0
        self.done = False

    def start(self, agent: int, dist: float):
        self.agent, self.dist, self.done = agent, dist, False

    def update(self) -> bool:
        if is_npc_dialog_visible():
            self.done = True
            self.agent = None
            return False
        if self.agent is None or self.done:
            return False
        mx, my = Player.GetXY()
        tx, ty = Agent.GetXY(self.agent)
        if math.dist((mx, my), (tx, ty)) <= self.dist:
            Player.Interact(self.agent)
            self.done = True
            self.agent = None
            return True
        Player.Move(tx, ty)
        return False

_mover = _Mover()

def move_interact_blessing_npc(agent: Optional[int], interact_distance: int = 100) -> bool:
    if agent is None:
        return False
    if _mover.agent != agent or _mover.done:
        _mover.start(agent, interact_distance)
    return _mover.update()

class _BlessingState(Enum):
    IDLE        = auto()
    APPROACH    = auto()
    DIALOG_WAIT = auto()
    DIALOG_NEXT = auto()
    VERIFY      = auto()
    DONE        = auto()

class BlessingRunner:
    def __init__(self, interact_distance: int = 100):
        self.interact_distance = interact_distance
        self.state = _BlessingState.IDLE
        self.member: Optional[BlessingNpc] = None
        self.agent:  Optional[int] = None
        self.dialog_seq: List[int] = []
        self.seq_idx = 0
        self.success = False
        self._norn_stage = 0
        self._wait_start = 0.0

    def start(self):
        ConsoleLog("BlessingRunner", "Starting blessing sequence", Console.MessageType.Info)
        _widget_handler.disable_widget("HeroAI")

        self.member, self.agent = get_blessing_npc()
        if self.member is None or self.agent is None:
            ConsoleLog("BlessingRunner", "No blessing NPC found", Console.MessageType.Warning)
            self.state, self.success = _BlessingState.DONE, False
            _widget_handler.enable_widget("HeroAI")
            return

        if self.member is BlessingNpc.Norn_Hunters:
            self.dialog_seq = [1]  # Norn handled in special flow
        else:
            self.dialog_seq = DIALOG_SEQUENCES.get(self.member, [1, 1])

        self.seq_idx = 0
        self._norn_stage = 0
        self.state = _BlessingState.APPROACH

    def update(self) -> Tuple[bool, bool]:
        if self.state == _BlessingState.IDLE:
            return False, False

        # Norn special flow
        if self.member is BlessingNpc.Norn_Hunters:
            if self._tick_norn():
                _widget_handler.enable_widget("HeroAI")
                return True, self.success
            return False, False

        # Approach & interact
        if self.state == _BlessingState.APPROACH:
            if move_interact_blessing_npc(self.agent, self.interact_distance):
                self.state = _BlessingState.DIALOG_WAIT
                self._wait_start = time.time()
            return False, False

        # Wait for dialog window
        if self.state == _BlessingState.DIALOG_WAIT:
            if is_npc_dialog_visible():
                self.state = _BlessingState.DIALOG_NEXT
            elif time.time() - self._wait_start > 10:
                self.state, self.success = _BlessingState.DONE, False
                _widget_handler.enable_widget("HeroAI")
                return True, self.success
            return False, False

        # Click through dialog options
        if self.state == _BlessingState.DIALOG_NEXT:
            if self.seq_idx < len(self.dialog_seq):
                click_dialog_button(self.dialog_seq[self.seq_idx])
                self.seq_idx += 1
                return False, False
            else:
                self.state = _BlessingState.VERIFY
                return False, False

        # Verify blessing effect
        if self.state == _BlessingState.VERIFY:
            self.success = has_any_blessing(Player.GetAgentID())
            _widget_handler.enable_widget("HeroAI")
            self.state = _BlessingState.DONE
            return True, self.success

        # DONE state
        if self.state == _BlessingState.DONE:
            _widget_handler.enable_widget("HeroAI")
            return True, self.success

        return False, False

    def _tick_norn(self) -> bool:
        # Stage 0: approach + interact (challenge)
        if self._norn_stage == 0:
            if move_interact_blessing_npc(self.agent, self.interact_distance):
                ConsoleLog("BlessingRunner", "Norn: interacted, waiting for dialog", Console.MessageType.Debug)
                self._wait_start = time.time()
                self._norn_stage = 1
            return False

        # Stage 1: wait for the “challenge” dialog to appear
        if self._norn_stage == 1:
            if is_npc_dialog_visible():
                ConsoleLog("BlessingRunner", "Norn: dialog visible, clicking accept", Console.MessageType.Debug)
                click_dialog_button(1)
                self._norn_stage = 2
            elif time.time() - self._wait_start > 8:
                ConsoleLog("BlessingRunner", "Norn: dialog never showed up, aborting", Console.MessageType.Warning)
                return True   # bail out
            return False

        # Stage 2: Check if blessing is resived or if norn guy turned hostile
        if self._norn_stage == 2:
            # If we already got the blessing (no fight needed), bail out
            if has_any_blessing(Player.GetAgentID()):
                ConsoleLog("BlessingRunner", "Norn: blessing already obtained, exiting", Console.MessageType.Debug)
                _widget_handler.enable_widget("HeroAI")
                self.success = True
                return True

            # Otherwise wait for the Norn to turn hostile
            if Agent.GetAllegiance(self.agent) == 3:  # Enemy
                ConsoleLog("BlessingRunner", "Stuck here", Console.MessageType.Debug)
                _widget_handler.enable_widget("HeroAI")
                self._norn_stage = 3
            return False

        # Stage 3: wait until friendly again
        if self._norn_stage == 3:
            if Agent.GetAllegiance(self.agent) != 3:
                ConsoleLog("BlessingRunner", "Norn: back to friendly", Console.MessageType.Debug)
                _widget_handler.disable_widget("HeroAI")
                self._norn_stage = 4
            return False

        # Stage 4: final interaction & blessing click
        if self._norn_stage == 4:
            if move_interact_blessing_npc(self.agent, self.interact_distance):
                ConsoleLog("BlessingRunner", "Norn: final dialog click", Console.MessageType.Debug)
                click_dialog_button(1)
                self.success = has_any_blessing(Player.GetAgentID())
                return True
            return False

        return False
