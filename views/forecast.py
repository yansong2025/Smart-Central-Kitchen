import time

import altair as alt
import streamlit as st

import ui
from sim import forecast

ui.page_header(
    "📈",
    "Demand Forecast",
    "Predicts daily restaurant orders so the kitchen produces the right amount: less waste, fewer shortages.",
)


def forecast_chart(frame):
    """Actual orders so far, the forecast, and the forecast range for the days ahead."""
    lines = frame.melt(id_vars="date", value_vars=["actual", "forecast"], var_name="series", value_name="units").dropna()
    lines["series"] = lines["series"].map({"actual": "Actual orders", "forecast": "Forecast"})
    x = alt.X("date:T", title=None, axis=alt.Axis(format="%a %d %b", tickCount="day", labelAngle=-45))

    band = alt.Chart(frame.dropna(subset=["low"])).mark_area(color=ui.SERIES_COLORS[1], opacity=0.18).encode(
        x=x, y="low:Q", y2="high:Q",
    )
    line = alt.Chart(lines).mark_line(strokeWidth=2, point=alt.OverlayMarkDef(size=40)).encode(
        x=x,
        y=alt.Y("units:Q", title="Units per day", scale=alt.Scale(zero=False)),
        color=alt.Color("series:N", title=None, legend=alt.Legend(orient="top"),
                        scale=alt.Scale(domain=["Actual orders", "Forecast"], range=ui.SERIES_COLORS)),
        tooltip=[alt.Tooltip("date:T", title="Day", format="%a %d %b"), alt.Tooltip("series:N", title="Series"),
                 alt.Tooltip("units:Q", title="Units", format=",")],
    )
    return (band + line).properties(height=320)


now = time.time()
frame = forecast.daily(now)
plan = forecast.production_plan(frame)

ui.alert_banner(forecast.status(now)["alerts"], "Demand is in line with the usual weekly pattern")
ui.kpi_row([
    ("Tomorrow's demand", f"{plan['Forecast demand'].sum():,} units"),
    ("Tomorrow's planned production", f"{plan['Planned production'].sum():,} units"),
    ("Forecast accuracy, last 14 days", f"{forecast.accuracy(frame):.1f}%"),
    ("Safety buffer", f"{forecast.SAFETY_BUFFER:.0%}"),
])

with ui.card("Daily demand: last 14 days and next 7 days"):
    product = st.segmented_control("Product", ["All products", *forecast.PRODUCTS], default="All products")
    if product in forecast.PRODUCTS:
        shown = frame[frame["product"] == product]
    else:
        shown = frame.groupby("date", as_index=False)[["forecast", "actual", "low", "high"]].sum(min_count=1)
    st.altair_chart(forecast_chart(shown), key="forecast")
    st.caption("The shaded area is the likely range. It widens the further ahead the forecast looks.")

with ui.card("Tomorrow's production plan"):
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
