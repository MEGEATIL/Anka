from anka.core.pending import dispatch_pending_response


class _Target:
    awaiting_note = True
    awaiting_music = False


def test_pending_response_runs_the_active_handler():
    target = _Target()
    received = []

    handled = dispatch_pending_response(
        target,
        (("awaiting_note", lambda command: received.append(command)),),
        "not metni",
        lambda state, error: None,
    )

    assert handled is True
    assert received == ["not metni"]


def test_pending_response_clears_state_and_reports_error():
    target = _Target()
    errors = []

    def failing_handler(command):
        raise RuntimeError("servis hatası")

    handled = dispatch_pending_response(
        target,
        (("awaiting_note", failing_handler),),
        "not metni",
        lambda state, error: errors.append((state, type(error).__name__)),
    )

    assert handled is True
    assert target.awaiting_note is False
    assert errors == [("awaiting_note", "RuntimeError")]


def test_pending_response_ignores_inactive_states():
    target = _Target()
    target.awaiting_note = False

    assert dispatch_pending_response(target, (("awaiting_note", lambda: None),), "x", lambda *_: None) is False
