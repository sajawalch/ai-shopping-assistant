"""Turn a LangGraph result (or interrupt) into the JSON the React UI renders."""
from __future__ import annotations

YES_NO = [{"label": "Yes, show more", "value": "yes"}, {"label": "No, I'm done", "value": "no"}]
CATEGORIES = [{"label": "💻 Laptop", "value": "laptop"}, {"label": "📱 Mobile phone", "value": "phone"}]
LAPTOP_USES = [{"label": l, "value": v} for l, v in [
    ("Gaming", "gaming"), ("Programming", "programming"),
    ("Office work", "office"), ("University studies", "university")]]
PHONE_USES = [{"label": l, "value": v} for l, v in [
    ("Gaming", "gaming"), ("Photography", "photography"),
    ("Daily use", "daily"), ("Battery life", "battery")]]


def to_payload(thread_id: str, result: dict) -> dict:
    pending = result.get("__interrupt__")
    if not pending:
        return {"thread_id": thread_id, "type": "done",
                "message": "Thanks for shopping with me! Happy with your new purchase. 👋",
                "options": [], "laptops": []}

    value = pending[0].value
    if isinstance(value, dict):  # recommendation + yes/no question
        return {"thread_id": thread_id, "type": "recommendation",
                "message": value["recommendation"], "laptops": value.get("ranked", []),
                "question": value["question"], "options": YES_NO, "step": "more"}

    text = str(value)
    options: list[dict] = []
    step = "text"
    if "shopping for" in text:
        step, options = "category", CATEGORIES
    elif "like to change" in text:
        step, options = "change", [{"label": "Just show other models", "value": ""}]
    elif "budget" in text:
        step = "budget"
    elif "need the laptop for" in text:
        step, options = "use", LAPTOP_USES
    elif "need the phone for" in text:
        step, options = "use", PHONE_USES
    return {"thread_id": thread_id, "type": "question", "step": step, "message": text,
            "options": options, "laptops": []}
