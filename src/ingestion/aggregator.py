"""Shared processing path for all sources and demo data."""

from __future__ import annotations

import pandas as pd

from src.processing.categorizer import categorize_feedback
from src.processing.cleaner import clean_feedback
from src.processing.priority import prioritize_issues
from src.processing.sentiment import SentimentEngine


def process_feedback(data: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    cleaned = clean_feedback(data)
    analyzed = SentimentEngine().analyze(cleaned.data)
    analyzed = categorize_feedback(analyzed)
    priorities = prioritize_issues(analyzed)
    if not analyzed.empty:
        analyzed = analyzed.merge(
            priorities[["category", "priority_score", "priority_level"]],
            on="category", how="left", suffixes=("", "_issue")
        )
        analyzed["priority_score"] = analyzed["priority_score_issue"]
        analyzed["priority_level"] = analyzed["priority_level_issue"]
        analyzed = analyzed.drop(columns=["priority_score_issue", "priority_level_issue"])
    return analyzed, {"accepted": cleaned.accepted, "modified": cleaned.modified,
                     "rejected": cleaned.rejected, "duplicates": cleaned.duplicates,
                     "errors": cleaned.errors, "issues": priorities}