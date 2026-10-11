"""Shared building blocks for the simulators.

Everything here is a pure function of time, so every rerun and every page
computes the same values without storing any history.
"""

from datetime import datetime

import numpy as np

SHIFT_START_H, SHIFT_END_H = 6, 22


def timeline(now, seconds, step):
    """Evenly spaced timestamps covering the last `seconds`, ending at `now`."""
    latest = int(now // step) * step
    return np.arange(latest - seconds, latest + step, step)


def as_times(ticks):
    return [datetime.fromtimestamp(t) for t in ticks]


def wave(t, seed=0):
    """Smooth drift between -1 and 1 (two overlapping slow waves)."""
    t = np.asarray(t, dtype=float)
    return 0.7 * np.sin(t / 45 + seed) + 0.3 * np.sin(t / 7 + 2 * seed)


def rand(t, seed=0):
    """Repeatable "random" number between 0 and 1 for each value of `t`."""
    x = np.sin((np.asarray(t, dtype=float) % 100_000) * 12.9898 + seed * 78.233) * 43758.5453
    return x - np.floor(x)


def shift_progress(now):
    """Fraction of today's production shift that has passed, from 0 to 1."""
    t = datetime.fromtimestamp(now)
    hours = t.hour + t.minute / 60 + t.second / 3600
    return min(max((hours - SHIFT_START_H) / (SHIFT_END_H - SHIFT_START_H), 0), 1)
