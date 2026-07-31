from typing import Optional

import discord
from redbot.core import Config, commands

from .store import CONFIG_IDENTIFIER, GUILD_DEFAULTS, GameStore, SelectionCache
from .views import AdminView, PanelView


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

    async def cog_load(self) -> None:
        all_guilds = await self.config.all_guilds()
        for guild_id, data in all_guilds.items():
            if data.get("panel_message_id") is None:
                continue
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                continue
            view = PanelView(self, list(data["games"].keys()))
            self.bot.add_view(view, message_id=data["panel_message_id"])

    async def cog_unload(self) -> None:
        pass

    @commands.hybrid_command(name="admin")
    @commands.guild_only()
    async def admin(self, ctx: commands.Context) -> None:
        """Open the GameServers admin panel."""
        allowed = await self.store.can_manage(ctx.author)
        if not allowed:
            await ctx.send("You don't have permission to manage GameServers.", ephemeral=True)
            return
        view = AdminView(self, ctx.guild)
        await ctx.send("GameServers Admin", view=view, ephemeral=True)
