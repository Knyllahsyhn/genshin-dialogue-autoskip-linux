from genshin_autoskip import detector


def test_scale_point_identity_at_reference_resolution():
    assert detector.scale_point((84, 46), 1920, 1080) == (84, 46)


def test_scale_point_to_1440p():
    # 84/1920*2560 = 112.0 ; 46/1080*1440 = 61.33 -> 61
    assert detector.scale_point((84, 46), 2560, 1440) == (112, 61)


def test_scaled_checkpoints_contains_all_checkpoints():
    points = detector.scaled_checkpoints(1920, 1080)
    assert points == {
        "playing_icon": (84, 46),
        "dialogue_icon_lower": (1301, 808),
        "dialogue_icon_higher": (1301, 790),
        "loading_screen": (1200, 700),
    }


def test_color_matches_exact_and_with_tolerance():
    assert detector.color_matches((236, 229, 216), (236, 229, 216))
    assert detector.color_matches((246, 219, 216), (236, 229, 216))  # ±10 ok
    assert not detector.color_matches((247, 229, 216), (236, 229, 216))  # 11 off


def _px(playing=(0, 0, 0), lower=(0, 0, 0), higher=(0, 0, 0), loading=(0, 0, 0)):
    return {
        "playing_icon": playing,
        "dialogue_icon_lower": lower,
        "dialogue_icon_higher": higher,
        "loading_screen": loading,
    }


def test_decide_without_pixels_is_none():
    assert detector.decide(None) is None


def test_decide_nothing_detected_is_none():
    assert detector.decide(_px()) is None


def test_decide_running_dialogue_is_skip():
    assert detector.decide(_px(playing=(236, 229, 216))) == "skip"


def test_decide_visible_options_is_confirm():
    assert detector.decide(_px(lower=(255, 255, 255))) == "confirm"
    assert detector.decide(_px(higher=(255, 255, 255))) == "confirm"


def test_decide_options_beat_skip():
    px = _px(playing=(236, 229, 216), lower=(255, 255, 255))
    assert detector.decide(px) == "confirm"


def test_decide_loading_screen_blocks_everything():
    px = _px(playing=(236, 229, 216), lower=(255, 255, 255), loading=(255, 255, 255))
    assert detector.decide(px) is None
