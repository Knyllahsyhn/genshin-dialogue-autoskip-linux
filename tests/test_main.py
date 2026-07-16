from random import Random

from genshin_autoskip.main import AppState, main_loop

DIALOG_PX = {
    "playing_icon": (236, 229, 216),
    "dialogue_icon_lower": (0, 0, 0),
    "dialogue_icon_higher": (0, 0, 0),
    "loading_screen": (0, 0, 0),
}

LOADING_PX = {**DIALOG_PX, "loading_screen": (255, 255, 255)}


class FakeClock:
    """Fake-Zeit: sleep() lässt die Uhr springen statt zu warten."""

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

    def read_checkpoints(self):
        return self.px

    def close(self):
        pass


class FakeKeyboard:
    """Beendet den Loop nach stop_after Tastendrücken."""

    def __init__(self, state, stop_after):
        self.state = state
        self.stop_after = stop_after
        self.presses = 0

    def press(self):
        self.presses += 1
        if self.presses >= self.stop_after:
            self.state.status = "exit"


def _stop_after_sleeps(state, clock, limit):
    original = clock.sleep

    def sleep(seconds):
        original(seconds)
        if clock.sleeps >= limit:
            state.status = "exit"

    return sleep


def test_startzustand_ist_pause():
    assert AppState().status == "pause"


def test_dialog_laeuft_loest_tastendruecke_aus():
    state = AppState()
    state.status = "run"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=3)
    main_loop(
        lambda: FakeWindow(DIALOG_PX), keyboard, state, Random(42),
        sleep=clock.sleep, now=clock.now,
    )
    assert keyboard.presses == 3


def test_loading_screen_drueckt_nie():
    state = AppState()
    state.status = "run"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    main_loop(
        lambda: FakeWindow(LOADING_PX), keyboard, state, Random(42),
        sleep=_stop_after_sleeps(state, clock, 50), now=clock.now,
    )
    assert keyboard.presses == 0


def test_pause_drueckt_nie():
    state = AppState()  # bleibt "pause"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    main_loop(
        lambda: FakeWindow(DIALOG_PX), keyboard, state, Random(42),
        sleep=_stop_after_sleeps(state, clock, 20), now=clock.now,
    )
    assert keyboard.presses == 0


def test_fehlendes_fenster_drueckt_nie():
    state = AppState()
    state.status = "run"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    main_loop(
        lambda: None, keyboard, state, Random(42),
        sleep=_stop_after_sleeps(state, clock, 20), now=clock.now,
    )
    assert keyboard.presses == 0


def test_dry_run_drueckt_nie():
    state = AppState()
    state.status = "run"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    main_loop(
        lambda: FakeWindow(DIALOG_PX), keyboard, state, Random(42),
        dry_run=True, sleep=_stop_after_sleeps(state, clock, 100), now=clock.now,
    )
    assert keyboard.presses == 0


def test_fenster_ohne_pixel_drueckt_nie():
    state = AppState()
    state.status = "run"
    clock = FakeClock()
    keyboard = FakeKeyboard(state, stop_after=1)
    main_loop(
        lambda: FakeWindow(None), keyboard, state, Random(42),
        sleep=_stop_after_sleeps(state, clock, 20), now=clock.now,
    )
    assert keyboard.presses == 0
