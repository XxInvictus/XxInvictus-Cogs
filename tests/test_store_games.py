async def test_add_game_succeeds_for_new_name(store, guild):
    added = await store.add_game(guild, "Minecraft")
    assert added is True
    games = await store.list_games(guild)
    assert games["Minecraft"] == {"fields": {}, "access_roles": []}


async def test_add_game_rejects_case_insensitive_duplicate(store, guild):
    await store.add_game(guild, "Minecraft")
    added = await store.add_game(guild, "minecraft")
    assert added is False
    games = await store.list_games(guild)
    assert len(games) == 1


async def test_get_game_is_case_insensitive(store, guild):
    await store.add_game(guild, "Minecraft")
    game = await store.get_game(guild, "MINECRAFT")
    assert game == {"fields": {}, "access_roles": []}


async def test_get_game_returns_none_for_missing_game(store, guild):
    assert await store.get_game(guild, "Nonexistent") is None


async def test_rename_game_moves_data_to_new_key(store, guild):
    await store.add_game(guild, "Minecraft")
    async with store.config.guild(guild).games() as games:
        games["Minecraft"]["fields"]["IP"] = "mc.example.com"
    renamed = await store.rename_game(guild, "Minecraft", "Minecraft Java")
    assert renamed is True
    games = await store.list_games(guild)
    assert "Minecraft" not in games
    assert games["Minecraft Java"]["fields"] == {"IP": "mc.example.com"}


async def test_rename_game_rejects_conflict_with_existing_name(store, guild):
    await store.add_game(guild, "Minecraft")
    await store.add_game(guild, "Terraria")
    assert await store.rename_game(guild, "Minecraft", "Terraria") is False


async def test_rename_game_returns_false_for_missing_game(store, guild):
    assert await store.rename_game(guild, "Nonexistent", "New Name") is False


async def test_delete_game_removes_it(store, guild):
    await store.add_game(guild, "Minecraft")
    assert await store.delete_game(guild, "minecraft") is True
    assert await store.list_games(guild) == {}


async def test_delete_game_returns_false_for_missing_game(store, guild):
    assert await store.delete_game(guild, "Nonexistent") is False
