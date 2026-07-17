from random import Random

from genshin_autoskip.main import AppState, main_loop

DIALOG_PX = {
    "playing_icon": (236, 229, 216),
    "dialogue_icon_lower": (0, 0, 0),
    "dialogue_icon_higher": (0, 0, 0),
    "loading_screen": (0, 0, 0),
}

LOADING_PX = {**DIALOG_PX, "loading_screen": (255, 255, 255)}

OPTIONS_PX = {
    "playing_icon": (0, 0, 0),
    "dialogue_icon_lower": (255, 255, 255),
    "dialogue_icon_higher": (0, 0, 0),
    "loading_screen": (0, 0, 0),
}


class FakeClock:
    """Fake time: sleep() jumps the clock forward instead of waiting."""

    def __init__(self):
        self.t = 0.0
        self.sleeps = 0

    def now(self):
        return self.t

    def sleep(self, seconds):
        self.t += seconds
        self.sleeps += 1


class FakeWindow:
    def __init__(self, px):
        self.px = px
        self.seen_checkpoints = []

    def read_checkpoints(self, checkpoints=None):
        self.seen_checkpoints.append(checkpoints)
        return self.px

    def size(self):
        return (1920, 1080)

    def close(self):
        pass


class FakeKeyboard:
    """Ends the loop after stop_after key presses."""

    def __init__(self, state, stop_after):
        self.state = state
        self.stop_after = stop_after
        self.presses = 0

    def press(self):
        self.presses += 1
        if self.presses >= self.stop_after:
            self.state.status = "exit"


class FakeReporter:
    def __init__(self):
        self.events = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return None

    def status_changed(self, status):
        self.events.append(("status", status))

    def pressed(self, action):
        self.events.append(("pressed", action))

    def dry_run_action(self, action):
        self.events.append(("dry", action))

    def break_started(self, duration):
        self.events.append(("break", duration))

    def window_missing(self):
        self.events.append(("missing",))

    def window_found(self, size):
        self.events.append(("found", size))

    def window_lost(self):
        self.events.append(("lost",))


def _stop_after_sleeps(state, clock, limit):
    original = clock.sleep

    def sleep(seconds):
        original(seconds)
        if clock.sleeps >= limit:
            state.status = "exit"

    return sleep


def _run_loop(get_window, keyboard, state, *, dry_run=False, sleep=None, clock=None, cfg=None):
    clock = clock or FakeClock()
    reporter = FakeReporter()
    kwargs = {} if cfg is None else {"cfg": cfg}
    main_loop(
        get_window, keyboard, state, Random(42),
        reporter=reporter, dry_run=dry_run,
        sleep=sleep or clock.sleep, now=clock.now,
        **kwargs,
    )
    return reporter


def test_initial_state_is_pause():
    assert AppState().status == "pause"


def test_running_dialogue_triggers_key_presses_and_events():
    state = AppState()
    state.status = "run"
    keyboard = FakeKeyboard(state, stop_after=3)
    reporter = _run_loop(lambda: FakeWindow(DIALOG_PX), keyboard, state)
    assert keyboard.presses == 3
    assert reporter.events.count(("pressed", "skip")) == 3
    assert ("found", (1920, 1080)) in reporter.events


def test_loading_screen_never_presses():
    state = AppState()
    state.status = "run"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    reporter = _run_loop(
        lambda: FakeWindow(LOADING_PX), keyboard, state,
        clock=clock, sleep=_stop_after_sleeps(state, clock, 50),
    )
    assert keyboard.presses == 0
    assert not [e for e in reporter.events if e[0] in ("pressed", "dry")]


def test_pause_never_presses():
    state = AppState()  # stays "pause"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    _run_loop(
        lambda: FakeWindow(DIALOG_PX), keyboard, state,
        clock=clock, sleep=_stop_after_sleeps(state, clock, 20),
    )
    assert keyboard.presses == 0


def test_missing_window_reports_missing():
    state = AppState()
    state.status = "run"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    reporter = _run_loop(
        lambda: None, keyboard, state,
        clock=clock, sleep=_stop_after_sleeps(state, clock, 20),
    )
    assert keyboard.presses == 0
    assert ("missing",) in reporter.events


def test_dry_run_reports_but_never_presses():
    state = AppState()
    state.status = "run"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    reporter = _run_loop(
        lambda: FakeWindow(DIALOG_PX), keyboard, state,
        dry_run=True, clock=clock, sleep=_stop_after_sleeps(state, clock, 100),
    )
    assert keyboard.presses == 0
    assert ("dry", "skip") in reporter.events


def test_auto_confirm_disabled_never_presses():
    from genshin_autoskip.config import Config

    state = AppState()
    state.status = "run"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    _run_loop(
        lambda: FakeWindow(OPTIONS_PX), keyboard, state,
        clock=clock, sleep=_stop_after_sleeps(state, clock, 50),
        cfg=Config(auto_confirm=False),
    )
    assert keyboard.presses == 0


def test_custom_checkpoints_reach_window():
    from genshin_autoskip.config import Config

    state = AppState()
    state.status = "run"
    cfg = Config()
    window = FakeWindow(DIALOG_PX)
    keyboard = FakeKeyboard(state, stop_after=1)
    _run_loop(lambda: window, keyboard, state, cfg=cfg)
    assert window.seen_checkpoints[0] is cfg.checkpoints


def test_unreadable_window_reports_lost():
    state = AppState()
    state.status = "run"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    reporter = _run_loop(
        lambda: FakeWindow(None), keyboard, state,
        clock=clock, sleep=_stop_after_sleeps(state, clock, 20),
    )
    assert keyboard.presses == 0
    assert ("lost",) in reporter.events
