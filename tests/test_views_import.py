from gameservers import views


def test_panel_view_class_exists():
    assert hasattr(views, "PanelView")


def test_setup_panel_view_class_exists():
    assert hasattr(views, "SetupPanelView")
