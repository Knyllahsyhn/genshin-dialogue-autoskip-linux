from evdev import ecodes as e

from genshin_autoskip import hotkeys


def test_f8_key_down_is_run():
    assert hotkeys.action_for(e.EV_KEY, e.KEY_F8, 1) == "run"


def test_f9_and_f12():
    assert hotkeys.action_for(e.EV_KEY, e.KEY_F9, 1) == "pause"
    assert hotkeys.action_for(e.EV_KEY, e.KEY_F12, 1) == "exit"


def test_key_up_and_autorepeat_ignored():
    assert hotkeys.action_for(e.EV_KEY, e.KEY_F8, 0) is None
    assert hotkeys.action_for(e.EV_KEY, e.KEY_F8, 2) is None


def test_other_keys_and_event_types_ignored():
    assert hotkeys.action_for(e.EV_KEY, e.KEY_A, 1) is None
    assert hotkeys.action_for(e.EV_ABS, e.KEY_F8, 1) is None
