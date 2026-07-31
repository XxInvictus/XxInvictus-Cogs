async def test_set_field_adds_new_field(store, guild):
    await store.add_game(guild, "Minecraft")
    ok = await store.set_field(guild, "Minecraft", "IP", "mc.example.com")
    assert ok is True
    game = await store.get_game(guild, "Minecraft")
    assert game["fields"] == {"IP": "mc.example.com"}


async def test_set_field_overwrites_existing_field(store, guild):
    await store.add_game(guild, "Minecraft")
    await store.set_field(guild, "Minecraft", "IP", "old.example.com")
    await store.set_field(guild, "Minecraft", "IP", "new.example.com")
    game = await store.get_game(guild, "Minecraft")
    assert game["fields"]["IP"] == "new.example.com"


async def test_set_field_returns_false_for_missing_game(store, guild):
    assert await store.set_field(guild, "Nonexistent", "IP", "x") is False


async def test_remove_field_removes_it(store, guild):
    await store.add_game(guild, "Minecraft")
    await store.set_field(guild, "Minecraft", "IP", "mc.example.com")
    ok = await store.remove_field(guild, "Minecraft", "IP")
    assert ok is True
    game = await store.get_game(guild, "Minecraft")
    assert game["fields"] == {}


async def test_remove_field_returns_false_for_missing_field(store, guild):
    await store.add_game(guild, "Minecraft")
    assert await store.remove_field(guild, "Minecraft", "Nonexistent") is False


async def test_remove_field_returns_false_for_missing_game(store, guild):
    assert await store.remove_field(guild, "Nonexistent", "IP") is False
