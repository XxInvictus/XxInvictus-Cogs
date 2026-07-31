from gameservers import views


def test_panel_view_class_exists():
    assert hasattr(views, "PanelView")


def test_setup_panel_view_class_exists():
    assert hasattr(views, "SetupPanelView")


def test_game_editor_view_class_exists():
    assert hasattr(views, "GameEditorView")


def test_admin_view_class_exists():
    assert hasattr(views, "AdminView")
