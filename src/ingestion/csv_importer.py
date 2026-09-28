"""CSV column detection, validation, and normalization."""

from __future__ import annotations

import pandas as pd

ALIASES = {
    "review_text": ("review_text", "feedback", "review", "comment", "text", "response"),
    "rating": ("rating", "stars", "score"),
    "review_date": ("review_date", "date", "created_at", "timestamp"),
    "source": ("source", "platform", "channel"),
}


def import_csv(uploaded_file, mapping: dict[str, str] | None = None) -> pd.DataFrame:
    try:
        frame = pd.read_csv(uploaded_file)
    except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as error:
        raise ValueError(f"Could not read CSV file: {error}") from error
    if frame.empty:
        raise ValueError("The uploaded CSV has no data rows.")
    original = {str(column).strip().lower(): column for column in frame.columns}
    mapping = mapping or {}
    selected = {}
    for field, aliases in ALIASES.items():
        requested = mapping.get(field)
        column = requested if requested in frame.columns else next(
            (original[alias] for alias in aliases if alias in original), None
        )
        if column is not None:
            selected[field] = column
    if "review_text" not in selected:
        raise ValueError("CSV needs a feedback, review, comment, or text column.")
    result = pd.DataFrame()
    result["review_text"] = frame[selected["review_text"]]
    result["rating"] = frame[selected["rating"]] if "rating" in selected else None
    result["review_date"] = frame[selected["review_date"]] if "review_date" in selected else pd.Timestamp.now(tz="UTC")
    result["source"] = frame[selected["source"]] if "source" in selected else "CSV Survey"
    return result