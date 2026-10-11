"""Simulated demand forecast: daily orders from the restaurants, per product."""

from datetime import date, timedelta

import pandas as pd

from sim import clock, events

HISTORY_DAYS = 14
HORIZON_DAYS = 7
SAFETY_BUFFER = 0.05  # produce 5% above the forecast
BANQUET_UPLIFT = 0.35  # a banquet order adds 35% to tomorrow

# Typical units ordered per day.
PRODUCTS = {"Har Gow": 5200, "Siew Mai": 4600, "Char Siew Bao": 3100, "Roast Duck": 600}

# Monday to Sunday: weekends are busier.
WEEKDAY_FACTOR = [0.90, 0.92, 0.95, 1.00, 1.15, 1.30, 1.25]


def daily(now):
    """Forecast for the last two weeks and the coming week, with actuals for past days.

    `low` and `high` give the forecast range, which widens further into the future.
    """
    today = date.fromtimestamp(now)
    rows = []
    for offset in range(-HISTORY_DAYS, HORIZON_DAYS + 1):
        day = today + timedelta(days=offset)
        for seed, (product, base) in enumerate(PRODUCTS.items()):
            forecast = base * WEEKDAY_FACTOR[day.weekday()]
            if offset == 1 and events.is_active("banquet_order"):
                forecast *= 1 + BANQUET_UPLIFT
            row = {"date": pd.Timestamp(day), "product": product, "forecast": round(forecast), "days_ahead": offset}
            if offset < 0:
                error = 0.07 * (2 * float(clock.rand(day.toordinal(), seed)) - 1)
                row["actual"] = round(forecast * (1 + error))
            else:
                band = 0.05 + 0.01 * offset
                row["low"], row["high"] = round(forecast * (1 - band)), round(forecast * (1 + band))
            rows.append(row)
    return pd.DataFrame(rows)


def accuracy(frame):
    """Forecast accuracy over the past days, in percent (100 minus the average error)."""
    past = frame.dropna(subset=["actual"])
    return 100 - 100 * ((past["actual"] - past["forecast"]).abs() / past["actual"]).mean()


def production_plan(frame):
    """Tomorrow's production plan per product, compared with today's."""
    today = frame[frame["days_ahead"] == 0].set_index("product")["forecast"]
    tomorrow = frame[frame["days_ahead"] == 1].set_index("product")["forecast"]
    plan = pd.DataFrame({
        "Forecast demand": tomorrow,
        "Safety buffer": (tomorrow * SAFETY_BUFFER).round().astype(int),
    })
    plan["Planned production"] = plan["Forecast demand"] + plan["Safety buffer"]
    plan["Change vs today"] = ((tomorrow / today - 1) * 100).round(1)
    return plan.loc[list(PRODUCTS)].reset_index(names="Product")


def status(now):
    frame = daily(now)
    tomorrow = int(frame[frame["days_ahead"] == 1]["forecast"].sum())
    alerts = []
    if events.is_active("banquet_order"):
        extra = round(tomorrow * BANQUET_UPLIFT / (1 + BANQUET_UPLIFT))
        alerts.append(events.alert(
            "banquet_order",
            f"Large banquet order received: tomorrow's demand is up by {extra:,} units",
            f"Tomorrow's production plan rises from {tomorrow - extra:,} to {tomorrow:,} units before the safety buffer",
            "Order the extra ingredients today and start tomorrow's shift earlier",
        ))
    return {"headline": ("Tomorrow's demand", f"{tomorrow:,} units"), "alerts": alerts}
