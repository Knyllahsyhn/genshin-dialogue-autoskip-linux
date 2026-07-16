"""Randomized timing, ported 1:1 from the original auto-skipper."""
from random import Random


def random_press_interval(rng: Random) -> float:
    """Interval between key presses: usually 0.12-0.18 s, 1-in-6 0.18-0.2 s."""
    return rng.uniform(0.18, 0.2) if rng.randint(1, 6) == 6 else rng.uniform(0.12, 0.18)


def should_take_break(rng: Random) -> bool:
    """1-in-25 chance of taking a human-like break."""
    return rng.randint(1, 25) == 1


def random_break_duration(rng: Random) -> float:
    """Break length of 3-8 seconds."""
    return rng.uniform(3.0, 8.0)
