async def test_create_submission_returns_pending_entry(store, guild):
    submission_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    submission = await store.get_submission(guild, submission_id)
    assert submission == {
        "type": "new_game",
        "submitter_id": 111,
        "game_name": "Minecraft",
        "fields": {},
        "status": "pending",
    }


async def test_create_submission_ids_increment(store, guild):
    first_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    second_id = await store.create_submission(guild, "new_game", 111, "Terraria")
    assert first_id != second_id


async def test_get_submission_returns_none_for_missing(store, guild):
    assert await store.get_submission(guild, "999") is None


async def test_set_submission_field_adds_field(store, guild):
    submission_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    ok = await store.set_submission_field(guild, submission_id, "IP", "mc.example.com")
    assert ok is True
    submission = await store.get_submission(guild, submission_id)
    assert submission["fields"] == {"IP": "mc.example.com"}


async def test_set_submission_field_returns_false_for_missing_submission(store, guild):
    assert await store.set_submission_field(guild, "999", "IP", "x") is False


async def test_remove_submission_field_removes_it(store, guild):
    submission_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    await store.set_submission_field(guild, submission_id, "IP", "mc.example.com")
    ok = await store.remove_submission_field(guild, submission_id, "IP")
    assert ok is True
    submission = await store.get_submission(guild, submission_id)
    assert submission["fields"] == {}


async def test_remove_submission_field_returns_false_for_missing_field(store, guild):
    submission_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    assert await store.remove_submission_field(guild, submission_id, "Nonexistent") is False


async def test_delete_submission_removes_it(store, guild):
    submission_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    assert await store.delete_submission(guild, submission_id) is True
    assert await store.get_submission(guild, submission_id) is None


async def test_delete_submission_returns_false_for_missing(store, guild):
    assert await store.delete_submission(guild, "999") is False


async def test_list_pending_submissions_excludes_decided(store, guild):
    pending_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    decided_id = await store.create_submission(guild, "new_game", 111, "Terraria")
    async with store.config.guild(guild).submissions() as submissions:
        submissions[decided_id]["status"] = "approved"
    pending = await store.list_pending_submissions(guild)
    assert list(pending.keys()) == [pending_id]


async def test_list_submissions_by_user_filters_by_submitter(store, guild):
    mine_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    await store.create_submission(guild, "new_game", 222, "Terraria")
    mine = await store.list_submissions_by_user(guild, 111)
    assert list(mine.keys()) == [mine_id]
