from unittest.mock import AsyncMock, MagicMock

import pytest

from gameservers.gameservers import GameServers


@pytest.fixture
def cog(config):
    return GameServers(MagicMock(), config=config)


async def test_admin_command_rejects_member_without_permission(cog, guild):
    ctx = MagicMock()
    ctx.guild = guild
    ctx.author.guild_permissions.administrator = False
    ctx.author.guild_permissions.manage_guild = False
    ctx.author.roles = []
    ctx.author.guild = guild
    ctx.send = AsyncMock()

    await cog.admin.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert "permission" in ctx.send.call_args.args[0]


async def test_admin_command_opens_view_for_admin(cog, guild):
    ctx = MagicMock()
    ctx.guild = guild
    ctx.author.guild_permissions.administrator = True
    ctx.author.roles = []
    ctx.author.guild = guild
    ctx.send = AsyncMock()

    await cog.admin.callback(cog, ctx)

    ctx.send.assert_awaited_once()
    assert ctx.send.call_args.kwargs["view"] is not None
