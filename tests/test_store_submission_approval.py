async def test_approve_new_game_creates_game_with_fields(store, guild):
    submission_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    await store.set_submission_field(guild, submission_id, "IP", "mc.example.com")

    result = await store.approve_submission(guild, submission_id)

    assert result == "approved"
    game = await store.get_game(guild, "Minecraft")
    assert game == {"fields": {"IP": "mc.example.com"}, "access_roles": []}
    submission = await store.get_submission(guild, submission_id)
    assert submission["status"] == "approved"


async def test_approve_new_game_auto_rejects_on_name_collision(store, guild):
    await store.add_game(guild, "Minecraft")
    submission_id = await store.create_submission(guild, "new_game", 111, "Minecraft")

    result = await store.approve_submission(guild, submission_id)

    assert result == "auto_rejected_name_exists"
    submission = await store.get_submission(guild, submission_id)
    assert submission["status"] == "rejected"


async def test_approve_edit_game_patches_existing_fields(store, guild):
    await store.add_game(guild, "Minecraft")
    await store.set_field(guild, "Minecraft", "IP", "old.example.com")
    submission_id = await store.create_submission(guild, "edit_game", 111, "Minecraft")
    await store.set_submission_field(guild, submission_id, "Version", "1.20")

    result = await store.approve_submission(guild, submission_id)

    assert result == "approved"
    game = await store.get_game(guild, "Minecraft")
    assert game["fields"] == {"IP": "old.example.com", "Version": "1.20"}


async def test_approve_edit_game_auto_rejects_when_target_missing(store, guild):
    submission_id = await store.create_submission(guild, "edit_game", 111, "Minecraft")

    result = await store.approve_submission(guild, submission_id)

    assert result == "auto_rejected_target_missing"
    submission = await store.get_submission(guild, submission_id)
    assert submission["status"] == "rejected"


async def test_approve_submission_returns_not_found_for_missing_id(store, guild):
    assert await store.approve_submission(guild, "999") == "not_found"


async def test_approve_submission_returns_not_pending_for_decided_submission(store, guild):
    submission_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    await store.reject_submission(guild, submission_id)

    assert await store.approve_submission(guild, submission_id) == "not_pending"


async def test_reject_submission_marks_rejected(store, guild):
    submission_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    assert await store.reject_submission(guild, submission_id) is True
    submission = await store.get_submission(guild, submission_id)
    assert submission["status"] == "rejected"


async def test_reject_submission_returns_false_for_missing_id(store, guild):
    assert await store.reject_submission(guild, "999") is False


async def test_reject_submission_returns_false_for_already_decided(store, guild):
    submission_id = await store.create_submission(guild, "new_game", 111, "Minecraft")
    await store.reject_submission(guild, submission_id)
    assert await store.reject_submission(guild, submission_id) is False
