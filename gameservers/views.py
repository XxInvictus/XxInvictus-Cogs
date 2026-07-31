import discord

from .store import can_view_game


def wrap_spoiler(value: str, spoiler: bool) -> str:
    return f"||{value}||" if spoiler else value


def unwrap_spoiler(value: str):
    if value.startswith("||") and value.endswith("||") and len(value) >= 4:
        return value[2:-2], True
    return value, False


def build_game_embed(game_name: str, fields: dict) -> discord.Embed:
    embed = discord.Embed(title=game_name, color=discord.Color.blurple())
    if not fields:
        embed.description = "No details have been configured for this game yet."
        return embed
    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)
    return embed


def build_submission_embed(submission: dict) -> discord.Embed:
    embed = discord.Embed(title=submission["game_name"], color=discord.Color.blurple())
    embed.add_field(
        name="Type",
        value="New Game" if submission["type"] == "new_game" else "Edit Existing Game",
        inline=True,
    )
    embed.add_field(name="Status", value=submission["status"].capitalize(), inline=True)
    embed.add_field(name="Submitted by", value=f"<@{submission['submitter_id']}>", inline=True)
    if submission["fields"]:
        for name, value in submission["fields"].items():
            embed.add_field(name=name, value=value, inline=False)
    else:
        embed.description = "No fields proposed yet."
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


def _panel_option_label(guild, panel: dict) -> str:
    channel = guild.get_channel(panel["channel_id"])
    channel_label = f"#{channel.name}" if channel is not None else "deleted-channel"
    return f"{channel_label} ({panel['message_id']})"[:100]


class SelectPanelGamesView(discord.ui.View):
    def __init__(self, cog, guild, channel, game_names: list, *, message_id, current_selection=None):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.channel = channel
        self.message_id = message_id
        current_selection = current_selection or []
        select = discord.ui.Select(
            placeholder="Choose games...",
            min_values=1,
            max_values=min(len(game_names), 25),
            options=[
                discord.SelectOption(label=name, default=(name in current_selection))
                for name in game_names[:25]
            ],
        )
        select.callback = self._on_select
        self.add_item(select)
        self._select = select

    async def _on_select(self, interaction: discord.Interaction):
        chosen = list(self._select.values)
        if self.message_id is None:
            await self.cog.create_panel(self.guild, self.channel, chosen)
            await interaction.response.edit_message(
                content=f"Panel posted in {self.channel.mention}.", embed=None, view=None
            )
        else:
            await self.cog.store.set_panel_games(self.guild, self.message_id, chosen)
            await self.cog.refresh_panels(self.guild)
            await interaction.response.edit_message(
                content="Panel's game list updated.", embed=None, view=None
            )


class ChoosePanelGamesView(discord.ui.View):
    def __init__(self, cog, guild, channel, *, message_id, current_selection=None):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.channel = channel
        self.message_id = message_id
        self.current_selection = current_selection

    @discord.ui.button(label="All Games", style=discord.ButtonStyle.primary)
    async def all_games(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.message_id is None:
            await self.cog.create_panel(self.guild, self.channel, None)
            await interaction.response.edit_message(
                content=f"Panel posted in {self.channel.mention}.", embed=None, view=None
            )
        else:
            await self.cog.store.set_panel_games(self.guild, self.message_id, None)
            await self.cog.refresh_panels(self.guild)
            await interaction.response.edit_message(
                content="Panel's game list updated.", embed=None, view=None
            )

    @discord.ui.button(label="Choose Specific Games", style=discord.ButtonStyle.secondary)
    async def choose_specific(self, interaction: discord.Interaction, button: discord.ui.Button):
        games = await self.cog.store.list_games(self.guild)
        if not games:
            await interaction.response.edit_message(
                content="No games configured yet.", embed=None, view=None
            )
            return
        view = SelectPanelGamesView(
            self.cog, self.guild, self.channel, list(games.keys()),
            message_id=self.message_id, current_selection=self.current_selection,
        )
        await interaction.response.edit_message(
            content="Select the games this panel should show:", embed=None, view=view
        )


class AddPanelChannelSelectView(discord.ui.View):
    def __init__(self, cog, guild):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text])
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = await select.values[0].fetch()
        view = ChoosePanelGamesView(self.cog, self.guild, channel, message_id=None)
        await interaction.response.edit_message(
            content=f"Which games should the panel in {channel.mention} show?", embed=None, view=view
        )


