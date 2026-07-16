"""Randomisiertes Timing, portiert 1:1 aus dem Original-Autoskipper."""
from random import Random


def random_press_interval(rng: Random) -> float:
    """Intervall zwischen Tastendrücken: meist 0,12-0,18 s, 1-in-6 0,18-0,2 s."""
    return rng.uniform(0.18, 0.2) if rng.randint(1, 6) == 6 else rng.uniform(0.12, 0.18)


def should_take_break(rng: Random) -> bool:
    """1-in-25-Chance auf eine Menschenpause."""
    return rng.randint(1, 25) == 1


def random_break_duration(rng: Random) -> float:
    """Pausenlänge 3-8 Sekunden."""
    return rng.uniform(3.0, 8.0)
