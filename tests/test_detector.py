from genshin_autoskip import detector


def test_scale_point_identisch_bei_referenzaufloesung():
    assert detector.scale_point((84, 46), 1920, 1080) == (84, 46)


def test_scale_point_auf_1440p():
    # 84/1920*2560 = 112.0 ; 46/1080*1440 = 61.33 -> 61
    assert detector.scale_point((84, 46), 2560, 1440) == (112, 61)


def test_scaled_checkpoints_enthaelt_alle_pruefpunkte():
    points = detector.scaled_checkpoints(1920, 1080)
    assert points == {
        "playing_icon": (84, 46),
        "dialogue_icon_lower": (1301, 808),
        "dialogue_icon_higher": (1301, 790),
        "loading_screen": (1200, 700),
    }


def test_color_matches_exakt_und_mit_toleranz():
    assert detector.color_matches((236, 229, 216), (236, 229, 216))
    assert detector.color_matches((246, 219, 216), (236, 229, 216))  # ±10 ok
    assert not detector.color_matches((247, 229, 216), (236, 229, 216))  # 11 daneben
