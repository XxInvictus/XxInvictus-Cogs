from unittest.mock import AsyncMock, MagicMock

import pytest

from gameservers.gameservers import GameServers


@pytest.fixture
def cog(config):
    return GameServers(MagicMock(), config=config)


async def test_propose_command_rejects_member_without_permission(cog, guild):
    ctx = MagicMock()
    ctx.guild = guild
    ctx.author.guild_permissions.administrator = False
    ctx.author.guild_permissions.manage_guild = False
    ctx.author.roles = []
    ctx.author.guild = guild
    ctx.send = AsyncMock()

    await cog.gameservers_propose.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert "permission" in ctx.send.call_args.args[0]


async def test_propose_command_opens_view_for_submitter(cog, guild):
    await cog.store.set_submitter_roles(guild, [777])
    ctx = MagicMock()
    ctx.guild = guild
    ctx.author.guild_permissions.administrator = False
    ctx.author.guild_permissions.manage_guild = False
    ctx.author.roles = [MagicMock(id=777)]
    ctx.author.guild = guild
    ctx.send = AsyncMock()

    await cog.gameservers_propose.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert ctx.send.call_args.kwargs["view"] is not None


async def test_submissions_command_reports_when_none_exist(cog, guild):
    ctx = MagicMock()
    ctx.guild = guild
    ctx.author.id = 111
    ctx.send = AsyncMock()

    await cog.gameservers_submissions.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert "haven't submitted" in ctx.send.call_args.args[0]


async def test_submissions_command_shows_view_when_submissions_exist(cog, guild):
    await cog.store.create_submission(guild, "new_game", 111, "Minecraft")
    ctx = MagicMock()
    ctx.guild = guild
    ctx.author.id = 111
    ctx.send = AsyncMock()

    await cog.gameservers_submissions.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert ctx.send.call_args.kwargs["view"] is not None
