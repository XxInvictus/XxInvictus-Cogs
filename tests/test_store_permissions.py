from gameservers.store import can_view_game


class FakePermissions:
    def __init__(self, *, administrator=False, manage_guild=False):
        self.administrator = administrator
        self.manage_guild = manage_guild


class FakeRole:
    def __init__(self, role_id):
        self.id = role_id


class FakeMember:
    def __init__(self, *, guild, roles=None, administrator=False, manage_guild=False):
        self.guild = guild
        self.roles = roles or []
        self.guild_permissions = FakePermissions(administrator=administrator, manage_guild=manage_guild)


async def test_can_manage_true_for_administrator(store, guild):
    member = FakeMember(guild=guild, administrator=True)
    assert await store.can_manage(member) is True


async def test_can_manage_true_for_manage_guild(store, guild):
    member = FakeMember(guild=guild, manage_guild=True)
    assert await store.can_manage(member) is True


async def test_can_manage_true_for_management_role(store, guild):
    await store.set_management_roles(guild, [555])
    member = FakeMember(guild=guild, roles=[FakeRole(555)])
    assert await store.can_manage(member) is True


async def test_can_manage_false_without_permission_or_role(store, guild):
    member = FakeMember(guild=guild, roles=[FakeRole(999)])
    assert await store.can_manage(member) is False


async def test_get_management_roles_defaults_empty(store, guild):
    assert await store.get_management_roles(guild) == []


async def test_set_access_roles_updates_game(store, guild):
    await store.add_game(guild, "Minecraft")
    ok = await store.set_access_roles(guild, "Minecraft", [111, 222])
    assert ok is True
    game = await store.get_game(guild, "Minecraft")
    assert game["access_roles"] == [111, 222]


async def test_set_access_roles_returns_false_for_missing_game(store, guild):
    assert await store.set_access_roles(guild, "Nonexistent", [111]) is False


def test_can_view_game_true_when_no_access_roles():
    member = FakeMember(guild=None, roles=[])
    game = {"fields": {}, "access_roles": []}
    assert can_view_game(member, game) is True


def test_can_view_game_true_when_member_has_matching_role():
    member = FakeMember(guild=None, roles=[FakeRole(111)])
    game = {"fields": {}, "access_roles": [111, 222]}
    assert can_view_game(member, game) is True


def test_can_view_game_false_when_member_lacks_role():
    member = FakeMember(guild=None, roles=[FakeRole(333)])
    game = {"fields": {}, "access_roles": [111, 222]}
    assert can_view_game(member, game) is False
