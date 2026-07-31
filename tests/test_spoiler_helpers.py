from gameservers.views import unwrap_spoiler, wrap_spoiler


def test_wrap_spoiler_wraps_when_true():
    assert wrap_spoiler("secret", True) == "||secret||"


def test_wrap_spoiler_passes_through_when_false():
    assert wrap_spoiler("secret", False) == "secret"


def test_unwrap_spoiler_strips_wrapped_value():
    assert unwrap_spoiler("||secret||") == ("secret", True)


def test_unwrap_spoiler_passes_through_unwrapped_value():
    assert unwrap_spoiler("secret") == ("secret", False)


def test_unwrap_spoiler_handles_empty_spoiler():
    assert unwrap_spoiler("||||") == ("", True)


def test_unwrap_spoiler_does_not_treat_bare_pipes_as_spoiler():
    assert unwrap_spoiler("||") == ("||", False)
