"""Simulated dim sum forming machine: throughput, piece weight, hopper and batches."""

import pandas as pd

from sim import clock, events

HISTORY_S = 600
STEP_S = 2
TARGET_PPM = 120  # pieces per minute
DAILY_TARGET = 48_000
WEIGHT_TOLERANCE_G = 1.0
BATCH_S = 240  # the line switches product every 4 minutes so the demo shows a changeover
HOPPER_CYCLE_S = 180
PIECE_VALUE_SGD = 0.40  # made-up value of one formed piece

PRODUCTS = [
    {"name": "Har Gow", "weight_g": 25},
    {"name": "Siew Mai", "weight_g": 28},
    {"name": "Char Siew Bao", "weight_g": 60},
]


def current_batch(now):
    index = int(now // BATCH_S)
    return {
        "number": index % 1000,
        "product": PRODUCTS[index % len(PRODUCTS)],
        "progress": (now % BATCH_S) / BATCH_S,
    }


def throughput(now, seconds=HISTORY_S):
    """Pieces per minute over the last `seconds`. A jam brings the line almost to a stop."""
    ticks = clock.timeline(now, seconds, STEP_S)
    ppm = TARGET_PPM + 4 * clock.wave(ticks, seed=1) + 3 * (clock.rand(ticks, seed=1) - 0.5)
    ppm = ppm * (1 - 0.97 * events.intensity("forming_jam", ticks, ramp_s=5))
    return pd.DataFrame({"time": clock.as_times(ticks), "ppm": ppm.round(1)})


def weight_deviation(now, pieces=300):
    """How far each of the latest `pieces` is from its target weight, in grams."""
    ticks = clock.timeline(now, pieces * STEP_S, STEP_S)
    # Adding three random numbers gives a bell-shaped spread around zero.
    spread = clock.rand(ticks, 2) + clock.rand(ticks, 3) + clock.rand(ticks, 4) - 1.5
    return pd.DataFrame({"deviation_g": (0.75 * spread).round(2)})


def hopper_level(now):
    """Filling hopper level in percent: drains steadily, then is topped up."""
    return 100 - 75 * (now % HOPPER_CYCLE_S) / HOPPER_CYCLE_S


def jam_seconds(now):
    return events.active_seconds("forming_jam", now)


def pieces_lost(now):
    return int(TARGET_PPM / 60 * jam_seconds(now))


def pieces_today(now):
    return max(int(DAILY_TARGET * clock.shift_progress(now)) - pieces_lost(now), 0)


def downtime_min(now):
    return 6 + jam_seconds(now) / 60  # 6 minutes of planned changeovers so far


def status(now):
    ppm = throughput(now, seconds=0)["ppm"].iloc[-1]
    alerts = []
    if ppm < TARGET_PPM / 2:
        lost = pieces_lost(now)
        alerts.append(events.alert(
            "forming_jam",
            f"Forming line jammed: {ppm:.0f} pcs/min against a target of {TARGET_PPM}",
            f"{lost:,} pieces of output lost so far, worth about S${lost * PIECE_VALUE_SGD:,.0f}",
            "Clear the jam at the forming head and restart the line",
        ))
    return {"headline": ("Throughput", f"{ppm:.0f} pcs/min"), "alerts": alerts}
