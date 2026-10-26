"""The seven smart-kitchen systems.

SYSTEMS is the page registry (app.py builds the navigation from it) and the
source of the Overview cards. Every simulator listed here provides
`status(now) -> {"headline": (label, value), "alerts": [events.alert(...), ...]}`.
"""

from sim import amr, duck_oven, foh_robot, forecast, forming, quality, temperature

# icon: a Material Symbols name. section: the navigation group the page sits in.
SYSTEMS = [
    {"name": "Dim Sum Forming Machine", "icon": "conveyor_belt", "section": "Production",
     "page": "views/forming.py", "sim": forming},
    {"name": "AI Quality Check", "icon": "document_scanner", "section": "Production",
     "page": "views/quality.py", "sim": quality},
    {"name": "Smart Duck Oven", "icon": "oven_gen", "section": "Production",
     "page": "views/duck_oven.py", "sim": duck_oven},
    {"name": "IoT Temperature Monitoring", "icon": "device_thermostat", "section": "Food safety",
     "page": "views/iot_temperature.py", "sim": temperature},
    {"name": "AMR Robot", "icon": "robot_2", "section": "Robotics",
     "page": "views/amr.py", "sim": amr},
    {"name": "FOH Service Robot", "icon": "room_service", "section": "Robotics",
     "page": "views/foh_robot.py", "sim": foh_robot},
    {"name": "Demand Forecast", "icon": "query_stats", "section": "Planning",
     "page": "views/forecast.py", "sim": forecast},
]


def summary(now):
    """One card per system: its name, icon and page, plus its headline metric and alerts."""
    cards = []
    for system in SYSTEMS:
        status = system["sim"].status(now)
        label, value = status["headline"]
        cards.append({**system, "label": label, "value": value, "alerts": status["alerts"]})
    return cards
