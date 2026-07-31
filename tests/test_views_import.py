from gameservers import views


def test_panel_view_class_exists():
    assert hasattr(views, "PanelView")


def test_setup_panel_view_class_exists():
    assert hasattr(views, "SetupPanelView")


def test_game_editor_view_class_exists():
    assert hasattr(views, "GameEditorView")


def test_admin_view_class_exists():
    assert hasattr(views, "AdminView")


def test_submission_field_editor_view_class_exists():
    assert hasattr(views, "SubmissionFieldEditorView")


def test_propose_view_class_exists():
    assert hasattr(views, "ProposeView")


def test_my_submissions_view_class_exists():
    assert hasattr(views, "MySubmissionsView")


def test_submission_review_view_class_exists():
    assert hasattr(views, "SubmissionReviewView")
