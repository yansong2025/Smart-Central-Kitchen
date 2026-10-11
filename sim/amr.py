"""Simulated autonomous mobile robot (AMR) that carries trays around the kitchen."""

import math

from sim import clock, events
from sim.layout import AMR_ROUTE

NAME = "AMR-01"
SPEED_M_S = 1.1
STOP_S = 5  # time spent loading or unloading at each stop
DAILY_TARGET = 140
BATTERY_CYCLE_S = 1200


def _legs():
    """The loop as a list of legs: travel to the next point, then wait there if it is a stop."""
    legs = []
    for i, (x, z, stop, job) in enumerate(AMR_ROUTE):
        prev_x, prev_z = AMR_ROUTE[i - 1][:2]
        travel_s = math.dist((prev_x, prev_z), (x, z)) / SPEED_M_S
        legs.append({"from": (prev_x, prev_z), "to": (x, z), "stop": stop, "job": job,
                     "travel_s": travel_s, "total_s": travel_s + (STOP_S if stop else 0)})
    return legs


LEGS = _legs()
LOOP_S = sum(leg["total_s"] for leg in LEGS)


def blocked_seconds(now):
    return events.active_seconds("amr_blocked", now)


def state(now):
    """Where the robot is and what it is doing. Time spent blocked does not move it."""
    blocked = events.is_active("amr_blocked")
    t = (now - blocked_seconds(now)) % LOOP_S

    for index, leg in enumerate(LEGS):
        if t < leg["total_s"]:
            break
        t -= leg["total_s"]

    share = min(t / leg["travel_s"], 1)
    x = leg["from"][0] + (leg["to"][0] - leg["from"][0]) * share
    z = leg["from"][1] + (leg["to"][1] - leg["from"][1]) * share
    at_stop = leg["stop"] is not None and t >= leg["travel_s"]

    # Upcoming stops with their arrival time, starting from the current leg.
    queue, eta = [], leg["travel_s"] - t
    for step in range(len(LEGS)):
        upcoming = LEGS[(index + step) % len(LEGS)]
        if step > 0:
            eta += upcoming["travel_s"]
        if upcoming["stop"] and not (step == 0 and at_stop):
            queue.append({"Stop": upcoming["stop"], "Arrives in": f"{max(eta, 0):.0f} s"})
        eta += STOP_S if upcoming["stop"] else 0

    if blocked:
        activity = "Blocked: obstacle in aisle"
    elif at_stop:
        activity = f"{leg['job']} at {leg['stop']}"
    else:
        activity = f"Driving to {queue[0]['Stop']}"

    return {"x": round(x, 2), "z": round(z, 2), "blocked": blocked, "activity": activity, "queue": queue[:5]}


def battery(now):
    """Battery in percent: drains over a 20-minute cycle, then swaps to a charged pack."""
    return 95 - 55 * (now % BATTERY_CYCLE_S) / BATTERY_CYCLE_S


def deliveries_missed(now):
    return int(blocked_seconds(now) / (LOOP_S / 8))  # eight stops per loop


def deliveries_today(now):
    return max(int(DAILY_TARGET * clock.shift_progress(now)) - deliveries_missed(now), 0)


def status(now):
    alerts = []
    if events.is_active("amr_blocked"):
        alerts.append(events.alert(
            "amr_blocked",
            f"{NAME} is blocked by an obstacle in the aisle",
            f"Stopped for {blocked_seconds(now):.0f} s so far: {deliveries_missed(now)} deliveries behind schedule",
            "Clear the aisle, and carry urgent trays by hand until the robot is moving",
        ))
    return {"headline": ("Deliveries today", f"{deliveries_today(now):,}"), "alerts": alerts}
