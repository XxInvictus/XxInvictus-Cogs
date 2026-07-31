import uuid
import weakref

import pytest

from redbot.core import Config
from redbot.core import config as config_module
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
    #
    # Two layers of process-wide caching in redbot.core need defeating for
    # test isolation, or one test's data leaks into the next:
    #   1. Config is a singleton per (cog_name, unique_identifier), cached in
    #      a module-level weakref dict (ConfigMeta.__call__). Reset it so
    #      each test gets its own instance instead of an earlier test's.
    #   2. JsonDriver.data is backed by a module-level dict keyed *only* by
    #      cog_name (_shared_datastore in redbot.core._drivers.json) --
    #      data_path_override does not affect this key at all. Two drivers
    #      with the same cog_name share the exact same in-memory data
    #      regardless of which directory they were pointed at, until every
    #      driver instance for that name has been garbage-collected (GC
    #      timing, not something to rely on). Using a unique cog_name per
    #      test sidesteps this cache entirely instead of racing it.
    config_module._config_cache = weakref.WeakValueDictionary()
    cog_name = f"GameServers-{uuid.uuid4()}"
    driver = JsonDriver(cog_name, CONFIG_IDENTIFIER, data_path_override=tmp_path)
    conf = Config(
        cog_name=cog_name,
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
