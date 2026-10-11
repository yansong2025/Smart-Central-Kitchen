"""Simulated front-of-house service robot delivering dishes in the restaurant.

Positions are in metres, measured from the kitchen pass: x runs across the
dining room, y runs from the front of the room to the back.
"""

import math

import numpy as np
import pandas as pd

from sim import clock, events

NAME = "Server-01"
HISTORY_S = 600
STEP_S = 2
TRIP_S = 30  # one delivery: drive to the table, serve, drive back
DAILY_TARGET = 320
MAX_WAIT_MIN = 4.0  # alert when guests wait longer than this on average
BATTERY_CYCLE_S = 1500

KITCHEN_PASS = {"x": 0.0, "y": 3.5}
AISLES_Y = [2.25, 4.75]  # the robot drives along these, between the rows of tables
DISHES = ["Har Gow", "Siew Mai", "Char Siew Bao", "Roast Duck", "Egg Tarts", "Cheong Fun"]

# Twelve tables in three rows of four, each with two to four guests.
TABLES = [
    {"table": n + 1, "x": 3 + 2.5 * (n % 4), "y": 1 + 2.5 * (n // 4), "guests": 2 + int(clock.rand(n, 11) * 3)}
    for n in range(12)
]


def service(now, seconds=HISTORY_S):
    """Orders waiting at the kitchen pass and the average wait, over the last `seconds`.

    A lunch rush piles orders up faster than one robot can deliver them.
    """
    ticks = clock.timeline(now, seconds, STEP_S)
    rush = events.intensity("lunch_rush", ticks, ramp_s=12)
    backlog = np.clip(2 + 1.2 * clock.wave(ticks, seed=4) + 7 * rush, 1, None)
    return pd.DataFrame({
        "time": clock.as_times(ticks),
        "orders": backlog.round().astype(int),
        "wait_min": (1.8 + 0.35 * backlog).round(2),
    })


def orders_waiting(now):
    return int(service(now, seconds=0)["orders"].iloc[-1])


def average_wait_min(now):
    return float(service(now, seconds=0)["wait_min"].iloc[-1])


def _trip_number(now):
    return int(now // TRIP_S)


def _table_for(trip):
    return TABLES[int(clock.rand(trip, 3) * len(TABLES))]


def queue(now):
    """The waiting orders, longest wait first. The first is on the robot now."""
    trip = _trip_number(now)
    wait = average_wait_min(now)
    count = orders_waiting(now)
    return [
        {
            "Table": _table_for(trip + i)["table"],
            "Dish": DISHES[int(clock.rand(trip + i, 9) * len(DISHES))],
            # Waits are spread evenly around the average: 1.5x for the oldest order, 0.5x for the newest.
            "Waiting": f"{wait * (1.5 - i / max(count - 1, 1)):.1f} min",
            "Status": "On robot" if i == 0 else "At pass",
        }
        for i in range(count)
    ]


def _path_to(table):
    """Way-points from the kitchen pass to a spot beside the table, following the nearest aisle."""
    aisle = min(AISLES_Y, key=lambda y: abs(y - table["y"]))
    return [(KITCHEN_PASS["x"] + 0.9, KITCHEN_PASS["y"]), (1.5, aisle), (table["x"], aisle)]


def _point_along(path, share):
    """The point a `share` (0 to 1) of the way along a path of way-points."""
    lengths = [math.dist(a, b) for a, b in zip(path, path[1:])]
    remaining = share * sum(lengths)
    for (a, b), length in zip(zip(path, path[1:]), lengths):
        if remaining <= length:
            return a[0] + (b[0] - a[0]) * remaining / length, a[1] + (b[1] - a[1]) * remaining / length
        remaining -= length
    return path[-1]


def position(now):
    """Where the robot is: out to the table, a pause to serve, then back to the pass."""
    table = _table_for(_trip_number(now))
    number = table["table"]
    share = (now % TRIP_S) / TRIP_S
    if share < 0.4:
        along, activity, short, carrying = share / 0.4, f"Delivering to table {number}", f"To T{number}", True
    elif share < 0.6:
        along, activity, short, carrying = 1.0, f"Serving table {number}", f"Serving T{number}", True
    else:
        along, activity, short, carrying = (1 - share) / 0.4, "Returning to the kitchen pass", "Returning", False
    x, y = _point_along(_path_to(table), along)
    return {"x": round(x, 2), "y": round(y, 2), "table": number, "activity": activity, "short": short, "carrying": carrying}


def battery(now):
    return 92 - 50 * (now % BATTERY_CYCLE_S) / BATTERY_CYCLE_S


def deliveries_today(now):
    return int(DAILY_TARGET * clock.shift_progress(now))


def status(now):
    wait = average_wait_min(now)
    alerts = []
    if wait > MAX_WAIT_MIN:
        alerts.append(events.alert(
            "lunch_rush",
            f"Lunch rush: {NAME} cannot keep up with orders",
            f"{orders_waiting(now)} orders waiting, guests wait {wait:.1f} min on average against a {MAX_WAIT_MIN:.0f} min limit",
            "Send two staff to run dishes from the kitchen pass until the queue clears",
        ))
    return {"headline": ("Average wait", f"{wait:.1f} min"), "alerts": alerts}
