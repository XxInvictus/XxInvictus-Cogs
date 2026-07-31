from typing import Optional

from redbot.core import Config, commands

from .store import CONFIG_IDENTIFIER, GUILD_DEFAULTS, GameStore, SelectionCache


class GameServers(commands.Cog):
    """Per-server game/server details panel with role-gated access."""

    def __init__(self, bot, config: Optional[Config] = None):
        self.bot = bot
        # `config` is injectable so tests can pass a JsonDriver-backed Config
        # pointed at a tmp dir instead of Config.get_conf(), which requires
        # Red's data_manager to have been bootstrapped by a running bot.
        self.config = config or Config.get_conf(
            self, identifier=CONFIG_IDENTIFIER, force_registration=True
        )
        self.config.register_guild(**GUILD_DEFAULTS)
        self.store = GameStore(self.config)
        self.selection_cache = SelectionCache()
