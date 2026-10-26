import time

import altair as alt
import streamlit as st

import ui
from sim import forecast

ui.system_header(
    "Demand Forecast",
    "Predicts daily restaurant orders so the kitchen produces the right amount: less waste, fewer shortages.",
    live=False,
)


def forecast_chart(frame):
    """Actual orders so far, the forecast, and the forecast range for the days ahead."""
    lines = frame.melt(id_vars="date", value_vars=["actual", "forecast"], var_name="series", value_name="units").dropna()
    lines["series"] = lines["series"].map({"actual": "Actual orders", "forecast": "Forecast"})
    x = alt.X("date:T", title=None, axis=alt.Axis(format="%a %d", tickCount="day", labelAngle=0, labelOverlap=True))

    band = alt.Chart(frame.dropna(subset=["low"])).mark_area(color=ui.SERIES_COLORS[1], opacity=0.15).encode(
        x=x, y="low:Q", y2="high:Q",
    )
    line = alt.Chart(lines).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=36, filled=True)).encode(
        x=x,
        y=alt.Y("units:Q", title="Units per day", scale=alt.Scale(zero=False)),
        color=alt.Color("series:N", legend=alt.Legend(orient="top", direction="horizontal"),
                        scale=alt.Scale(domain=["Actual orders", "Forecast"], range=ui.SERIES_COLORS)),
        tooltip=[alt.Tooltip("date:T", title="Day", format="%a %d %b"), alt.Tooltip("series:N", title="Series"),
                 alt.Tooltip("units:Q", title="Units", format=",")],
    )
    today = alt.Chart(frame[frame["days_ahead"] == 0].head(1)).mark_rule(color="#98a2b3", strokeDash=[2, 3]).encode(x="date:T")
    return band + today + line


now = time.time()
frame = forecast.daily(now)
plan = forecast.production_plan(frame)
alerts = forecast.status(now)["alerts"]

ui.alert_banner(alerts, "Demand is in line with the usual weekly pattern")
ui.kpi_row([
    ui.kpi("Tomorrow's demand", f"{plan['Forecast demand'].sum():,}", unit="units", icon_name="shopping_cart",
           note="Banquet order included" if alerts else "Normal weekly pattern"),
    ui.kpi("Planned production", f"{plan['Planned production'].sum():,}", unit="units", icon_name="factory",
           note=f"Forecast plus a {forecast.SAFETY_BUFFER:.0%} safety buffer"),
    ui.kpi("Forecast accuracy", f"{forecast.accuracy(frame):.1f}", unit="%", icon_name="target",
           note=f"Last {forecast.HISTORY_DAYS} days"),
    ui.kpi("Products planned", len(forecast.PRODUCTS), icon_name="restaurant_menu",
           note=", ".join(forecast.PRODUCTS)),
])

with ui.card("Daily demand", f"Last {forecast.HISTORY_DAYS} days and next {forecast.HORIZON_DAYS} days. "
                             "The shaded band is the likely range; it widens further ahead."):
    product = st.segmented_control("Product", ["All products", *forecast.PRODUCTS], default="All products",
                                   label_visibility="collapsed")
    if product in forecast.PRODUCTS:
        shown = frame[frame["product"] == product]
    else:
        shown = frame.groupby(["date", "days_ahead"], as_index=False)[["forecast", "actual", "low", "high"]].sum(min_count=1)
    ui.show_chart(forecast_chart(shown), key="forecast", height=320)

with ui.card("Tomorrow's production plan", "What the kitchen will make tomorrow, per product"):
    st.dataframe(
        plan,
        hide_index=True,
        column_config={
            "Forecast demand": st.column_config.NumberColumn(format="localized"),
            "Safety buffer": st.column_config.NumberColumn(format="localized"),
            "Planned production": st.column_config.NumberColumn(format="localized"),
            "Change vs today": st.column_config.NumberColumn(format="%+.1f%%"),
        },
    )