class ChangePanelChannelView(discord.ui.View):
    def __init__(self, cog, guild, message_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.message_id = message_id

    @discord.ui.select(cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text])
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        new_channel = await select.values[0].fetch()
        panel = await self.cog.store.get_panel(self.guild, self.message_id)
        old_channel = self.guild.get_channel(panel["channel_id"]) if panel else None
        if old_channel is not None:
            try:
                old_message = await old_channel.fetch_message(self.message_id)
                await old_message.delete()
            except discord.NotFound:
                pass
        game_names = panel["game_names"] if panel else None
        games = await self.cog.store.list_games(self.guild)
        names_to_show = self.cog._panel_game_names(game_names, games)
        view = PanelView(self.cog, names_to_show)
        new_message = await new_channel.send(
            "**Game Server Details** — pick a game, then click Get Details.", view=view
        )
        try:
            await new_message.pin()
        except discord.HTTPException:
            pass
        await self.cog.store.remove_panel(self.guild, self.message_id)
        await self.cog.store.add_panel(self.guild, new_channel.id, new_message.id, game_names)
        self.cog.bot.add_view(view, message_id=new_message.id)
        await interaction.response.edit_message(
            content=f"Panel moved to {new_channel.mention}.", embed=None, view=None
        )


class ManageSinglePanelView(discord.ui.View):
    def __init__(self, cog, guild, message_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.message_id = message_id

    @discord.ui.button(label="Delete Panel", style=discord.ButtonStyle.danger)
    async def delete_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        panel = await self.cog.store.get_panel(self.guild, self.message_id)
        if panel is not None:
            channel = self.guild.get_channel(panel["channel_id"])
            if channel is not None:
                try:
                    message = await channel.fetch_message(self.message_id)
                    await message.delete()
                except discord.NotFound:
                    pass
        await self.cog.store.remove_panel(self.guild, self.message_id)
        await interaction.response.edit_message(content="Panel deleted.", embed=None, view=None)

    @discord.ui.button(label="Change Channel", style=discord.ButtonStyle.primary)
    async def change_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChangePanelChannelView(self.cog, self.guild, self.message_id)
        await interaction.response.edit_message(
            content="Select the new channel for this panel:", embed=None, view=view
        )

    @discord.ui.button(label="Edit Game List", style=discord.ButtonStyle.secondary)
    async def edit_game_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        panel = await self.cog.store.get_panel(self.guild, self.message_id)
        channel = self.guild.get_channel(panel["channel_id"]) if panel else None
        view = ChoosePanelGamesView(
            self.cog, self.guild, channel,
            message_id=self.message_id, current_selection=panel["game_names"] if panel else None,
        )
        await interaction.response.edit_message(
            content="Which games should this panel show?", embed=None, view=view
        )


class ManagePanelsView(discord.ui.View):
    def __init__(self, cog, guild, panels: list):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self._select = None
        if panels:
            select = discord.ui.Select(
                placeholder="Pick a panel to manage...",
                options=[
                    discord.SelectOption(label=_panel_option_label(guild, panel), value=str(panel["message_id"]))
                    for panel in panels
                ][:25],
            )
            select.callback = self._on_select
            self.add_item(select)
            self._select = select

    @discord.ui.button(label="Add Panel", style=discord.ButtonStyle.success)
    async def add_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AddPanelChannelSelectView(self.cog, self.guild)
        await interaction.response.edit_message(
            content="Select the channel to post a new panel in:", embed=None, view=view
        )

    async def _on_select(self, interaction: discord.Interaction):
        message_id = int(self._select.values[0])
        view = ManageSinglePanelView(self.cog, self.guild, message_id)
        await interaction.response.edit_message(content="Manage this panel:", embed=None, view=view)


class AddFieldModal(discord.ui.Modal, title="Add Field"):
    field_name = discord.ui.TextInput(label="Field name", max_length=100)
    field_value = discord.ui.TextInput(
        label="Field value", max_length=1000, style=discord.TextStyle.paragraph
    )

    def __init__(self, cog, guild, game_name: str, *, spoiler: bool = False):
        super().__init__(title="Add Field (Spoiler)" if spoiler else "Add Field")
        self.cog = cog
        self.guild = guild
        self.game_name = game_name
        self.spoiler = spoiler

    async def on_submit(self, interaction: discord.Interaction):
        value = wrap_spoiler(self.field_value.value, self.spoiler)
        await self.cog.store.set_field(self.guild, self.game_name, self.field_name.value, value)
        game = await self.cog.store.get_game(self.guild, self.game_name)
        await interaction.response.send_message(
            embed=build_game_embed(self.game_name, game["fields"]), ephemeral=True
        )


class EditFieldModal(discord.ui.Modal, title="Edit Field"):
    def __init__(self, cog, guild, game_name: str, field_name: str, current_value: str, *, spoiler: bool = False):
        super().__init__(title="Edit Field (Spoiler)" if spoiler else "Edit Field")
        self.cog = cog
        self.guild = guild
        self.game_name = game_name
        self.field_name = field_name
        self.spoiler = spoiler
        raw_value, _ = unwrap_spoiler(current_value)
        self.field_value = discord.ui.TextInput(
            label=f"Value for {field_name}"[:45],
            default=raw_value,
            max_length=1000,
            style=discord.TextStyle.paragraph,
        )
        self.add_item(self.field_value)

    async def on_submit(self, interaction: discord.Interaction):
        value = wrap_spoiler(self.field_value.value, self.spoiler)
        await self.cog.store.set_field(self.guild, self.game_name, self.field_name, value)
        game = await self.cog.store.get_game(self.guild, self.game_name)
        await interaction.response.send_message(
            embed=build_game_embed(self.game_name, game["fields"]), ephemeral=True
        )


class RenameGameModal(discord.ui.Modal, title="Rename Game"):
    new_name = discord.ui.TextInput(label="New name", max_length=100)

    def __init__(self, cog, guild, game_name: str):
        super().__init__()
        self.cog = cog
        self.guild = guild
        self.game_name = game_name

    async def on_submit(self, interaction: discord.Interaction):
        renamed = await self.cog.store.rename_game(self.guild, self.game_name, self.new_name.value)
        if not renamed:
            await interaction.response.send_message(
                f"Could not rename to **{self.new_name.value}** (name already in use, or game missing).",
                ephemeral=True,
            )
            return
        await self.cog.refresh_panels(self.guild)
        await interaction.response.send_message(f"Renamed to **{self.new_name.value}**.", ephemeral=True)


class SelectFieldView(discord.ui.View):
    def __init__(self, cog, guild, game_name: str, field_names: list, *, action: str, spoiler: bool = False):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.game_name = game_name
        self.action = action
        self.spoiler = spoiler
        select = discord.ui.Select(
            placeholder="Choose a field...",
            options=[discord.SelectOption(label=name) for name in field_names[:25]],
        )
        select.callback = self._on_select
        self.add_item(select)
        self._select = select

    async def _on_select(self, interaction: discord.Interaction):
        field_name = self._select.values[0]
        if self.action == "edit":
            game = await self.cog.store.get_game(self.guild, self.game_name)
            await interaction.response.send_modal(
                EditFieldModal(
                    self.cog, self.guild, self.game_name, field_name, game["fields"][field_name],
                    spoiler=self.spoiler,
                )
            )
        else:
            await self.cog.store.remove_field(self.guild, self.game_name, field_name)
            game = await self.cog.store.get_game(self.guild, self.game_name)
            await interaction.response.send_message(
                embed=build_game_embed(self.game_name, game["fields"]), ephemeral=True
            )


class ManageAccessRolesView(discord.ui.View):
    def __init__(self, cog, guild, game_name: str, current_role_ids: list):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.game_name = game_name
        select = discord.ui.RoleSelect(
            placeholder="Roles allowed to view details (none = everyone)",
            min_values=0,
            max_values=25,
            default_values=[discord.Object(id=role_id) for role_id in current_role_ids],
        )
        select.callback = self._on_select
        self.add_item(select)
        self._select = select

    async def _on_select(self, interaction: discord.Interaction):
        role_ids = [role.id for role in self._select.values]
        await self.cog.store.set_access_roles(self.guild, self.game_name, role_ids)
        await interaction.response.send_message("Access roles updated.", ephemeral=True)


class GameEditorView(discord.ui.View):
    def __init__(self, cog, guild, game_name: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.game_name = game_name
        self.spoiler_mode = False

    @discord.ui.button(label="Spoiler: Off", style=discord.ButtonStyle.secondary)
    async def toggle_spoiler(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.spoiler_mode = not self.spoiler_mode
        button.label = f"Spoiler: {'On' if self.spoiler_mode else 'Off'}"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.success)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            AddFieldModal(self.cog, self.guild, self.game_name, spoiler=self.spoiler_mode)
        )

    @discord.ui.button(label="Edit Field", style=discord.ButtonStyle.primary)
    async def edit_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.cog.store.get_game(self.guild, self.game_name)
        if not game or not game["fields"]:
            await interaction.response.send_message("This game has no fields to edit yet.", ephemeral=True)
            return
        view = SelectFieldView(
            self.cog, self.guild, self.game_name, list(game["fields"].keys()),
            action="edit", spoiler=self.spoiler_mode,
        )
        await interaction.response.send_message("Pick a field to edit:", view=view, ephemeral=True)

    @discord.ui.button(label="Remove Field", style=discord.ButtonStyle.danger)
    async def remove_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.cog.store.get_game(self.guild, self.game_name)
        if not game or not game["fields"]:
            await interaction.response.send_message("This game has no fields to remove.", ephemeral=True)
            return
        view = SelectFieldView(self.cog, self.guild, self.game_name, list(game["fields"].keys()), action="remove")
        await interaction.response.send_message("Pick a field to remove:", view=view, ephemeral=True)

    @discord.ui.button(label="Manage Access Roles", style=discord.ButtonStyle.secondary)
    async def manage_access_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.cog.store.get_game(self.guild, self.game_name)
        view = ManageAccessRolesView(self.cog, self.guild, self.game_name, game["access_roles"])
        await interaction.response.send_message(
            "Select the roles allowed to view this game's details (none = everyone):",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="Rename Game", style=discord.ButtonStyle.secondary)
    async def rename_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RenameGameModal(self.cog, self.guild, self.game_name))

    @discord.ui.button(label="Delete Game", style=discord.ButtonStyle.danger)
    async def delete_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        deleted = await self.cog.store.delete_game(self.guild, self.game_name)
        if deleted:
            await self.cog.refresh_panels(self.guild)
        await interaction.response.send_message(
            f"Deleted **{self.game_name}**." if deleted else "That game no longer exists.",
            ephemeral=True,
        )


