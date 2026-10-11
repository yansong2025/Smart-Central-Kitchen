"""Floor plan of the central kitchen, used by the 3D twin and the AMR.

Positions are in metres: x runs left to right, z runs from the back wall
(negative) to the front (positive). The corridor runs along z = 0.
"system" links a zone to an entry in sim/systems.py; cold and hot zones are
linked to their temperature sensor by name.
"""

FLOOR = {"width": 26, "depth": 16}

ZONES = [
    # Back row: cold rooms, oven and hot holding
    {"name": "Chiller 1 · Dim Sum", "kind": "cold_room", "x": -10.5, "z": -5.5, "w": 3.6, "d": 4},
    {"name": "Chiller 2 · Meat & Poultry", "kind": "cold_room", "x": -6.5, "z": -5.5, "w": 3.6, "d": 4},
    {"name": "Freezer 1 · Seafood", "kind": "cold_room", "x": -2.5, "z": -5.5, "w": 3.6, "d": 4},
    {"name": "Freezer 2 · Frozen Dim Sum", "kind": "cold_room", "x": 1.5, "z": -5.5, "w": 3.6, "d": 4},
    {"name": "Duck Oven", "kind": "oven", "x": 5.9, "z": -5.5, "w": 3.6, "d": 4, "system": "Smart Duck Oven"},
    {"name": "Hot Holding · Roast Meats", "kind": "hot_cabinet", "x": 10.2, "z": -5.5, "w": 3.6, "d": 4},
    # Front row: goods in, production line, goods out
    {"name": "Receiving", "kind": "dock", "x": -10.5, "z": 5.5, "w": 3.6, "d": 4},
    {"name": "Cold Prep Room", "kind": "prep", "x": -6.0, "z": 5.5, "w": 4.4, "d": 4},
    {"name": "Dim Sum Forming", "kind": "forming", "x": -0.4, "z": 5.5, "w": 5.8, "d": 4, "system": "Dim Sum Forming Machine"},
    {"name": "AI Quality Check", "kind": "quality", "x": 5.0, "z": 5.5, "w": 4.0, "d": 4, "system": "AI Quality Check"},
    {"name": "Dispatch", "kind": "dock", "x": 10.2, "z": 5.5, "w": 3.6, "d": 4},
]

# The AMR's delivery loop: (x, z, stop name, job done there). Stop is None for a corner.
AMR_ROUTE = [
    (-10.5, 2.2, "Receiving", "Collect raw ingredients"),
    (-10.5, -2.2, "Chiller 1 · Dim Sum", "Deliver chilled fillings"),
    (-6.0, -2.2, None, None),
    (-6.0, 2.2, "Cold Prep Room", "Deliver ingredients for prep"),
    (-0.4, 2.2, "Dim Sum Forming", "Deliver wrappers and fillings"),
    (5.0, 2.2, "AI Quality Check", "Collect inspected trays"),
    (5.9, -2.2, "Duck Oven", "Collect roast ducks"),
    (10.2, -2.2, "Hot Holding · Roast Meats", "Deliver roast ducks"),
    (10.2, 2.2, "Dispatch", "Deliver trays for dispatch"),
    (10.2, 0.0, None, None),
    (-10.5, 0.0, None, None),
]
