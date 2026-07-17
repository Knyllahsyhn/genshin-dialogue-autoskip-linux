import pytest

from genshin_autoskip import config


def write_env(tmp_path, text):
    path = tmp_path / ".env"
    path.write_text(text)
    return path


def test_missing_file_returns_defaults(tmp_path):
    cfg = config.load(tmp_path / ".env", environ={})
    assert cfg == config.Config()


def test_defaults_match_original_values():
    cfg = config.Config()
    assert cfg.notifications is True
    assert cfg.auto_confirm is True
    assert cfg.playing_icon_color == (236, 229, 216)
    assert cfg.color_tolerance == 10
    assert cfg.checkpoints == {
        "playing_icon": (84, 46),
        "dialogue_icon_lower": (1301, 808),
        "dialogue_icon_higher": (1301, 790),
        "loading_screen": (1200, 700),
    }


def test_parse_env_text_handles_comments_blanks_whitespace():
    values = config.parse_env_text("# comment\n\n  KEY = value  \nA=1\n")
    assert values == {"KEY": "value", "A": "1"}


def test_parse_env_text_rejects_line_without_equals():
    with pytest.raises(config.ConfigError):
        config.parse_env_text("NOT A PAIR\n")


def test_file_values_are_applied(tmp_path):
    path = write_env(
        tmp_path,
        "NOTIFICATIONS=false\n"
        "AUTO_CONFIRM=no\n"
        "PLAYING_ICON_COLOR=1,2,3\n"
        "COLOR_TOLERANCE=5\n"
        "CHECKPOINT_PLAYING_ICON=10,20\n",
    )
    cfg = config.load(path, environ={})
    assert cfg.notifications is False
    assert cfg.auto_confirm is False
    assert cfg.playing_icon_color == (1, 2, 3)
    assert cfg.color_tolerance == 5
    assert cfg.checkpoints["playing_icon"] == (10, 20)
    # untouched checkpoints keep their defaults
    assert cfg.checkpoints["loading_screen"] == (1200, 700)


def test_environment_overrides_file(tmp_path):
    path = write_env(tmp_path, "COLOR_TOLERANCE=5\n")
    cfg = config.load(path, environ={"COLOR_TOLERANCE": "20"})
    assert cfg.color_tolerance == 20


def test_boolean_forms():
    for raw in ("true", "TRUE", "1", "yes", "Yes"):
        assert config._parse_bool("K", raw) is True
    for raw in ("false", "FALSE", "0", "no"):
        assert config._parse_bool("K", raw) is False
    with pytest.raises(config.ConfigError, match="K"):
        config._parse_bool("K", "maybe")


def test_invalid_color_names_key(tmp_path):
    path = write_env(tmp_path, "PLAYING_ICON_COLOR=blue\n")
    with pytest.raises(config.ConfigError, match="PLAYING_ICON_COLOR"):
        config.load(path, environ={})


def test_color_out_of_range_names_key(tmp_path):
    path = write_env(tmp_path, "PLAYING_ICON_COLOR=300,0,0\n")
    with pytest.raises(config.ConfigError, match="PLAYING_ICON_COLOR"):
        config.load(path, environ={})


def test_checkpoint_needs_two_coordinates(tmp_path):
    path = write_env(tmp_path, "CHECKPOINT_PLAYING_ICON=10\n")
    with pytest.raises(config.ConfigError, match="CHECKPOINT_PLAYING_ICON"):
        config.load(path, environ={})


def test_negative_tolerance_rejected(tmp_path):
    path = write_env(tmp_path, "COLOR_TOLERANCE=-1\n")
    with pytest.raises(config.ConfigError, match="COLOR_TOLERANCE"):
        config.load(path, environ={})


def test_patch_radius_and_match_fraction_defaults():
    cfg = config.Config()
    assert cfg.patch_radius == 3
    assert cfg.match_fraction == 0.34


def test_patch_radius_and_match_fraction_from_env(tmp_path):
    path = write_env(tmp_path, "PATCH_RADIUS=5\nMATCH_FRACTION=0.5\n")
    cfg = config.load(path, environ={})
    assert cfg.patch_radius == 5
    assert cfg.match_fraction == 0.5


def test_match_fraction_out_of_range_rejected(tmp_path):
    for bad in ("0", "1.5", "-0.2", "abc"):
        path = write_env(tmp_path, f"MATCH_FRACTION={bad}\n")
        with pytest.raises(config.ConfigError, match="MATCH_FRACTION"):
            config.load(path, environ={})


def test_negative_patch_radius_rejected(tmp_path):
    path = write_env(tmp_path, "PATCH_RADIUS=-1\n")
    with pytest.raises(config.ConfigError, match="PATCH_RADIUS"):
        config.load(path, environ={})


def test_unknown_key_warns_but_continues(tmp_path, capsys):
    path = write_env(tmp_path, "TYPO_KEY=1\n")
    cfg = config.load(path, environ={})
    assert cfg == config.Config()
    assert "TYPO_KEY" in capsys.readouterr().err
