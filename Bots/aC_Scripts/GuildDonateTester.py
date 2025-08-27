# GuildDonateTester.py
# Minimal tester UI to broadcast DonateToGuild to the team.
# Precondition: your bot/app already handled travel to the correct outpost.

from Py4GWCoreLib import *
from Py4GWCoreLib import GLOBAL_CACHE, Routines, Console, ConsoleLog, SharedCommandType, PyImGui

# Outpost IDs (match the guard inside Messaging.DonateToGuild)
HZH_ID     = 77   # House zu Heltzer (Kurzick)
CAVALON_ID = 193  # Cavalon (Luxon)

def BroadcastDonateToGuild(donate_to_luxon: bool) -> bool:
    """
    If donate_to_luxon=True  -> must be in Cavalon (193)
    If donate_to_luxon=False -> must be in House zu Heltzer (77)
    Broadcasts SharedCommandType.DonateToGuild with the proper faction enum.
    Returns True if broadcast happened, False otherwise.
    """
    if not Routines.Checks.Map.MapValid():
        ConsoleLog("DonateTester", "Map invalid; not broadcasting DonateToGuild.", Console.MessageType.Warning)
        return False

    current_map_id = GLOBAL_CACHE.Map.GetMapID()
    expected = CAVALON_ID if donate_to_luxon else HZH_ID
    if current_map_id != expected:
        need = "Cavalon" if donate_to_luxon else "House zu Heltzer"
        ConsoleLog("DonateTester", f"Not in {need}; skipping DonateToGuild broadcast.", Console.MessageType.Warning)
        return False

    faction_enum = 1 if donate_to_luxon else 2  # (Luxon=1, Kurzick=2) expected by Messaging.DonateToGuild
    accounts = GLOBAL_CACHE.ShMem.GetAllAccountData()
    sender_email = GLOBAL_CACHE.Player.GetAccountEmail()

    for acc in accounts:
        msg = "Donating Luxon faction to Guild" if donate_to_luxon else "Donating Kurzick faction to Guild"
        ConsoleLog("DonateTester", f"{msg}: {acc.AccountEmail}", Console.MessageType.Info)
        GLOBAL_CACHE.ShMem.SendMessage(
            sender_email,
            acc.AccountEmail,
            SharedCommandType.DonateToGuild,
            (faction_enum, 0, 0, 0)
        )

    return True


def BroadcastDonateFromHere() -> bool:
    """
    Detect current outpost and broadcast the matching donation:
    - Cavalon  -> Luxon donation
    - HZH      -> Kurzick donation
    Returns True if broadcast happened, False otherwise.
    """
    if not Routines.Checks.Map.MapValid():
        ConsoleLog("DonateTester", "Map invalid; not broadcasting.", Console.MessageType.Warning)
        return False

    mid = GLOBAL_CACHE.Map.GetMapID()
    if mid == CAVALON_ID:
        return BroadcastDonateToGuild(True)
    if mid == HZH_ID:
        return BroadcastDonateToGuild(False)

    ConsoleLog("DonateTester", "Not in Cavalon or House zu Heltzer; cannot donate.", Console.MessageType.Warning)
    return False


def _map_status():
    """Helper for UI display."""
    if not Routines.Checks.Map.MapValid():
        return False, -1, "Invalid"
    mid = GLOBAL_CACHE.Map.GetMapID()
    name = "Cavalon" if mid == CAVALON_ID else ("House zu Heltzer" if mid == HZH_ID else f"Unknown ({mid})")
    return True, mid, name


def main():
    if PyImGui.begin("Guild Donate Tester", PyImGui.WindowFlags.AlwaysAutoResize):
        ok, mid, name = _map_status()

        PyImGui.text(f"Map valid: {'Yes' if ok else 'No'}")
        PyImGui.text(f"Current outpost: {name}")
        PyImGui.separator()

        # Buttons
        if PyImGui.button("Broadcast: Donate from CURRENT outpost"):
            BroadcastDonateFromHere()

        PyImGui.same_line(0, 10)
        if PyImGui.button("Broadcast: Donate Luxon (Cavalon)"):
            BroadcastDonateToGuild(True)

        PyImGui.same_line(0, 10)
        if PyImGui.button("Broadcast: Donate Kurzick (House zu Heltzer)"):
            BroadcastDonateToGuild(False)

        PyImGui.separator()
        PyImGui.text("Team accounts:")
        for acc in GLOBAL_CACHE.ShMem.GetAllAccountData():
            PyImGui.text(f"- {acc.AccountEmail}")

        PyImGui.end()


if __name__ == "__main__":
    main()