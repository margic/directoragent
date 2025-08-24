from __future__ import annotations


def classify_intent(message: str) -> str:
    lower = message.lower()
    if any(k in lower for k in ["who's leading", "whos leading", "leader", "gap"]):
        return "LEADER"
    if any(k in lower for k in ["battle", "closest", "who's close", "whos close", "close battle"]):
        return "BATTLE"
    if "what happened" in lower or "miss" in lower:
        return "RECENT_EVENTS"
    if "who is" in lower or "car" in lower:
        return "DRIVER_INFO"
    if "pit" in lower or "strategy" in lower or "fuel" in lower:
        return "STRATEGY"
    if "penalty" in lower or "incident" in lower or "crash" in lower:
        return "INCIDENT"
    return "OTHER"
