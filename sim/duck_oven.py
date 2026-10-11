"""Simulated smart duck oven running a programmed roast cycle.

A real roast takes about an hour. The demo compresses one cycle into 4 minutes
so the class can watch every phase.
"""

import numpy as np
import pandas as pd

from sim import clock, events

HISTORY_S = 600
STEP_S = 2
CYCLE_S = 240
DUCKS_PER_BATCH = 24
DAILY_TARGET = 600
CORE_TARGET_C = 75
HEATING_LAG_S = 8  # how quickly the oven follows a new setpoint
LEAK_DROP_C = 45  # heat lost through a leaking door seal
MAX_GAP_C = 20  # alert when the oven is this far below the recipe
DUCK_VALUE_SGD = 60  # made-up value of one roast duck

# (phase, starts at this fraction of the cycle, setpoint in °C)
PHASES = [
    ("Load", 0.00, 60),
    ("Dry", 0.08, 90),
    ("Roast", 0.25, 200),
    ("Crisp", 0.72, 240),
    ("Rest", 0.90, 120),
]


def cycle_fraction(t):
    return (np.asarray(t, dtype=float) % CYCLE_S) / CYCLE_S


def phase_index(t):
    starts = [start for _, start, _ in PHASES]
    return np.searchsorted(starts, cycle_fraction(t), side="right") - 1


def temperatures(now, seconds=HISTORY_S):
    """Recipe temperature and actual oven temperature over the last `seconds`."""
    warm_up = 60  # extra lead-in so the lag has settled by the first row we keep
    ticks = clock.timeline(now, seconds + warm_up, STEP_S)
    setpoint = np.array([s for _, _, s in PHASES])[phase_index(ticks)]

    # The recipe curve is the setpoint with a heating lag: each step closes part of the gap.
    recipe = np.empty(len(ticks))
    recipe[0] = setpoint[0]
    for i in range(1, len(ticks)):
        recipe[i] = recipe[i - 1] + (setpoint[i] - recipe[i - 1]) * STEP_S / HEATING_LAG_S

    leak = events.intensity("oven_door_leak", ticks, ramp_s=12)
    actual = recipe + 1.5 * clock.wave(ticks, seed=3) - LEAK_DROP_C * leak
    frame = pd.DataFrame({"time": clock.as_times(ticks), "recipe": recipe.round(1), "actual": actual.round(1)})
    return frame.iloc[warm_up // STEP_S:].reset_index(drop=True)


def core_temperature(now):
    """Core temperature of the ducks: climbs smoothly to just above the target."""
    progress = min(float(cycle_fraction(now)) / 0.9, 1)
    smooth = progress * progress * (3 - 2 * progress)
    leak = float(events.intensity("oven_door_leak", now, ramp_s=12))
    return 8 + 70 * smooth - 10 * leak


def ducks_today(now):
    return int(DAILY_TARGET * clock.shift_progress(now))


def status(now):
    latest = temperatures(now, seconds=0).iloc[-1]
    gap = latest["recipe"] - latest["actual"]
    alerts = []
    if gap > MAX_GAP_C:
        alerts.append(events.alert(
            "oven_door_leak",
            f"Duck oven is {gap:.0f} °C below the recipe ({latest['actual']:.0f} °C)",
            f"{DUCKS_PER_BATCH} ducks in this batch may be undercooked, worth about S${DUCKS_PER_BATCH * DUCK_VALUE_SGD:,}",
            f"Check the door seal and keep roasting until the core reaches {CORE_TARGET_C} °C",
        ))
    return {"headline": ("Oven temperature", f"{latest['actual']:.0f} °C"), "alerts": alerts}