class AddGameModal(discord.ui.Modal, title="Add Game"):
    name = discord.ui.TextInput(label="Game name", max_length=100)

    def __init__(self, cog, guild):
        super().__init__()
        self.cog = cog
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        added = await self.cog.store.add_game(self.guild, self.name.value)
        if not added:
            await interaction.response.send_message(
                f"A game named **{self.name.value}** already exists.", ephemeral=True
            )
            return
        await self.cog.refresh_panels(self.guild)
        game = await self.cog.store.get_game(self.guild, self.name.value)
        view = GameEditorView(self.cog, self.guild, self.name.value)
        await interaction.response.send_message(
            embed=build_game_embed(self.name.value, game["fields"]), view=view, ephemeral=True
        )


class SelectGameToManageView(discord.ui.View):
    def __init__(self, cog, guild, game_names: list):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        select = discord.ui.Select(
            placeholder="Choose a game...",
            options=[discord.SelectOption(label=name) for name in game_names[:25]],
        )
        select.callback = self._on_select
        self.add_item(select)
        self._select = select

    async def _on_select(self, interaction: discord.Interaction):
        game_name = self._select.values[0]
        game = await self.cog.store.get_game(self.guild, game_name)
        view = GameEditorView(self.cog, self.guild, game_name)
        await interaction.response.send_message(
            embed=build_game_embed(game_name, game["fields"]), view=view, ephemeral=True
        )


