"""Synthetic complaint dataset for AI triage training."""

from __future__ import annotations

import random

CATEGORIES = [
    "Electrical",
    "Plumbing",
    "Furniture",
    "Cleanliness",
    "IT / Network",
    "Other",
]

PRIORITIES = ["Low", "Medium", "High"]

# Seed templates per category to keep text realistic and reproducible.
_CATEGORY_TEMPLATES: dict[str, list[str]] = {
    "Electrical": [
        "Power outlet not working in {room}.",
        "Flickering lights in {room} during lectures.",
        "Circuit breaker tripped in {room}.",
        "Ceiling fan switch defective in {room}.",
        "Extension board sparking near {room}.",
        "Emergency light not charging in {room}.",
        "Projector socket loose in {room}.",
        "AC power cable frayed in {room}.",
    ],
    "Plumbing": [
        "Water leaking from sink pipe in {room}.",
        "Toilet flush not working in {room}.",
        "Drainage blocked in {room}.",
        "Tap handle broken in {room}.",
        "Water pressure too low in {room}.",
        "Overflow from washbasin in {room}.",
        "Shower head missing in {room}.",
        "Urinal auto-sensor stuck in {room}.",
    ],
    "Furniture": [
        "Broken chair leg in {room}.",
        "Table drawer stuck in {room}.",
        "Whiteboard mounting loose in {room}.",
        "Window latch broken in {room}.",
        "Door handle fallen off in {room}.",
        "Bench slat cracked in {room}.",
        "Bookshelf anchor loose in {room}.",
        "Lab stool gas lift failed in {room}.",
    ],
    "Cleanliness": [
        "Dustbin overflowing in {room}.",
        "Floor wet and slippery in {room}.",
        "Cobwebs in ceiling corners of {room}.",
        "Restroom foul smell in {room}.",
        "Spilled food not cleaned in {room}.",
        "Garbage not collected from {room}.",
        "Sticky floor near {room}.",
        "Graffiti on wall in {room}.",
    ],
    "IT / Network": [
        "Wi-Fi not connecting in {room}.",
        "LAN port dead in {room}.",
        "Printer offline in {room}.",
        "Lab software crashing in {room}.",
        "Authentication server unreachable from {room}.",
        "Projector display distorted in {room}.",
        "Microphone not detected in {room}.",
        "VPN access blocked in {room}.",
    ],
    "Other": [
        "Lost item found near {room}.",
        "Noise complaint from {room}.",
        "Parking space occupied without permit near {room}.",
        "General inquiry about {room}.",
        "Signage unclear near {room}.",
        "Tree branch blocking walkway near {room}.",
        "Water cooler not working near {room}.",
        "Cafeteria menu missing allergen info near {room}.",
    ],
}

