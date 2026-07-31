async def test_get_panel_defaults_to_none_none(store, guild):
    assert await store.get_panel(guild) == (None, None)


async def test_set_panel_then_get_panel_round_trips(store, guild):
    await store.set_panel(guild, 123, 456)
    assert await store.get_panel(guild) == (123, 456)


async def test_clear_panel_resets_to_none_none(store, guild):
    await store.set_panel(guild, 123, 456)
    await store.clear_panel(guild)
    assert await store.get_panel(guild) == (None, None)
