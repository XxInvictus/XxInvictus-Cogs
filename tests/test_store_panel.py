async def test_list_panels_defaults_empty(store, guild):
    assert await store.list_panels(guild) == []


async def test_add_panel_appends_entry(store, guild):
    await store.add_panel(guild, 111, 222, None)
    panels = await store.list_panels(guild)
    assert panels == [{"channel_id": 111, "message_id": 222, "game_names": None}]


async def test_add_panel_supports_specific_game_names(store, guild):
    await store.add_panel(guild, 111, 222, ["Minecraft", "Terraria"])
    panels = await store.list_panels(guild)
    assert panels[0]["game_names"] == ["Minecraft", "Terraria"]


async def test_get_panel_finds_by_message_id(store, guild):
    await store.add_panel(guild, 111, 222, None)
    await store.add_panel(guild, 333, 444, None)
    panel = await store.get_panel(guild, 444)
    assert panel == {"channel_id": 333, "message_id": 444, "game_names": None}


async def test_get_panel_returns_none_for_missing(store, guild):
    assert await store.get_panel(guild, 999) is None


async def test_remove_panel_removes_matching_entry(store, guild):
    await store.add_panel(guild, 111, 222, None)
    await store.add_panel(guild, 333, 444, None)
    assert await store.remove_panel(guild, 222) is True
    panels = await store.list_panels(guild)
    assert [p["message_id"] for p in panels] == [444]


async def test_remove_panel_returns_false_for_missing(store, guild):
    assert await store.remove_panel(guild, 999) is False


async def test_set_panel_games_updates_existing_panel(store, guild):
    await store.add_panel(guild, 111, 222, None)
    ok = await store.set_panel_games(guild, 222, ["Minecraft"])
    assert ok is True
    panel = await store.get_panel(guild, 222)
    assert panel["game_names"] == ["Minecraft"]


async def test_set_panel_games_returns_false_for_missing(store, guild):
    assert await store.set_panel_games(guild, 999, ["Minecraft"]) is False
