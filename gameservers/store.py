from typing import Optional

CONFIG_IDENTIFIER = 847291635

GUILD_DEFAULTS = {
    "games": {},
    "management_roles": [],
    "panel_channel_id": None,
    "panel_message_id": None,
}


def can_view_game(member, game: dict) -> bool:
    access_roles = game.get("access_roles", [])
    if not access_roles:
        return True
    member_role_ids = {role.id for role in member.roles}
    return bool(member_role_ids.intersection(access_roles))


class GameStore:
    """Config-backed CRUD and permission checks for the GameServers cog.

    Deliberately has no discord.ui dependency so it can be unit tested
    without a live bot connection.
    """

    def __init__(self, config):
        self.config = config

    @staticmethod
    def _find_key(games: dict, name: str) -> Optional[str]:
        lowered = name.lower()
        for key in games:
            if key.lower() == lowered:
                return key
        return None

    async def list_games(self, guild) -> dict:
        return await self.config.guild(guild).games()

    async def get_game(self, guild, name: str) -> Optional[dict]:
        games = await self.config.guild(guild).games()
        key = self._find_key(games, name)
        return games[key] if key is not None else None

    async def add_game(self, guild, name: str) -> bool:
        async with self.config.guild(guild).games() as games:
            if self._find_key(games, name) is not None:
                return False
            games[name] = {"fields": {}, "access_roles": []}
        return True

    async def rename_game(self, guild, old_name: str, new_name: str) -> bool:
        async with self.config.guild(guild).games() as games:
            old_key = self._find_key(games, old_name)
            if old_key is None:
                return False
            if old_key.lower() != new_name.lower() and self._find_key(games, new_name) is not None:
                return False
            games[new_name] = games.pop(old_key)
        return True

    async def delete_game(self, guild, name: str) -> bool:
        async with self.config.guild(guild).games() as games:
            key = self._find_key(games, name)
            if key is None:
                return False
            del games[key]
        return True

    async def set_field(self, guild, game_name: str, field_name: str, field_value: str) -> bool:
        async with self.config.guild(guild).games() as games:
            key = self._find_key(games, game_name)
            if key is None:
                return False
            games[key]["fields"][field_name] = field_value
        return True

    async def remove_field(self, guild, game_name: str, field_name: str) -> bool:
        async with self.config.guild(guild).games() as games:
            key = self._find_key(games, game_name)
            if key is None or field_name not in games[key]["fields"]:
                return False
            del games[key]["fields"][field_name]
        return True

    async def get_management_roles(self, guild) -> list:
        return await self.config.guild(guild).management_roles()

    async def set_management_roles(self, guild, role_ids: list) -> None:
        await self.config.guild(guild).management_roles.set(list(role_ids))

    async def can_manage(self, member) -> bool:
        perms = member.guild_permissions
        if perms.administrator or perms.manage_guild:
            return True
        management_roles = await self.config.guild(member.guild).management_roles()
        member_role_ids = {role.id for role in member.roles}
        return bool(member_role_ids.intersection(management_roles))

    async def set_access_roles(self, guild, game_name: str, role_ids: list) -> bool:
        async with self.config.guild(guild).games() as games:
            key = self._find_key(games, game_name)
            if key is None:
                return False
            games[key]["access_roles"] = list(role_ids)
        return True

    async def get_panel(self, guild) -> tuple:
        channel_id = await self.config.guild(guild).panel_channel_id()
        message_id = await self.config.guild(guild).panel_message_id()
        return channel_id, message_id

    async def set_panel(self, guild, channel_id: int, message_id: int) -> None:
        await self.config.guild(guild).panel_channel_id.set(channel_id)
        await self.config.guild(guild).panel_message_id.set(message_id)

    async def clear_panel(self, guild) -> None:
        await self.config.guild(guild).panel_channel_id.set(None)
        await self.config.guild(guild).panel_message_id.set(None)
