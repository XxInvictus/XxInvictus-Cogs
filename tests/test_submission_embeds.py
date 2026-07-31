from gameservers.views import build_submission_embed


def test_build_submission_embed_shows_type_status_and_submitter():
    submission = {
        "type": "new_game",
        "submitter_id": 111,
        "game_name": "Minecraft",
        "fields": {},
        "status": "pending",
    }
    embed = build_submission_embed(submission)
    assert embed.title == "Minecraft"
    field_names = [f.name for f in embed.fields]
    assert "Type" in field_names
    assert "Status" in field_names
    assert "Submitted by" in field_names
    assert "No fields proposed yet" in embed.description


def test_build_submission_embed_includes_proposed_fields():
    submission = {
        "type": "edit_game",
        "submitter_id": 111,
        "game_name": "Minecraft",
        "fields": {"IP": "mc.example.com"},
        "status": "pending",
    }
    embed = build_submission_embed(submission)
    field_names = [f.name for f in embed.fields]
    assert "IP" in field_names
