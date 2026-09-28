"""Normalize incoming feedback into the application's common schema."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

REQUIRED_COLUMNS = ("source", "review_text", "rating", "review_date")
OUTPUT_COLUMNS = (
    "feedback_id", "source", "review_text", "rating", "review_date",
    "ingestion_date", "sentiment", "sentiment_score", "confidence",
    "category", "priority_score", "priority_level", "processed", "cleaned_text",
)
SOURCE_ALIASES = {
    "google play": "Google Play", "google play store": "Google Play",
    "play store": "Google Play", "apple": "Apple App Store",
    "app store": "Apple App Store", "apple app store": "Apple App Store",
    "csv": "CSV Survey", "survey": "CSV Survey", "csv survey": "CSV Survey",
}


@dataclass
class CleaningResult:
    data: pd.DataFrame
    accepted: int
    modified: int
    rejected: int
    duplicates: int
    errors: list[str]


def clean_feedback(data: pd.DataFrame) -> CleaningResult:
    """Validate, normalize, and deduplicate source records without hiding failures."""
    if data.empty:
        return CleaningResult(pd.DataFrame(columns=OUTPUT_COLUMNS), 0, 0, 0, 0, [])

    frame = data.copy()
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    missing = [column for column in REQUIRED_COLUMNS if column not in frame]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    original_text = frame["review_text"].copy()
    original_source = frame["source"].copy()
    original_date = frame["review_date"].copy()
    normalized_text = frame["review_text"].fillna("").astype(str).map(
        lambda text: re.sub(r"\s+", " ", text).strip()
    )
    frame["review_text"] = normalized_text
    normalized_source = frame["source"].fillna("CSV Survey").astype(str).str.strip()
    normalized_source = normalized_source.map(
        lambda value: SOURCE_ALIASES.get(value.casefold(), value or "CSV Survey")
    )
    modified_mask = original_text.fillna("").astype(str).ne(normalized_text)
    modified_mask |= original_source.fillna("").astype(str).str.strip().ne(normalized_source)
    modified_mask |= original_date.map(
        lambda value: pd.notna(value) and not isinstance(value, pd.Timestamp)
    )
    frame["source"] = normalized_source
    frame["rating"] = pd.to_numeric(frame["rating"], errors="coerce")
    frame["review_date"] = pd.to_datetime(frame["review_date"], errors="coerce", utc=True)

    invalid = frame["review_text"].eq("") | frame["review_date"].isna()
    invalid |= frame["rating"].notna() & ~frame["rating"].between(1, 5)
    rejected = int(invalid.sum())
    frame = frame.loc[~invalid].copy()
    before_duplicates = len(frame)
    frame = frame.drop_duplicates(subset=["source", "review_text", "review_date"], keep="first")
    duplicates = before_duplicates - len(frame)

    frame["rating"] = frame["rating"].astype("Float64")
    frame["ingestion_date"] = pd.Timestamp.now(tz="UTC")
    frame["cleaned_text"] = frame["review_text"]
    if "feedback_id" not in frame:
        frame["feedback_id"] = pd.util.hash_pandas_object(
            frame[["source", "review_text", "review_date"]], index=False
        ).astype(str)
    for column, default in (
        ("sentiment", None), ("sentiment_score", None), ("confidence", None),
        ("category", None), ("priority_score", None), ("priority_level", None),
        ("processed", False),
    ):
        if column not in frame:
            frame[column] = default

    frame = frame.reindex(columns=OUTPUT_COLUMNS)
    errors = [f"Rejected {rejected} record(s) with empty text, invalid dates, or ratings outside 1-5."] if rejected else []
    modified = int(modified_mask.loc[frame.index].sum())
    return CleaningResult(frame.reset_index(drop=True), len(frame), modified, rejected, duplicates, errors)