class ManageManagementRolesView(discord.ui.View):
    def __init__(self, cog, guild, current_role_ids: list):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        select = discord.ui.RoleSelect(
            placeholder="Roles allowed to manage GameServers (none = admins only)",
            min_values=0,
            max_values=25,
            default_values=[discord.Object(id=role_id) for role_id in current_role_ids],
        )
        select.callback = self._on_select
        self.add_item(select)
        self._select = select

    async def _on_select(self, interaction: discord.Interaction):
        role_ids = [role.id for role in self._select.values]
        await self.cog.store.set_management_roles(self.guild, role_ids)
        await interaction.response.send_message("Management roles updated.", ephemeral=True)


class AdminView(discord.ui.View):
    def __init__(self, cog, guild):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild

    @discord.ui.button(label="Add Game", style=discord.ButtonStyle.success)
    async def add_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddGameModal(self.cog, self.guild))

    @discord.ui.button(label="Manage Games", style=discord.ButtonStyle.primary)
    async def manage_games(self, interaction: discord.Interaction, button: discord.ui.Button):
        games = await self.cog.store.list_games(self.guild)
        if not games:
            await interaction.response.send_message(
                "No games configured yet. Use Add Game first.", ephemeral=True
            )
            return
        view = SelectGameToManageView(self.cog, self.guild, list(games.keys()))
        await interaction.response.send_message("Pick a game to manage:", view=view, ephemeral=True)

    @discord.ui.button(label="Manage Roles", style=discord.ButtonStyle.secondary)
    async def manage_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        current = await self.cog.store.get_management_roles(self.guild)
        view = ManageManagementRolesView(self.cog, self.guild, current)
        await interaction.response.send_message(
            "Select the roles (besides Discord admins) allowed to manage GameServers:",
            view=view,
            ephemeral=True,
        )

    @discord.ui.button(label="Manage Panels", style=discord.ButtonStyle.secondary)
    async def manage_panels(self, interaction: discord.Interaction, button: discord.ui.Button):
        panels = await self.cog.store.list_panels(self.guild)
        view = ManagePanelsView(self.cog, self.guild, panels)
        await interaction.response.edit_message(content="Manage panels:", embed=None, view=view)

    @discord.ui.button(label="Review Submissions", style=discord.ButtonStyle.primary)
    async def review_submissions(self, interaction: discord.Interaction, button: discord.ui.Button):
        pending = await self.cog.store.list_pending_submissions(self.guild)
        if not pending:
            await interaction.response.send_message("No pending submissions.", ephemeral=True)
            return
        view = SelectSubmissionToReviewView(self.cog, self.guild, pending)
        await interaction.response.send_message("Pick a submission to review:", view=view, ephemeral=True)

    @discord.ui.button(label="Manage Submitter Roles", style=discord.ButtonStyle.secondary)
    async def manage_submitter_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        current = await self.cog.store.get_submitter_roles(self.guild)
        view = ManageSubmitterRolesView(self.cog, self.guild, current)
        await interaction.response.send_message(
            "Select the roles allowed to propose new games/edits:", view=view, ephemeral=True
        )


