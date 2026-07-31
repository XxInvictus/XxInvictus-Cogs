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


async def test_get_submitter_roles_defaults_empty(store, guild):
    assert await store.get_submitter_roles(guild) == []


async def test_can_submit_true_for_submitter_role(store, guild):
    await store.set_submitter_roles(guild, [777])
    member = FakeMember(guild=guild, roles=[FakeRole(777)])
    assert await store.can_submit(member) is True


async def test_can_submit_true_for_manager_without_submitter_role(store, guild):
    member = FakeMember(guild=guild, administrator=True)
    assert await store.can_submit(member) is True


async def test_can_submit_false_without_role_or_management(store, guild):
    member = FakeMember(guild=guild, roles=[FakeRole(999)])
    assert await store.can_submit(member) is False
