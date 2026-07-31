import discord

from .store import can_view_game


def build_game_embed(game_name: str, fields: dict) -> discord.Embed:
    embed = discord.Embed(title=game_name, color=discord.Color.blurple())
    if not fields:
        embed.description = "No details have been configured for this game yet."
        return embed
    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)
    return embed


class _GameSelect(discord.ui.Select):
    def __init__(self, cog, game_names: list):
        options = [discord.SelectOption(label=name) for name in game_names[:25]] or [
            discord.SelectOption(label="No games configured", value="__none__")
        ]
        super().__init__(
            placeholder="Choose a game...",
            custom_id="gameservers:panel:select",
            options=options,
            disabled=not game_names,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        self.cog.selection_cache.set_selection(interaction.message.id, interaction.user.id, self.values[0])
        await interaction.response.defer()


class _GetDetailsButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            label="Get Details",
            style=discord.ButtonStyle.primary,
            custom_id="gameservers:panel:get_details",
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        game_name = self.cog.selection_cache.get_selection(interaction.message.id, interaction.user.id)
        if game_name is None:
            await interaction.response.send_message("Pick a game from the dropdown first.", ephemeral=True)
            return
        game = await self.cog.store.get_game(interaction.guild, game_name)
        if game is None:
            await interaction.response.send_message(
                "That game is no longer configured. Please pick another.", ephemeral=True
            )
            return
        if not can_view_game(interaction.user, game):
            await interaction.response.send_message(
                "You don't have permission to view details for this game.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=build_game_embed(game_name, game["fields"]), ephemeral=True
        )


class PanelView(discord.ui.View):
    def __init__(self, cog, game_names: list):
        super().__init__(timeout=None)
        self.add_item(_GameSelect(cog, game_names))
        self.add_item(_GetDetailsButton(cog))


class SetupPanelView(discord.ui.View):
    def __init__(self, cog, guild):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text])
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = await select.values[0].fetch()

        old_channel_id, old_message_id = await self.cog.store.get_panel(self.guild)
        if old_channel_id is not None and old_message_id is not None:
            old_channel = self.guild.get_channel(old_channel_id)
            if old_channel is not None:
                try:
                    old_message = await old_channel.fetch_message(old_message_id)
                    await old_message.delete()
                except discord.NotFound:
                    pass

        games = await self.cog.store.list_games(self.guild)
        view = PanelView(self.cog, list(games.keys()))
        message = await channel.send(
            "**Game Server Details** — pick a game, then click Get Details.", view=view
        )
        try:
            await message.pin()
        except discord.HTTPException:
            pass
        await self.cog.store.set_panel(self.guild, channel.id, message.id)
        self.cog.bot.add_view(view, message_id=message.id)
        await interaction.response.send_message(f"Panel posted in {channel.mention}.", ephemeral=True)