class AddSubmissionFieldModal(discord.ui.Modal, title="Add Field"):
    field_name = discord.ui.TextInput(label="Field name", max_length=100)
    field_value = discord.ui.TextInput(
        label="Field value", max_length=1000, style=discord.TextStyle.paragraph
    )

    def __init__(self, cog, guild, submission_id: str, *, spoiler: bool = False):
        super().__init__(title="Add Field (Spoiler)" if spoiler else "Add Field")
        self.cog = cog
        self.guild = guild
        self.submission_id = submission_id
        self.spoiler = spoiler

    async def on_submit(self, interaction: discord.Interaction):
        value = wrap_spoiler(self.field_value.value, self.spoiler)
        await self.cog.store.set_submission_field(self.guild, self.submission_id, self.field_name.value, value)
        submission = await self.cog.store.get_submission(self.guild, self.submission_id)
        await interaction.response.send_message(embed=build_submission_embed(submission), ephemeral=True)


class EditSubmissionFieldModal(discord.ui.Modal, title="Edit Field"):
    def __init__(self, cog, guild, submission_id: str, field_name: str, current_value: str, *, spoiler: bool = False):
        super().__init__(title="Edit Field (Spoiler)" if spoiler else "Edit Field")
        self.cog = cog
        self.guild = guild
        self.submission_id = submission_id
        self.field_name = field_name
        self.spoiler = spoiler
        raw_value, _ = unwrap_spoiler(current_value)
        self.field_value = discord.ui.TextInput(
            label=f"Value for {field_name}"[:45],
            default=raw_value,
            max_length=1000,
            style=discord.TextStyle.paragraph,
        )
        self.add_item(self.field_value)

    async def on_submit(self, interaction: discord.Interaction):
        value = wrap_spoiler(self.field_value.value, self.spoiler)
        await self.cog.store.set_submission_field(self.guild, self.submission_id, self.field_name, value)
        submission = await self.cog.store.get_submission(self.guild, self.submission_id)
        await interaction.response.send_message(embed=build_submission_embed(submission), ephemeral=True)


