from .gameservers import GameServers


async def setup(bot):
    await bot.add_cog(GameServers(bot))
