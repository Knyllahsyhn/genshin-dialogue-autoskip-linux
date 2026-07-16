import time

from genshin_autoskip import ui


def test_format_uptime_minutes_seconds():
    assert ui.format_uptime(0) == "00:00"
    assert ui.format_uptime(754) == "12:34"
    assert ui.format_uptime(59.9) == "00:59"


def test_format_uptime_with_hours():
    assert ui.format_uptime(3723) == "1:02:03"


def test_format_uptime_negative_clamps_to_zero():
    assert ui.format_uptime(-5) == "00:00"


def test_uistate_defaults():
    state = ui.UiState()
    assert state.status == "pause"
    assert state.presses == 0
    assert state.breaks == 0
    assert state.last_action is None
    assert state.window_size is None
    assert state.dry_run is False
    assert state.started_at <= time.monotonic()


def test_plain_reporter_prints_events(capsys):
    rep = ui.PlainReporter(dry_run=True)
    with rep:
        rep.status_changed("run")
        rep.dry_run_action("skip")
        rep.break_started(4.2)
        rep.window_lost()
        rep.window_missing()
        rep.pressed("skip")
        rep.window_found((1920, 1080))
    out = capsys.readouterr().out
    assert "DRY-RUN" in out
    assert ">>> Status: RUN" in out
    assert "Would now: skip dialogue" in out
    assert "Human-like break: 4.2s" in out
    assert "Window lost" in out
    assert "window not found" in out


def _raise_file_not_found(*args, **kwargs):
    raise FileNotFoundError("notify-send")


def test_notify_swallows_missing_binary(monkeypatch):
    monkeypatch.setattr(ui.subprocess, "run", _raise_file_not_found)
    ui.notify("test")  # must not raise


def test_terminal_echo_off_is_noop_without_tty(monkeypatch):
    monkeypatch.setattr(ui.sys.stdin, "isatty", lambda: False)
    with ui.terminal_echo_off():
        pass  # must not raise
