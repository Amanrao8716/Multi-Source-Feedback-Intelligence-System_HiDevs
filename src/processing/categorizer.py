"""Configurable keyword categories for interpretable feedback grouping."""

from __future__ import annotations

import re

DEFAULT_CATEGORIES = {
    "Bugs and Errors": ("crash", "crashes", "crashed", "crashing", "bug", "bugs", "error", "errors", "broken", "freeze", "freezes"),
    "Performance and Stability": ("slow", "loading", "lag", "performance", "battery"),
    "User Interface and Experience": ("design", "interface", "layout", "confusing", "navigation"),
    "Feature Requests": ("please add", "would like", "feature", "wish", "dark mode"),
    "Pricing and Payments": ("price", "payment", "charged", "subscription", "refund", "billing"),
    "Customer Support": ("support", "help desk", "customer service", "response"),
    "Account and Login": ("login", "sign in", "password", "account", "verification"),
}


def categorize(text: object, sentiment: object = None, rules: dict | None = None) -> str:
    if not isinstance(text, str) or not text.strip():
        return "Other or Unclassified"
    normalized = text.casefold()
    for category, keywords in (rules or DEFAULT_CATEGORIES).items():
        if any(re.search(r"\b" + re.escape(keyword.casefold()) + r"\b", normalized) for keyword in keywords):
            return category
    if str(sentiment).casefold() == "positive":
        return "Positive Feedback"
    return "Other or Unclassified"


def categorize_feedback(data):
    result = data.copy()
    if not result.empty:
        result["category"] = [categorize(text, sentiment) for text, sentiment in zip(result.review_text, result.sentiment)]
    return result