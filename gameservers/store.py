from typing import Optional

CONFIG_IDENTIFIER = 847291635

GUILD_DEFAULTS = {
    "games": {},
    "management_roles": [],
    "panels": [],
    "submitter_roles": [],
    "submissions": {},
    "next_submission_id": 1,
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

    async def list_panels(self, guild) -> list:
        return await self.config.guild(guild).panels()

    async def get_panel(self, guild, message_id: int) -> Optional[dict]:
        panels = await self.config.guild(guild).panels()
        for panel in panels:
            if panel["message_id"] == message_id:
                return panel
        return None

    async def add_panel(self, guild, channel_id: int, message_id: int, game_names) -> None:
        async with self.config.guild(guild).panels() as panels:
            panels.append({"channel_id": channel_id, "message_id": message_id, "game_names": game_names})

    async def remove_panel(self, guild, message_id: int) -> bool:
        async with self.config.guild(guild).panels() as panels:
            for index, panel in enumerate(panels):
                if panel["message_id"] == message_id:
                    del panels[index]
                    return True
        return False

    async def set_panel_games(self, guild, message_id: int, game_names) -> bool:
        async with self.config.guild(guild).panels() as panels:
            for panel in panels:
                if panel["message_id"] == message_id:
                    panel["game_names"] = game_names
                    return True
        return False

    async def create_submission(self, guild, submission_type: str, submitter_id: int, game_name: str) -> str:
        next_id = await self.config.guild(guild).next_submission_id()
        submission_id = str(next_id)
        async with self.config.guild(guild).submissions() as submissions:
            submissions[submission_id] = {
                "type": submission_type,
                "submitter_id": submitter_id,
                "game_name": game_name,
                "fields": {},
                "status": "pending",
            }
        await self.config.guild(guild).next_submission_id.set(next_id + 1)
        return submission_id

    async def get_submission(self, guild, submission_id: str) -> Optional[dict]:
        submissions = await self.config.guild(guild).submissions()
        return submissions.get(submission_id)

    async def set_submission_field(self, guild, submission_id: str, field_name: str, field_value: str) -> bool:
        async with self.config.guild(guild).submissions() as submissions:
            if submission_id not in submissions:
                return False
            submissions[submission_id]["fields"][field_name] = field_value
        return True

    async def remove_submission_field(self, guild, submission_id: str, field_name: str) -> bool:
        async with self.config.guild(guild).submissions() as submissions:
            if submission_id not in submissions or field_name not in submissions[submission_id]["fields"]:
                return False
            del submissions[submission_id]["fields"][field_name]
        return True

    async def delete_submission(self, guild, submission_id: str) -> bool:
        async with self.config.guild(guild).submissions() as submissions:
            if submission_id not in submissions:
                return False
            del submissions[submission_id]
        return True

    async def list_pending_submissions(self, guild) -> dict:
        submissions = await self.config.guild(guild).submissions()
        return {sid: s for sid, s in submissions.items() if s["status"] == "pending"}

    async def list_submissions_by_user(self, guild, user_id: int) -> dict:
        submissions = await self.config.guild(guild).submissions()
        return {sid: s for sid, s in submissions.items() if s["submitter_id"] == user_id}

    async def get_submitter_roles(self, guild) -> list:
        return await self.config.guild(guild).submitter_roles()

    async def set_submitter_roles(self, guild, role_ids: list) -> None:
        await self.config.guild(guild).submitter_roles.set(list(role_ids))

    async def can_submit(self, member) -> bool:
        if await self.can_manage(member):
            return True
        submitter_roles = await self.config.guild(member.guild).submitter_roles()
        member_role_ids = {role.id for role in member.roles}
        return bool(member_role_ids.intersection(submitter_roles))

    async def approve_submission(self, guild, submission_id: str) -> str:
        submissions = await self.config.guild(guild).submissions()
        submission = submissions.get(submission_id)
        if submission is None:
            return "not_found"
        if submission["status"] != "pending":
            return "not_pending"

        if submission["type"] == "new_game":
            added = await self.add_game(guild, submission["game_name"])
            if not added:
                await self._set_submission_status(guild, submission_id, "rejected")
                return "auto_rejected_name_exists"
        else:
            game = await self.get_game(guild, submission["game_name"])
            if game is None:
                await self._set_submission_status(guild, submission_id, "rejected")
                return "auto_rejected_target_missing"

        for field_name, field_value in submission["fields"].items():
            await self.set_field(guild, submission["game_name"], field_name, field_value)

        await self._set_submission_status(guild, submission_id, "approved")
        return "approved"

    async def reject_submission(self, guild, submission_id: str) -> bool:
        submissions = await self.config.guild(guild).submissions()
        submission = submissions.get(submission_id)
        if submission is None or submission["status"] != "pending":
            return False
        await self._set_submission_status(guild, submission_id, "rejected")
        return True

    async def _set_submission_status(self, guild, submission_id: str, status: str) -> None:
        async with self.config.guild(guild).submissions() as submissions:
            submissions[submission_id]["status"] = status


class SelectionCache:
    """In-memory tracker for a panel's currently-selected game, per user.

    Intentionally not persisted to Config: losing a selection on restart
    just means the member has to reselect, which costs nothing.
    """

    def __init__(self):
        self._selections = {}

    def set_selection(self, message_id: int, user_id: int, game_name: str) -> None:
        self._selections[(message_id, user_id)] = game_name

    def get_selection(self, message_id: int, user_id: int):
        return self._selections.get((message_id, user_id))