# Category-aware urgency phrases so the priority classifier can learn
# category-specific priority signals instead of generic global phrases.
_CATEGORY_PRIORITY_PHRASES: dict[str, dict[str, list[str]]] = {
    "Electrical": {
        "High": [
            "sparking",
            "shock risk",
            "fire hazard",
            "exposed wiring",
            "power outage",
        ],
        "Medium": [
            "flickering",
            "intermittent",
            "dim",
            "loose connection",
            "tripping",
        ],
        "Low": [
            "cosmetic",
            "paint",
            "sticker",
            "minor noise",
            "dust",
        ],
    },
    "Plumbing": {
        "High": [
            "leaking",
            "flooding",
            "burst pipe",
            "sewage backup",
            "no water",
        ],
        "Medium": [
            "low pressure",
            "slow drain",
            "stuck",
            "dripping",
            "clogged",
        ],
        "Low": [
            "cosmetic",
            "stain",
            "minor leak",
            "paint",
            "caulk",
        ],
    },
    "Furniture": {
        "High": [
            "unsafe",
            "collapsed",
            "broken leg",
            "sharp edge",
            "unstable",
        ],
        "Medium": [
            "stuck",
            "loose",
            "wobbly",
            "drawer stuck",
            "hinge broken",
        ],
        "Low": [
            "cosmetic",
            "paint",
            "stain",
            "minor wear",
            "scuff mark",
        ],
    },
    "Cleanliness": {
        "High": [
            "biohazard",
            "sewage",
            "flooding",
            "unsafe",
            "infestation",
        ],
        "Medium": [
            "foul smell",
            "overflowing",
            "spilled",
            "sticky",
            "trash",
        ],
        "Low": [
            "dust",
            "cobweb",
            "minor stain",
            "graffiti",
            "cosmetic",
        ],
    },
    "IT / Network": {
        "High": [
            "server down",
            "outage",
            "data loss",
            "security breach",
            "unreachable",
        ],
        "Medium": [
            "slow",
            "intermittent",
            "offline",
            "distorted",
            "lag",
        ],
        "Low": [
            "cosmetic",
            "label",
            "minor",
            "sticker",
            "display",
        ],
    },
    "Other": {
        "High": [
            "emergency",
            "unsafe",
            "blocked",
            "hazard",
            "urgent",
        ],
        "Medium": [
            "noise",
            "inquiry",
            "soon",
            "needs",
            "requested",
        ],
        "Low": [
            "cosmetic",
            "minor",
            "inquiry",
            "signage",
            "schedule",
        ],
    },
}

_ROOMS = [
    "Room 101",
    "Room 102",
    "Room 103",
    "Room 201",
    "Room 202",
    "Library",
    "Cafeteria",
    "Main Corridor",
    "Restroom Ground Floor",
    "Restroom First Floor",
    "Lab A",
    "Lab B",
    "Faculty Room",
    "Admin Block",
    "Sports Complex",
    "Hostel Block A",
]

_CATEGORY_PRIORITY_WEIGHTS: dict[str, dict[str, int]] = {
    "Electrical": {"High": 4, "Medium": 3, "Low": 1},
    "Plumbing": {"High": 4, "Medium": 2, "Low": 1},
    "Furniture": {"High": 1, "Medium": 3, "Low": 3},
    "Cleanliness": {"High": 1, "Medium": 2, "Low": 4},
    "IT / Network": {"High": 3, "Medium": 3, "Low": 1},
    "Other": {"High": 1, "Medium": 2, "Low": 4},
}


def _weighted_choice(category: str) -> str:
    weights = _CATEGORY_PRIORITY_WEIGHTS[category]
    items = []
    for priority, weight in weights.items():
        items.extend([priority] * weight)
    return random.choice(items)


def _inject_priority_hint(text: str, category: str, priority: str) -> str:
    phrases = _CATEGORY_PRIORITY_PHRASES.get(category, {}).get(priority, [])
    if not phrases:
        return text
    # Use 1-2 category-specific urgency phrases so the classifier can
    # learn priority from domain language, not generic appendages.
    chosen = random.sample(phrases, k=min(len(phrases), random.choice([1, 2])))
    return f"{text} {' '.join(chosen)}."


def generate_synthetic_complaints(count: int = 600, seed: int = 42) -> list[dict]:
    """Return a list of synthetic complaint dicts with title, description, category, priority."""
    random.seed(seed)
    samples: list[dict] = []
    categories = CATEGORIES[:]
    for _ in range(count):
        category = random.choice(categories)
        priority = _weighted_choice(category)
        room = random.choice(_ROOMS)
        title_template = random.choice(_CATEGORY_TEMPLATES[category])
        title = title_template.format(room=room)
        description = _inject_priority_hint(title, category, priority)
        if random.random() < 0.25:
            description = f"{description} Please fix urgently." if priority == "High" else f"{description} Please look into this when possible."
        samples.append(
            {
                "title": title,
                "description": description,
                "category": category,
                "priority": priority,
            }
        )
    return samples