class SelectSubmissionFieldView(discord.ui.View):
    def __init__(self, cog, guild, submission_id: str, field_names: list, *, action: str, spoiler: bool = False):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.submission_id = submission_id
        self.action = action
        self.spoiler = spoiler
        select = discord.ui.Select(
            placeholder="Choose a field...",
            options=[discord.SelectOption(label=name) for name in field_names[:25]],
        )
        select.callback = self._on_select
        self.add_item(select)
        self._select = select

    async def _on_select(self, interaction: discord.Interaction):
        field_name = self._select.values[0]
        if self.action == "edit":
            submission = await self.cog.store.get_submission(self.guild, self.submission_id)
            await interaction.response.send_modal(
                EditSubmissionFieldModal(
                    self.cog, self.guild, self.submission_id, field_name, submission["fields"][field_name],
                    spoiler=self.spoiler,
                )
            )
        else:
            await self.cog.store.remove_submission_field(self.guild, self.submission_id, field_name)
            submission = await self.cog.store.get_submission(self.guild, self.submission_id)
            await interaction.response.send_message(
                embed=build_submission_embed(submission), ephemeral=True
            )


class SubmissionFieldEditorView(discord.ui.View):
    def __init__(self, cog, guild, submission_id: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.submission_id = submission_id
        self.spoiler_mode = False

    @discord.ui.button(label="Spoiler: Off", style=discord.ButtonStyle.secondary)
    async def toggle_spoiler(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.spoiler_mode = not self.spoiler_mode
        button.label = f"Spoiler: {'On' if self.spoiler_mode else 'Off'}"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.success)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            AddSubmissionFieldModal(self.cog, self.guild, self.submission_id, spoiler=self.spoiler_mode)
        )

    @discord.ui.button(label="Edit Field", style=discord.ButtonStyle.primary)
    async def edit_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        submission = await self.cog.store.get_submission(self.guild, self.submission_id)
        if not submission or not submission["fields"]:
            await interaction.response.send_message("This proposal has no fields to edit yet.", ephemeral=True)
            return
        view = SelectSubmissionFieldView(
            self.cog, self.guild, self.submission_id, list(submission["fields"].keys()),
            action="edit", spoiler=self.spoiler_mode,
        )
        await interaction.response.send_message("Pick a field to edit:", view=view, ephemeral=True)

    @discord.ui.button(label="Remove Field", style=discord.ButtonStyle.danger)
    async def remove_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        submission = await self.cog.store.get_submission(self.guild, self.submission_id)
        if not submission or not submission["fields"]:
            await interaction.response.send_message("This proposal has no fields to remove.", ephemeral=True)
            return
        view = SelectSubmissionFieldView(
            self.cog, self.guild, self.submission_id, list(submission["fields"].keys()), action="remove"
        )
        await interaction.response.send_message("Pick a field to remove:", view=view, ephemeral=True)


