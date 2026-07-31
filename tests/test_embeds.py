from gameservers.views import build_game_embed


def test_build_game_embed_includes_all_fields_in_order():
    embed = build_game_embed("Minecraft", {"IP": "mc.example.com", "Version": "1.20"})
    assert embed.title == "Minecraft"
    assert len(embed.fields) == 2
    assert embed.fields[0].name == "IP"
    assert embed.fields[0].value == "mc.example.com"
    assert embed.fields[1].name == "Version"


def test_build_game_embed_handles_no_fields():
    embed = build_game_embed("Minecraft", {})
    assert embed.fields == []
    assert "No details" in embed.description
