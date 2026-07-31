from typing import Optional

CONFIG_IDENTIFIER = 847291635

GUILD_DEFAULTS = {
    "games": {},
    "management_roles": [],
    "panel_channel_id": None,
    "panel_message_id": None,
}


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
