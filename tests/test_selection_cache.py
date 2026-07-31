from gameservers.store import SelectionCache


def test_get_selection_returns_none_when_unset():
    cache = SelectionCache()
    assert cache.get_selection(1, 2) is None


def test_set_then_get_selection_round_trips():
    cache = SelectionCache()
    cache.set_selection(1, 2, "Minecraft")
    assert cache.get_selection(1, 2) == "Minecraft"


def test_selections_are_isolated_per_message_and_user():
    cache = SelectionCache()
    cache.set_selection(1, 2, "Minecraft")
    cache.set_selection(1, 3, "Terraria")
    cache.set_selection(9, 2, "Valheim")
    assert cache.get_selection(1, 2) == "Minecraft"
    assert cache.get_selection(1, 3) == "Terraria"
    assert cache.get_selection(9, 2) == "Valheim"


def test_set_selection_overwrites_previous_value():
    cache = SelectionCache()
    cache.set_selection(1, 2, "Minecraft")
    cache.set_selection(1, 2, "Terraria")
    assert cache.get_selection(1, 2) == "Terraria"