class ProposeNewGameModal(discord.ui.Modal, title="Propose New Game"):
    name = discord.ui.TextInput(label="Game name", max_length=100)

    def __init__(self, cog, guild):
        super().__init__()
        self.cog = cog
        self.guild = guild

    async def on_submit(self, interaction: discord.Interaction):
        submission_id = await self.cog.store.create_submission(
            self.guild, "new_game", interaction.user.id, self.name.value
        )
        submission = await self.cog.store.get_submission(self.guild, submission_id)
        view = SubmissionFieldEditorView(self.cog, self.guild, submission_id)
        await interaction.response.send_message(
            embed=build_submission_embed(submission), view=view, ephemeral=True
        )


class SelectGameForEditProposalView(discord.ui.View):
    def __init__(self, cog, guild, game_names: list):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        select = discord.ui.Select(
            placeholder="Choose a game...",
            options=[discord.SelectOption(label=name) for name in game_names[:25]],
        )
        select.callback = self._on_select
        self.add_item(select)
        self._select = select

    async def _on_select(self, interaction: discord.Interaction):
        game_name = self._select.values[0]
        submission_id = await self.cog.store.create_submission(
            self.guild, "edit_game", interaction.user.id, game_name
        )
        submission = await self.cog.store.get_submission(self.guild, submission_id)
        view = SubmissionFieldEditorView(self.cog, self.guild, submission_id)
        await interaction.response.send_message(
            embed=build_submission_embed(submission), view=view, ephemeral=True
        )


class ProposeView(discord.ui.View):
    def __init__(self, cog, guild):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild

    @discord.ui.button(label="Propose New Game", style=discord.ButtonStyle.success)
    async def propose_new_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ProposeNewGameModal(self.cog, self.guild))

    @discord.ui.button(label="Propose Edit to Existing Game", style=discord.ButtonStyle.primary)
    async def propose_edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        games = await self.cog.store.list_games(self.guild)
        if not games:
            await interaction.response.send_message(
                "No games exist yet to propose edits to.", ephemeral=True
            )
            return
        view = SelectGameForEditProposalView(self.cog, self.guild, list(games.keys()))
        await interaction.response.send_message(
            "Pick a game to propose an edit for:", view=view, ephemeral=True
        )


