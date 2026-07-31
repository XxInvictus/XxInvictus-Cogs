from gameservers.views import with_menu_notice


def test_with_menu_notice_quotes_the_notice_above_the_menu():
    result = with_menu_notice("Deleted **Minecraft**.", "GameServers Admin")
    assert result == "> Deleted **Minecraft**.\n\nGameServers Admin"
