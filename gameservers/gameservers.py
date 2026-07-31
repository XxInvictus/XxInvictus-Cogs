from typing import Optional

import discord
from redbot.core import Config, commands

from .store import CONFIG_IDENTIFIER, GUILD_DEFAULTS, GameStore, SelectionCache
from .views import AdminView, MySubmissionsView, PanelView, ProposeView


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

    @commands.hybrid_group(name="gameservers")
    @commands.guild_only()
    async def gameservers(self, ctx: commands.Context) -> None:
        """Manage and use the GameServers panel."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @gameservers.command(name="admin")
    async def gameservers_admin(self, ctx: commands.Context) -> None:
        """Open the GameServers admin panel."""
        allowed = await self.store.can_manage(ctx.author)
        if not allowed:
            await ctx.send("You don't have permission to manage GameServers.", ephemeral=True)
            return
        view = AdminView(self, ctx.guild)
        await ctx.send("GameServers Admin", view=view, ephemeral=True)

    @gameservers.command(name="propose")
    async def gameservers_propose(self, ctx: commands.Context) -> None:
        """Propose a new game or an edit to an existing one."""
        allowed = await self.store.can_submit(ctx.author)
        if not allowed:
            await ctx.send("You don't have permission to propose games.", ephemeral=True)
            return
        view = ProposeView(self, ctx.guild)
        await ctx.send("Propose a Game", view=view, ephemeral=True)

    @gameservers.command(name="submissions")
    async def gameservers_submissions(self, ctx: commands.Context) -> None:
        """View the status of your own game proposals."""
        own = await self.store.list_submissions_by_user(ctx.guild, ctx.author.id)
        if not own:
            await ctx.send("You haven't submitted any proposals yet.", ephemeral=True)
            return
        view = MySubmissionsView(self, ctx.guild, own)
        await ctx.send("Your Submissions", view=view, ephemeral=True)