class SubmissionActionsView(discord.ui.View):
    def __init__(self, cog, guild, submission_id: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.submission_id = submission_id

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.primary)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        submission = await self.cog.store.get_submission(self.guild, self.submission_id)
        view = SubmissionFieldEditorView(self.cog, self.guild, self.submission_id)
        await interaction.response.send_message(
            embed=build_submission_embed(submission), view=view, ephemeral=True
        )

    @discord.ui.button(label="Withdraw", style=discord.ButtonStyle.danger)
    async def withdraw(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.cog.store.delete_submission(self.guild, self.submission_id)
        await interaction.response.send_message("Submission withdrawn.", ephemeral=True)


class MySubmissionsView(discord.ui.View):
    def __init__(self, cog, guild, submissions: dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        options = [
            discord.SelectOption(label=f"{data['game_name']} ({data['status']})"[:100], value=sid)
            for sid, data in submissions.items()
        ][:25]
        select = discord.ui.Select(placeholder="Choose a submission...", options=options)
        select.callback = self._on_select
        self.add_item(select)
        self._select = select

    async def _on_select(self, interaction: discord.Interaction):
        submission_id = self._select.values[0]
        submission = await self.cog.store.get_submission(self.guild, submission_id)
        if submission["status"] == "pending":
            view = SubmissionActionsView(self.cog, self.guild, submission_id)
            await interaction.response.send_message(
                embed=build_submission_embed(submission), view=view, ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=build_submission_embed(submission), ephemeral=True
            )


class SubmissionReviewView(discord.ui.View):
    def __init__(self, cog, guild, submission_id: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.submission_id = submission_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = await self.cog.store.approve_submission(self.guild, self.submission_id)
        if result == "approved":
            submission = await self.cog.store.get_submission(self.guild, self.submission_id)
            if submission["type"] == "new_game":
                await self.cog.refresh_panels(self.guild)
            await interaction.response.send_message("Submission approved.", ephemeral=True)
        elif result == "auto_rejected_name_exists":
            await interaction.response.send_message(
                "Could not approve: a game with that name already exists. Submission auto-rejected.",
                ephemeral=True,
            )
        elif result == "auto_rejected_target_missing":
            await interaction.response.send_message(
                "Could not approve: the target game no longer exists. Submission auto-rejected.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message("This submission can no longer be reviewed.", ephemeral=True)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        rejected = await self.cog.store.reject_submission(self.guild, self.submission_id)
        await interaction.response.send_message(
            "Submission rejected." if rejected else "This submission can no longer be reviewed.",
            ephemeral=True,
        )


class SelectSubmissionToReviewView(discord.ui.View):
    def __init__(self, cog, guild, submissions: dict):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        options = [
            discord.SelectOption(
                label=f"{data['game_name']} ({'New' if data['type'] == 'new_game' else 'Edit'})"[:100],
                value=sid,
            )
            for sid, data in submissions.items()
        ][:25]
        select = discord.ui.Select(placeholder="Choose a submission to review...", options=options)
        select.callback = self._on_select
        self.add_item(select)
        self._select = select

    async def _on_select(self, interaction: discord.Interaction):
        submission_id = self._select.values[0]
        submission = await self.cog.store.get_submission(self.guild, submission_id)
        view = SubmissionReviewView(self.cog, self.guild, submission_id)
        await interaction.response.send_message(
            embed=build_submission_embed(submission), view=view, ephemeral=True
        )


class ManageSubmitterRolesView(discord.ui.View):
    def __init__(self, cog, guild, current_role_ids: list):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        select = discord.ui.RoleSelect(
            placeholder="Roles allowed to submit proposals",
            min_values=0,
            max_values=25,
            default_values=[discord.Object(id=role_id) for role_id in current_role_ids],
        )
        select.callback = self._on_select
        self.add_item(select)
        self._select = select

    async def _on_select(self, interaction: discord.Interaction):
        role_ids = [role.id for role in self._select.values]
        await self.cog.store.set_submitter_roles(self.guild, role_ids)
        await interaction.response.send_message("Submitter roles updated.", ephemeral=True)
