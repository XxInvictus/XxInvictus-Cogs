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

    async def refresh_panels(self, guild) -> None:
        panels = await self.store.list_panels(guild)
        games = await self.store.list_games(guild)
        for panel in panels:
            channel = guild.get_channel(panel["channel_id"])
            if channel is None:
                await self.store.remove_panel(guild, panel["message_id"])
                continue
            try:
                message = await channel.fetch_message(panel["message_id"])
            except discord.NotFound:
                await self.store.remove_panel(guild, panel["message_id"])
                continue
            names_to_show = self._panel_game_names(panel["game_names"], games)
            view = PanelView(self, names_to_show)
            await message.edit(view=view)
            self.bot.add_view(view, message_id=message.id)

    async def create_panel(self, guild, channel, game_names) -> None:
        games = await self.store.list_games(guild)
        names_to_show = self._panel_game_names(game_names, games)
        view = PanelView(self, names_to_show)
        message = await channel.send(
            "**Game Server Details** — pick a game, then click Get Details.", view=view
        )
        try:
            await message.pin()
        except discord.HTTPException:
            pass
        await self.store.add_panel(guild, channel.id, message.id, game_names)
        self.bot.add_view(view, message_id=message.id)

    @staticmethod
    def _panel_game_names(game_names, games: dict) -> list:
        if game_names is None:
            return list(games.keys())
        return [name for name in game_names if name in games]

    async def cog_load(self) -> None:
        all_guilds = await self.config.all_guilds()
        for guild_id, data in all_guilds.items():
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                continue
            games = data.get("games", {})
            for panel in data.get("panels", []):
                names_to_show = self._panel_game_names(panel["game_names"], games)
                view = PanelView(self, names_to_show)
                self.bot.add_view(view, message_id=panel["message_id"])

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
        view.message = await ctx.send("GameServers Admin", view=view, ephemeral=True)

    @gameservers.command(name="propose")
    async def gameservers_propose(self, ctx: commands.Context) -> None:
        """Propose a new game or an edit to an existing one."""
        allowed = await self.store.can_submit(ctx.author)
        if not allowed:
            await ctx.send("You don't have permission to propose games.", ephemeral=True)
            return
        view = ProposeView(self, ctx.guild)
        view.message = await ctx.send("Propose a Game", view=view, ephemeral=True)

    @gameservers.command(name="submissions")
    async def gameservers_submissions(self, ctx: commands.Context) -> None:
        """View the status of your own game proposals."""
        own = await self.store.list_submissions_by_user(ctx.guild, ctx.author.id)
        if not own:
            await ctx.send("You haven't submitted any proposals yet.", ephemeral=True)
            return
        view = MySubmissionsView(self, ctx.guild, own)
        view.message = await ctx.send("Your Submissions", view=view, ephemeral=True)
