from datetime import datetime
from collections import defaultdict
from Py4GWCoreLib import IconsFontAwesome5

class RunInfo:
    def __init__(self, order, id, origin, destination, region=None, run_name=None):
        self.order = order
        self.id = id  # e.g. "Eye_Of_The_North__1_Eotn_To_Gunnars"
        self.origin = origin
        self.destination = destination
        self.display = f"{origin} {IconsFontAwesome5.ICON_ARROWS_ALT_H} {destination}"
        self.region = region
        self.run_name = run_name

        # Progress flags
        self.started = False
        self.finished = False
        
        # Timing
        self.start_time = None
        self.end_time = None
        self.duration = 0
        
        # Fail tracking
        self.failures = 0
        self.deaths = 0
        self.stuck_timeouts = 0

        # Vanquish state observed during this run (optional)
        self.vanquish_attempted = False
        self.vanquish_success = False

    def mark_started(self):
        self.started = True
        self.start_time = datetime.now()

    def mark_finished(self, failed=False, deaths=0, stuck_timeouts=0):
        self.finished = True
        self.end_time = datetime.now()
        if self.start_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
        else:
            self.duration = 0
        self.deaths += deaths
        self.stuck_timeouts += stuck_timeouts
        if failed:
            self.failures += 1

    def get_duration(self):
        if self.end_time:
            return self.duration
        elif self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0


class ChainStatistics:
    """
    Aggregates stats across the active loop (chain).
    A new instance is created when the FSM starts or restarts a loop.
    """
    def __init__(self, chain_runs: list[RunInfo]):
        self.runs = chain_runs         # list[RunInfo]
        self.chain_start = None
        self.chain_end = None

        # Aggregates
        self.per_map = defaultdict(lambda: {
            "success": 0,
            "fails": 0,
            "vanquished": 0,
            "not_vanquished": 0,
            "total_time": 0.0,
            "runs": 0
        })
        self.donations = {"luxon": 0, "kurzick": 0}
        self.total_faction_donated = 0
        self.consumables = defaultdict(int)  # name -> count

    # ---------------- timing ----------------
    def start_chain(self):
        self.chain_start = datetime.now()
    
    def finish_chain(self):
        self.chain_end = datetime.now()
    
    def total_chain_time(self):
        if not self.chain_start:
            return 0
        if self.chain_end:
            return (self.chain_end - self.chain_start).total_seconds()
        return (datetime.now() - self.chain_start).total_seconds()

    # ---------------- recorders ----------------
    def record_run_result(self, run: RunInfo, *, failed: bool = False,
                          vanquish_attempted: bool | None = None,
                          vanquish_success: bool | None = None):
        """Call once when a RunInfo finishes (success or fail)."""
        key = run.id
        p = self.per_map[key]
        if failed:
            p["fails"] += 1
        else:
            p["success"] += 1
        # Vanquish book-keeping
        if vanquish_attempted:
            if vanquish_success:
                p["vanquished"] += 1
            else:
                p["not_vanquished"] += 1
        # Time aggregates
        if run.finished:
            p["total_time"] += float(run.duration or 0.0)
            p["runs"] += 1

    def record_fail(self, run: RunInfo):
        self.per_map[run.id]["fails"] += 1

    def record_donation(self, faction: str, amount: int):
        faction = (faction or "").lower()
        if faction in ("luxon", "kurzick"):
            self.donations[faction] += int(amount or 0)
            self.total_faction_donated += int(amount or 0)

    def record_consumable(self, name: str, count: int = 1):
        if name:
            self.consumables[name] += int(count or 0)

    # ---------------- rollups ----------------
    def runs_completed(self):
        return sum(1 for r in self.runs if r.finished)

    def runs_failed(self):
        return sum(r.failures for r in self.runs)

    def map_run_times(self):
        return [r.duration for r in self.runs if r.finished]

    def avg_run_time_seconds(self):
        times = self.map_run_times()
        return (sum(times) / len(times)) if times else 0.0

    def avg_faction_per_hour(self):
        secs = self.total_chain_time()
        if secs <= 0:
            return 0.0
        return self.total_faction_donated / (secs / 3600.0)
