import discord


def build_game_embed(game_name: str, fields: dict) -> discord.Embed:
    embed = discord.Embed(title=game_name, color=discord.Color.blurple())
    if not fields:
        embed.description = "No details have been configured for this game yet."
        return embed
    for name, value in fields.items():
        embed.add_field(name=name, value=value, inline=False)
    return embed
