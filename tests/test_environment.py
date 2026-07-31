import sys

import redbot


def test_python_version_is_3_11():
    assert sys.version_info[:2] == (3, 11)


def test_redbot_is_installed():
    assert redbot.__version__
