from Py4GWCoreLib import *
from FollowPathAndAggro import FollowPathAndAggro
import luxon

class FactionFSMHelpers:
    def __init__(self):
        self.path_handler = None
        self.follow_handler = Routines.Movement.FollowXY()

    def check_faction_threshold(self, threshold, mode):
        # Check if faction >= threshold, then deposit
        if mode == "Luxon":
            unspent = luxon.get_luxon_unspent()
            if unspent >= threshold:
                return self.deposit_faction("Luxon")
        else:
            unspent = luxon.get_kurzick_unspent()
            if unspent >= threshold:
                return self.deposit_faction("Kurzick")
        return True  # Skip if below threshold

    def deposit_faction(self, mode):
        # Travel to Cavalon or House Zu Heltzer, interact, deposit all
        if mode == "Luxon":
            outpost_id = 389  # Cavalon
            deposit_fn = luxon.deposit_all_luxon
        else:
            outpost_id = 298  # House Zu Heltzer
            deposit_fn = luxon.deposit_all_kurzick

        # Travel
        Routines.Transition.TravelToOutpost(outpost_id)
        Routines.Yield.Map.WaitforMapLoad(outpost_id)
        # For simplicity assume NPC is nearby, directly deposit
        deposit_fn()
        return True

    def travel_to_outpost(self, outpost_id):
        Routines.Transition.TravelToOutpost(outpost_id)
        return Routines.Yield.Map.WaitforMapLoad(outpost_id)

    def follow_path(self, coords):
        return Routines.Yield.Movement.FollowPath(coords)

    def get_blessing(self):
        # TODO: better blessing logic (walk to NPC, interact, confirm blessing)
        Get_Blessed()
        return True

    def farm_combat_path(self, map_name):
        # Load map coordinates dynamically
        if map_name == "MountQinkai":
            from MountQinkai import MountQinkai as path_coords
        else:
            from MorostavTrail import MorostavTrail as path_coords

        # Follow path & aggro enemies
        for point in path_coords:
            Player.Move(*point)
            # Simulate combat scanning
            # Could integrate FollowPathAndAggro here
        return True

    def resign_and_return(self):
        # Resign, wait party defeat, return
        GLOBAL_CACHE.Party.Resign()
        Routines.Yield.wait(3000)
        GLOBAL_CACHE.Party.ReturnToOutpost()
        return True
