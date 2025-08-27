from Py4GWCoreLib import *
from FSM import FactionFarmFSM
from StatsManager import ChainStatistics
from Titles import display_faction

# Configurable thresholds (increments of 5k)
THRESHOLD_OPTIONS = [5000 * i for i in range(1, 11)]  # 5k to 50k

class FactionsBotUI:
    def __init__(self):
        self.is_running = False
        self.faction_mode = "Luxon"  # Default: Luxon farming
        self.deposit_threshold = 5000
        self.fsm = FactionFarmFSM()
        self.chain_stats = None

    def draw_window(self):
        if not PyImGui.begin("Faction Farm Bot", PyImGui.WindowFlags.AlwaysAutoResize):
            PyImGui.end()
            return

        # --- Faction Mode ---
        PyImGui.text("Faction Mode:")
        modes = ["Luxon", "Kurzick"]
        selected_idx = 0 if self.faction_mode == "Luxon" else 1
        changed_idx = PyImGui.combo("##FactionMode", selected_idx, modes)
        self.faction_mode = modes[changed_idx]

        PyImGui.separator()

        # --- Deposit Threshold ---
        PyImGui.text("Deposit Threshold:")
        threshold_labels = [f"{val:,}" for val in THRESHOLD_OPTIONS]
        curr_idx = THRESHOLD_OPTIONS.index(self.deposit_threshold)
        new_idx = PyImGui.combo("##Threshold", curr_idx, threshold_labels)
        self.deposit_threshold = THRESHOLD_OPTIONS[new_idx]

        PyImGui.separator()

        # --- Start/Stop Button ---
        if not self.is_running:
            if PyImGui.button("Start Farming", width=200):
                self.start_bot()
        else:
            if PyImGui.button("Stop Farming", width=200):
                self.stop_bot()

        PyImGui.separator()

        # --- Current FSM State ---
        if self.is_running:
            PyImGui.text(f"Current FSM State: {self.fsm.get_current_state()}")

        # --- Stats ---
        if self.chain_stats:
            PyImGui.text(f"Runs Completed: {self.chain_stats.runs_completed()}")
            PyImGui.text(f"Runs Failed: {self.chain_stats.runs_failed()}")
            PyImGui.text(f"Total Time: {self.chain_stats.total_chain_time():.1f}s")

        PyImGui.end()

    def start_bot(self):
        self.is_running = True
        self.chain_stats = ChainStatistics([])
        self.chain_stats.start_chain()
        self.fsm.configure(mode=self.faction_mode, threshold=self.deposit_threshold)
        self.fsm.start()

    def stop_bot(self):
        self.is_running = False
        self.fsm.stop()
        if self.chain_stats:
            self.chain_stats.finish_chain()

    def tick(self):
        self.draw_window()
        if self.is_running:
            self.fsm.update()

# Entry point
bot_ui = FactionsBotUI()

def main():
    bot_ui.tick()
