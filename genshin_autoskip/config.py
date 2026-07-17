"""User configuration from an optional .env file plus environment overrides."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CHECKPOINTS: dict[str, tuple[int, int]] = {
    "playing_icon": (84, 46),
    "dialogue_icon_lower": (1301, 808),
    "dialogue_icon_higher": (1301, 790),
    "loading_screen": (1200, 700),
}

# Maps .env keys to checkpoint names.
CHECKPOINT_KEYS = {
    "CHECKPOINT_PLAYING_ICON": "playing_icon",
    "CHECKPOINT_DIALOGUE_ICON_LOWER": "dialogue_icon_lower",
    "CHECKPOINT_DIALOGUE_ICON_HIGHER": "dialogue_icon_higher",
    "CHECKPOINT_LOADING_SCREEN": "loading_screen",
}

KNOWN_KEYS = {
    "NOTIFICATIONS",
    "AUTO_CONFIRM",
    "PLAYING_ICON_COLOR",
    "COLOR_TOLERANCE",
    *CHECKPOINT_KEYS,
}

_TRUE = {"true", "1", "yes"}
_FALSE = {"false", "0", "no"}


class ConfigError(Exception):
    """Invalid configuration value; the message names the offending key."""


@dataclass(frozen=True)
class Config:
    notifications: bool = True
    auto_confirm: bool = True
    playing_icon_color: tuple[int, int, int] = (236, 229, 216)
    color_tolerance: int = 10
    checkpoints: dict[str, tuple[int, int]] = field(
        default_factory=lambda: dict(DEFAULT_CHECKPOINTS)
    )


DEFAULT_CONFIG = Config()


def parse_env_text(text: str) -> dict[str, str]:
    """Parse KEY=VALUE lines; '#' comments and blank lines are ignored."""
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ConfigError(f"invalid line in .env (expected KEY=VALUE): {line!r}")
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip()
    return values


def _parse_bool(key: str, raw: str) -> bool:
    value = raw.lower()
    if value in _TRUE:
        return True
    if value in _FALSE:
        return False
    raise ConfigError(f"{key}: expected true/false, got {raw!r}")


def _parse_ints(key: str, raw: str, count: int) -> tuple[int, ...]:
    parts = [p.strip() for p in raw.split(",")]
    try:
        numbers = tuple(int(p) for p in parts)
    except ValueError:
        raise ConfigError(
            f"{key}: expected {count} comma-separated integers, got {raw!r}"
        ) from None
    if len(numbers) != count:
        raise ConfigError(
            f"{key}: expected {count} comma-separated integers, got {raw!r}"
        )
    if any(n < 0 for n in numbers):
        raise ConfigError(f"{key}: values must be non-negative, got {raw!r}")
    return numbers


def _parse_color(key: str, raw: str) -> tuple[int, int, int]:
    r, g, b = _parse_ints(key, raw, 3)
    if any(v > 255 for v in (r, g, b)):
        raise ConfigError(f"{key}: RGB values must be 0-255, got {raw!r}")
    return (r, g, b)


def load(path: str | Path = ".env", environ: dict[str, str] | None = None) -> Config:
    """Build a Config from the .env file (optional) plus environment overrides."""
    environ = os.environ if environ is None else environ
    values: dict[str, str] = {}
    env_path = Path(path)
    if env_path.is_file():
        values.update(parse_env_text(env_path.read_text()))
    for unknown in sorted(set(values) - KNOWN_KEYS):
        print(f"Warning: unknown key in .env ignored: {unknown}", file=sys.stderr)
    for key in KNOWN_KEYS:
        if key in environ:
            values[key] = environ[key]

    checkpoints = dict(DEFAULT_CHECKPOINTS)
    for env_key, name in CHECKPOINT_KEYS.items():
        if env_key in values:
            x, y = _parse_ints(env_key, values[env_key], 2)
            checkpoints[name] = (x, y)

    notifications = DEFAULT_CONFIG.notifications
    if "NOTIFICATIONS" in values:
        notifications = _parse_bool("NOTIFICATIONS", values["NOTIFICATIONS"])
    auto_confirm = DEFAULT_CONFIG.auto_confirm
    if "AUTO_CONFIRM" in values:
        auto_confirm = _parse_bool("AUTO_CONFIRM", values["AUTO_CONFIRM"])
    color = DEFAULT_CONFIG.playing_icon_color
    if "PLAYING_ICON_COLOR" in values:
        color = _parse_color("PLAYING_ICON_COLOR", values["PLAYING_ICON_COLOR"])
    tolerance = DEFAULT_CONFIG.color_tolerance
    if "COLOR_TOLERANCE" in values:
        (tolerance,) = _parse_ints("COLOR_TOLERANCE", values["COLOR_TOLERANCE"], 1)

    return Config(
        notifications=notifications,
        auto_confirm=auto_confirm,
        playing_icon_color=color,
        color_tolerance=tolerance,
        checkpoints=checkpoints,
    )
