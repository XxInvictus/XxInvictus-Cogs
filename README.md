# GameServers

A RED (Red-DiscordBot) cog that manages a persistent, pinned per-server panel:
members pick a game from a dropdown and click **Get Details** to see that
game's server details as an ephemeral reply. Admins (or delegated roles)
configure games, custom detail fields, and per-game viewing access through
an interactive `[p]/gameservers admin` UI.

## Development

This repo's dev tooling is managed entirely with [uv](https://docs.astral.sh/uv/) — no `requirements.txt`.

```
uv python install 3.8
uv sync
uv run pytest
```

## Installing into a Red instance

Add this repo to Red's downloader and load the cog:

```
[p]repo add gameservers <path-or-url-to-this-repo>
[p]cog install gameservers gameservers
[p]load gameservers
```

Then run `[p]gameservers admin` in a server (requires Manage Server/Administrator, or a configured management role) to add games and set up the panel.
