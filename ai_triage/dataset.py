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

_PRIORITY_HINTS: dict[str, list[str]] = {
    "High": [
        "sparking",
        "leaking",
        "flooding",
        "not working",
        "emergency",
        "unsafe",
        "shock",
        "blocked",
        "broken",
        "crashing",
        "unreachable",
        "fire",
    ],
    "Medium": [
        "flickering",
        "low pressure",
        "stuck",
        "loose",
        "sticky",
        "offline",
        "distorted",
        "missing",
        "foul smell",
        "overdue",
        "slow",
        "noisy",
    ],
    "Low": [
        "cosmetic",
        "paint",
        "minor",
        "noise",
        "inquiry",
        "signage",
        "graffiti",
        "lost item",
        "menu",
        "parking",
    ],
}


def _inject_priority_hint(text: str, priority: str) -> str:
    # Always append a strong, priority-specific phrase so the classifier can learn.
    phrases = {
        "High": [
            "This is an urgent safety issue.",
            "Immediate attention required.",
            "Risk of damage or injury.",
            "Emergency maintenance needed.",
        ],
        "Medium": [
            "Prompt attention requested.",
            "Should be fixed soon.",
            "Affects normal operations.",
            "Needs maintenance soon.",
        ],
        "Low": [
            "Can be scheduled later.",
            "Minor inconvenience.",
            "Low urgency request.",
            "Non-blocking issue.",
        ],
    }
    candidates = phrases.get(priority, [])
    if candidates:
        return f"{text} {random.choice(candidates)}"
    return text


# Category -> priority distribution weights (higher = more likely).
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
        description = _inject_priority_hint(title, priority)
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
