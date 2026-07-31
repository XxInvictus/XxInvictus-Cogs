import pytest

from redbot.core import Config
from redbot.core._drivers.json import JsonDriver

from gameservers.store import GUILD_DEFAULTS, GameStore

CONFIG_IDENTIFIER = "847291635"


class FakeGuild:
    def __init__(self, guild_id: int):
        self.id = guild_id


@pytest.fixture
def config(tmp_path):
    # Config.get_conf() needs Red's data_manager bootstrapped (a running
    # Red instance does this at startup); constructing Config directly with
    # a JsonDriver pointed at tmp_path sidesteps that for isolated tests.
    driver = JsonDriver("GameServers", CONFIG_IDENTIFIER, data_path_override=tmp_path)
    conf = Config(
        cog_name="GameServers",
        unique_identifier=CONFIG_IDENTIFIER,
        driver=driver,
        force_registration=True,
    )
    conf.register_guild(**GUILD_DEFAULTS)
    return conf


@pytest.fixture
def guild():
    return FakeGuild(111222333444)


@pytest.fixture
def store(config):
    return GameStore(config)
