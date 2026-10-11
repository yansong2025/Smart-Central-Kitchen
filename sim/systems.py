"""The seven smart-kitchen systems.

SYSTEMS is the page registry (app.py builds the navigation from it) and the
source of the Overview cards. Every simulator listed here provides
`status(now) -> {"headline": (label, value), "alerts": [events.alert(...), ...]}`.
"""

from sim import amr, duck_oven, foh_robot, forecast, forming, quality, temperature

SYSTEMS = [
    {"name": "Dim Sum Forming Machine", "icon": "🥟", "page": "views/forming.py", "sim": forming},
    {"name": "AI Quality Check", "icon": "🔍", "page": "views/quality.py", "sim": quality},
    {"name": "Smart Duck Oven", "icon": "🦆", "page": "views/duck_oven.py", "sim": duck_oven},
    {"name": "IoT Temperature Monitoring", "icon": "🌡️", "page": "views/iot_temperature.py", "sim": temperature},
    {"name": "AMR Robot", "icon": "🤖", "page": "views/amr.py", "sim": amr},
    {"name": "Demand Forecast", "icon": "📈", "page": "views/forecast.py", "sim": forecast},
    {"name": "FOH Service Robot", "icon": "🍽️", "page": "views/foh_robot.py", "sim": foh_robot},
]


def summary(now):
    """One card per system: its name, icon and page, plus its headline metric and alerts."""
    cards = []
    for system in SYSTEMS:
        status = system["sim"].status(now)
        label, value = status["headline"]
        cards.append({**system, "label": label, "value": value, "alerts": status["alerts"]})
    return cards
