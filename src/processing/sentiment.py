"""VADER-based sentiment analysis with an explicitly uncalibrated strength proxy."""

from __future__ import annotations

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

EXPLICIT_FAILURE_TERMS = (
    "crash", "crashes", "crashed", "crashing", "bug", "bugs", "broken",
    "does not work", "doesn't work", "cannot use", "can't use", "fails", "failure",
)


class SentimentEngine:
    """Analyze text locally; confidence is a polarity-strength proxy, not probability."""

    def __init__(self) -> None:
        self._analyzer = SentimentIntensityAnalyzer()

    def analyze_text(self, text: object) -> dict[str, object]:
        if not isinstance(text, str) or not text.strip():
            return {"sentiment": "neutral", "sentiment_score": 0.0, "confidence": 0.0}
        compound = float(self._analyzer.polarity_scores(text)["compound"])
        if abs(compound) < 0.05 and any(term in text.casefold() for term in EXPLICIT_FAILURE_TERMS):
            compound = -0.35
        label = "positive" if compound >= 0.05 else "negative" if compound <= -0.05 else "neutral"
        return {"sentiment": label, "sentiment_score": compound, "confidence": abs(compound)}

    def analyze(self, data: pd.DataFrame, batch_size: int = 500) -> pd.DataFrame:
        """Return a copy with sentiment fields; batch_size limits intermediate work."""
        result = data.copy()
        if result.empty:
            return result
        text_column = "cleaned_text" if "cleaned_text" in result else "review_text"
        outputs: list[dict[str, object]] = []
        texts = result[text_column].tolist()
        for start in range(0, len(texts), max(1, batch_size)):
            outputs.extend(self.analyze_text(text) for text in texts[start:start + batch_size])
        scores = pd.DataFrame(outputs, index=result.index)
        for column in scores:
            result[column] = scores[column]
        result["processed"] = True
        return result