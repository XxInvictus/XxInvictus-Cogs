from typing import Optional

import discord
from redbot.core import Config, commands

from .store import CONFIG_IDENTIFIER, GUILD_DEFAULTS, GameStore, SelectionCache
from .views import PanelView


class GameServers(commands.Cog):
    """Per-server game/server details panel with role-gated access."""

    def __init__(self, bot, config: Optional[Config] = None):
        self.bot = bot
        # `config` is injectable so tests can pass a JsonDriver-backed Config
        # pointed at a tmp dir instead of Config.get_conf(), which requires
        # Red's data_manager to have been bootstrapped by a running bot.
        self.config = config or Config.get_conf(
            self, identifier=CONFIG_IDENTIFIER, force_registration=True
        )
        self.config.register_guild(**GUILD_DEFAULTS)
        self.store = GameStore(self.config)
        self.selection_cache = SelectionCache()

    async def refresh_panel(self, guild) -> None:
        channel_id, message_id = await self.store.get_panel(guild)
        if channel_id is None or message_id is None:
            return
        channel = guild.get_channel(channel_id)
        if channel is None:
            return
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            await self.store.clear_panel(guild)
            return
        games = await self.store.list_games(guild)
        view = PanelView(self, list(games.keys()))
        await message.edit(view=view)
        self.bot.add_view(view, message_id=message.id)
