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


class AddFieldModal(discord.ui.Modal, title="Add Field"):
    field_name = discord.ui.TextInput(label="Field name", max_length=100)
    field_value = discord.ui.TextInput(
        label="Field value", max_length=1000, style=discord.TextStyle.paragraph
    )

    def __init__(self, cog, guild, game_name: str):
        super().__init__()
        self.cog = cog
        self.guild = guild
        self.game_name = game_name

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.store.set_field(self.guild, self.game_name, self.field_name.value, self.field_value.value)
        game = await self.cog.store.get_game(self.guild, self.game_name)
        await interaction.response.send_message(
            embed=build_game_embed(self.game_name, game["fields"]), ephemeral=True
        )


class EditFieldModal(discord.ui.Modal, title="Edit Field"):
    def __init__(self, cog, guild, game_name: str, field_name: str, current_value: str):
        super().__init__()
        self.cog = cog
        self.guild = guild
        self.game_name = game_name
        self.field_name = field_name
        self.field_value = discord.ui.TextInput(
            label=f"Value for {field_name}"[:45],
            default=current_value,
            max_length=1000,
            style=discord.TextStyle.paragraph,
        )
        self.add_item(self.field_value)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.store.set_field(self.guild, self.game_name, self.field_name, self.field_value.value)
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
        await self.cog.refresh_panel(self.guild)
        await interaction.response.send_message(f"Renamed to **{self.new_name.value}**.", ephemeral=True)


class SelectFieldView(discord.ui.View):
    def __init__(self, cog, guild, game_name: str, field_names: list, *, action: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.game_name = game_name
        self.action = action
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
                EditFieldModal(self.cog, self.guild, self.game_name, field_name, game["fields"][field_name])
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

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.success)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddFieldModal(self.cog, self.guild, self.game_name))

    @discord.ui.button(label="Edit Field", style=discord.ButtonStyle.primary)
    async def edit_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        game = await self.cog.store.get_game(self.guild, self.game_name)
        if not game or not game["fields"]:
            await interaction.response.send_message("This game has no fields to edit yet.", ephemeral=True)
            return
        view = SelectFieldView(self.cog, self.guild, self.game_name, list(game["fields"].keys()), action="edit")
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
            await self.cog.refresh_panel(self.guild)
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
        await self.cog.refresh_panel(self.guild)
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

    @discord.ui.button(label="Setup Panel", style=discord.ButtonStyle.secondary)
    async def setup_panel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = SetupPanelView(self.cog, self.guild)
        await interaction.response.send_message(
            "Select the channel to post the panel in:", view=view, ephemeral=True
        )


class AddSubmissionFieldModal(discord.ui.Modal, title="Add Field"):
    field_name = discord.ui.TextInput(label="Field name", max_length=100)
    field_value = discord.ui.TextInput(
        label="Field value", max_length=1000, style=discord.TextStyle.paragraph
    )

    def __init__(self, cog, guild, submission_id: str):
        super().__init__()
        self.cog = cog
        self.guild = guild
        self.submission_id = submission_id

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.store.set_submission_field(
            self.guild, self.submission_id, self.field_name.value, self.field_value.value
        )
        submission = await self.cog.store.get_submission(self.guild, self.submission_id)
        await interaction.response.send_message(embed=build_submission_embed(submission), ephemeral=True)


class EditSubmissionFieldModal(discord.ui.Modal, title="Edit Field"):
    def __init__(self, cog, guild, submission_id: str, field_name: str, current_value: str):
        super().__init__()
        self.cog = cog
        self.guild = guild
        self.submission_id = submission_id
        self.field_name = field_name
        self.field_value = discord.ui.TextInput(
            label=f"Value for {field_name}"[:45],
            default=current_value,
            max_length=1000,
            style=discord.TextStyle.paragraph,
        )
        self.add_item(self.field_value)

    async def on_submit(self, interaction: discord.Interaction):
        await self.cog.store.set_submission_field(
            self.guild, self.submission_id, self.field_name, self.field_value.value
        )
        submission = await self.cog.store.get_submission(self.guild, self.submission_id)
        await interaction.response.send_message(embed=build_submission_embed(submission), ephemeral=True)


class SelectSubmissionFieldView(discord.ui.View):
    def __init__(self, cog, guild, submission_id: str, field_names: list, *, action: str):
        super().__init__(timeout=300)
        self.cog = cog
        self.guild = guild
        self.submission_id = submission_id
        self.action = action
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
                    self.cog, self.guild, self.submission_id, field_name, submission["fields"][field_name]
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

    @discord.ui.button(label="Add Field", style=discord.ButtonStyle.success)
    async def add_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(
            AddSubmissionFieldModal(self.cog, self.guild, self.submission_id)
        )

    @discord.ui.button(label="Edit Field", style=discord.ButtonStyle.primary)
    async def edit_field(self, interaction: discord.Interaction, button: discord.ui.Button):
        submission = await self.cog.store.get_submission(self.guild, self.submission_id)
        if not submission or not submission["fields"]:
            await interaction.response.send_message("This proposal has no fields to edit yet.", ephemeral=True)
            return
        view = SelectSubmissionFieldView(
            self.cog, self.guild, self.submission_id, list(submission["fields"].keys()), action="edit"
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
