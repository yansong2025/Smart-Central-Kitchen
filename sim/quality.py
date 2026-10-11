"""Simulated AI vision quality check: every tray of formed dim sum is inspected."""

import numpy as np
import pandas as pd

from sim import clock, events, forming

HISTORY_S = 600
STEP_S = 2  # one tray is inspected every 2 seconds
TRAY_PIECES = 50
BASE_DEFECT_RATE = 0.014
SPIKE_DEFECT_RATE = 0.12  # extra defects while the mould is worn
TARGET_PASS_RATE = 97.0
REJECT_TRAY_AT = 3  # defects in one tray
ROLLING_TRAYS = 15  # pass rate is averaged over the last 30 seconds
DAILY_TARGET = 46_000

DEFECT_TYPES = ["Torn wrapper", "Underfilled", "Open seam", "Misshapen"]


def inspections(now, seconds=HISTORY_S):
    """One row per inspected tray over the last `seconds`."""
    ticks = clock.timeline(now, seconds, STEP_S)
    spike = events.intensity("defect_spike", ticks, ramp_s=10)
    defect_rate = BASE_DEFECT_RATE + SPIKE_DEFECT_RATE * spike
    defects = np.floor(TRAY_PIECES * defect_rate + clock.rand(ticks, 5)).astype(int)

    # A worn mould mostly produces misshapen pieces; otherwise the type is random.
    random_type = (clock.rand(ticks, 6) * len(DEFECT_TYPES)).astype(int)
    type_index = np.where((spike > 0.3) & (clock.rand(ticks, 8) < 0.8), DEFECT_TYPES.index("Misshapen"), random_type)

    frame = pd.DataFrame({
        "time": clock.as_times(ticks),
        "product": forming.current_batch(now)["product"]["name"],
        "defects": defects,
        "defect_type": np.array(DEFECT_TYPES)[type_index],
        "confidence": (0.95 + 0.049 * clock.rand(ticks, 7)).round(3),
    })
    frame["pass_rate"] = (100 * (1 - frame["defects"] / TRAY_PIECES)).rolling(ROLLING_TRAYS, min_periods=1).mean().round(2)
    frame["rejected"] = frame["defects"] >= REJECT_TRAY_AT
    return frame


def pass_rate(now):
    return inspections(now, seconds=ROLLING_TRAYS * STEP_S)["pass_rate"].iloc[-1]


def pieces_inspected_today(now):
    return int(DAILY_TARGET * clock.shift_progress(now))


def status(now):
    rate = pass_rate(now)
    alerts = []
    if rate < TARGET_PASS_RATE:
        rejected = int(inspections(now)["rejected"].sum())
        alerts.append(events.alert(
            "defect_spike",
            f"Quality pass rate fell to {rate:.1f}% (target {TARGET_PASS_RATE:.0f}%)",
            f"{rejected} trays rejected in the last 10 minutes: {rejected * TRAY_PIECES:,} pieces scrapped",
            "Pause the forming line and replace the worn mould",
        ))
    return {"headline": ("Pass rate", f"{rate:.1f}%"), "alerts": alerts}
