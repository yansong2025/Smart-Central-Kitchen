"""Simulated IoT temperature sensors for the cold rooms and hot holding."""

import pandas as pd

from sim import clock, events

HISTORY_S = 600  # how much history the charts show
STEP_S = 2  # seconds between readings

# low / high are the safe limits in °C (None = no limit on that side).
# event / event_rise: a demo event that pushes this sensor up by that many °C.
# stock / value_sgd: what is stored there and what it is worth (made-up figures).
# action: what staff should do if the zone goes out of range.
# Names match the zones in sim/layout.py so readings show up on the 3D twin.
SENSORS = [
    {"name": "Chiller 1 · Dim Sum", "base": 3.0, "low": 0, "high": 5,
     "event": "chiller_door_open", "event_rise": 9.0,
     "stock": "420 kg of fresh dim sum", "value_sgd": 6300,
     "action": "Close the chiller door and check the door seal"},
    {"name": "Chiller 2 · Meat & Poultry", "base": 2.5, "low": 0, "high": 5,
     "stock": "650 kg of raw meat and poultry", "value_sgd": 9100,
     "action": "Check the chiller door and compressor"},
    {"name": "Freezer 1 · Seafood", "base": -21.0, "low": None, "high": -18,
     "event": "freezer_fault", "event_rise": 12.0,
     "stock": "800 kg of frozen seafood", "value_sgd": 24000,
     "action": "Call the refrigeration technician and move stock to Freezer 2"},
    {"name": "Freezer 2 · Frozen Dim Sum", "base": -20.5, "low": None, "high": -18,
     "stock": "1,100 kg of frozen dim sum", "value_sgd": 13200,
     "action": "Call the refrigeration technician and move stock to Freezer 1"},
    {"name": "Cold Prep Room", "base": 13.0, "low": None, "high": 15,
     "stock": "90 kg of fillings being prepared", "value_sgd": 1100,
     "action": "Check the room cooling and return fillings to the chiller"},
    {"name": "Hot Holding · Roast Meats", "base": 68.0, "low": 60, "high": None,
     "stock": "48 roast ducks ready to dispatch", "value_sgd": 2900,
     "action": "Check the cabinet heater and reheat or dispatch the ducks now"},
]


def history(now, seconds=HISTORY_S):
    """Readings for every sensor over the last `seconds` (long format)."""
    ticks = clock.timeline(now, seconds, STEP_S)
    frames = []
    for i, sensor in enumerate(SENSORS):
        # The slow wave stands in for compressor cycling and sensor drift.
        temp = sensor["base"] + 0.55 * clock.wave(ticks, seed=i)
        if "event" in sensor:
            # A short ramp so the demo shows the excursion within a few seconds.
            temp = temp + sensor["event_rise"] * events.intensity(sensor["event"], ticks, ramp_s=12)
        frames.append(pd.DataFrame({"time": clock.as_times(ticks), "sensor": sensor["name"], "temp_c": temp.round(2)}))
    return pd.concat(frames, ignore_index=True)


def in_range(sensor, temp_c):
    above_low = sensor["low"] is None or temp_c >= sensor["low"]
    below_high = sensor["high"] is None or temp_c <= sensor["high"]
    return above_low and below_high


def limit_text(sensor):
    if sensor["low"] is None:
        return f"≤ {sensor['high']} °C"
    if sensor["high"] is None:
        return f"≥ {sensor['low']} °C"
    return f"{sensor['low']} to {sensor['high']} °C"


def latest(now):
    """Current temperature and in-range flag for each sensor."""
    current = history(now, seconds=0).groupby("sensor")["temp_c"].last()
    return [
        {**sensor, "temp_c": float(current[sensor["name"]]), "ok": in_range(sensor, current[sensor["name"]])}
        for sensor in SENSORS
    ]


def status(now):
    sensors = latest(now)
    alerts = [
        events.alert(
            f"temperature: {s['name']}",
            f"{s['name']} is at {s['temp_c']:.1f} °C (limit {limit_text(s)})",
            f"{s['stock']} at risk, worth about S${s['value_sgd']:,}",
            s["action"],
        )
        for s in sensors
        if not s["ok"]
    ]
    zones_ok = len(sensors) - len(alerts)
    return {"headline": ("Zones in range", f"{zones_ok} / {len(sensors)}"), "alerts": alerts}
