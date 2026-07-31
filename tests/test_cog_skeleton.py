from unittest.mock import MagicMock

from gameservers.gameservers import GameServers
from gameservers.store import GameStore, SelectionCache


def test_cog_instantiates_with_injected_config(config):
    bot = MagicMock()
    cog = GameServers(bot, config=config)
    assert cog.bot is bot
    assert isinstance(cog.store, GameStore)
    assert isinstance(cog.selection_cache, SelectionCache)
