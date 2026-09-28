# Multi-Source Feedback Intelligence System

A local Streamlit application that consolidates Google Play reviews, Apple App Store RSS reviews, and CSV survey feedback. It cleans and deduplicates records, applies sentiment analysis and understandable issue categories, prioritizes recurring complaints, visualizes trends, and exports a PDF summary.

## Features

- Demo mode with a dated, multi-source sample dataset; no credentials or network required.
- Google Play review retrieval, Apple App Store public RSS ingestion, and mapped CSV imports.
- Shared validation and normalization pipeline with accepted, rejected, and duplicate counts.
- VADER sentiment analysis, keyword categorization, and explainable issue-level priority scores.
- Overview, feedback search/filtering (including manual CSV column mapping), daily/weekly/monthly charts, issue frequency comparisons, prioritized issues, ingestion status, and PDF reports.
- Source failures are shown in the dashboard without discarding already-loaded records.

## Requirements and Installation

Python 3.11 or newer is recommended. From the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows activate with `.venv\Scripts\activate`.

## Run the Dashboard

```sh
streamlit run app.py
```

The dashboard starts with clearly labeled demonstration data. Use the left sidebar to add reviews or import a CSV. Reset to demo data to restore the original sample.

## Data Sources

### Google Play

Enter an Android package name such as `com.example.app` and a review limit. The connector uses `google-play-scraper`, an unofficial community library. It is subject to Google-side changes, throttling, and availability limits; retrieval errors are shown rather than hidden.

Install the optional connector package if using this integration:

```sh
python -m pip install google-play-scraper
```

### Apple App Store

Enter the numeric App Store application ID and storefront country. Reviews come from Apple's public customer-review RSS feed, which exposes only a limited set of recent reviews and metadata.

### CSV Surveys

Upload a UTF-8 CSV containing a feedback column named `feedback`, `review`, `comment`, `text`, or `review_text`. Optional columns include `rating`/`stars`, `date`/`review_date`, and `source`/`platform`. Unmapped source defaults to `CSV Survey`; missing dates default to ingestion time. Ratings must be between 1 and 5. Empty text, invalid dates, and invalid ratings are rejected with counts shown in status.

Example:

```csv
feedback,rating,date,source
The app is helpful,5,2026-09-01,Survey
It crashes on launch,1,2026-09-02,Survey
```

## Analysis Notes

VADER is a lightweight, local, rule-based English sentiment model suited to short reviews, with a narrow explicit-failure fallback for crash/bug language that VADER otherwise scores as neutral. `sentiment_score` is the compound polarity score in [-1, 1] (with that fallback represented as -0.35). `confidence` is the absolute score, a polarity-strength proxy only; it is **not** a calibrated probability or a statistically validated confidence estimate. No labeled evaluation corpus is included, so this project makes no accuracy claim. Keyword categories are deliberately transparent and can miss indirect or multilingual feedback.

Issue priority is a transparent heuristic based on negative count, negative share, rating, severe phrases, and recent negative volume. A single review cannot trigger Critical or High priority. Priority levels are triage aids, not statistical significance claims. Period comparisons show sample counts and warn about small samples.

## Project Structure

```text
app.py                         Streamlit user interface
data/sample_feedback.csv       Offline demonstration data
src/ingestion/                 Google Play, Apple RSS, CSV, processing pipeline
src/processing/                Cleaning, sentiment, categorization, prioritization
src/analytics/                 Descriptive and temporal metrics
src/reporting/                 PDF report generation
tests/                         Automated component and integration checks
```

## Tests

```sh
pytest -q
```

The tests cover normalization, deduplication, sentiment, CSV validation, connector input validation, empty analytics, the shared pipeline, and PDF output.

## Limitations and Next Steps

- Google Play scraping is unofficial; Apple RSS is constrained by Apple's exposed feed data.
- Sentiment and categories are English-focused heuristics/models. Evaluation requires a representative labeled dataset.
- Trend detection compares negative category counts across adjacent 30-day windows ending at the latest negative review. It flags topics with fewer than two previous-period complaints as new or insufficient-baseline instead of overstating the change. All trend comparisons are descriptive, not significance tests.
- Confidence is not statistically calibrated. Configurable category management in the UI is a future improvement.
- Data is kept in Streamlit session state only and is not persisted between sessions.
## 🎥 Project Demo

Watch the complete project demonstration on YouTube:

[![Watch Demo](https://img.youtube.com/vi/wBHlnMb-96Y/0.jpg)](https://youtu.be/wBHlnMb-96Y)

**[▶ Watch Full Demo on YouTube](https://youtu.be/wBHlnMb-96Y)**

---

## 📸 Screenshots

![The main dashboard provides a centralized view of customer feedback collected from Google Play Store, Apple App Store, and CSV files. It displays key performance indicators, including total feedback, sentiment distribution, average ratings, and source-wise insights, enabling users to quickly understand customer satisfaction and identify areas for improvement.
](image.png)

