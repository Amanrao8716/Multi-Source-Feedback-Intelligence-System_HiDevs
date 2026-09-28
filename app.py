"""Streamlit dashboard for multi-source customer feedback analysis."""

from __future__ import annotations

from io import BytesIO

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analytics.metrics import period_comparison, sentiment_summary, volume_over_time
from src.analytics.trends import compare_issue_trends
from src.ingestion.aggregator import process_feedback
from src.ingestion.app_store import fetch_reviews as fetch_apple_reviews
from src.ingestion.csv_importer import import_csv
from src.ingestion.google_play import fetch_reviews as fetch_google_reviews
from src.reporting.pdf_report import generate_pdf

st.set_page_config(page_title="Feedback Intelligence", page_icon="F", layout="wide")

COLORS = {"positive": "#25856a", "neutral": "#d6a32f", "negative": "#c6534b"}


def initialize_state() -> None:
    if "raw_feedback" not in st.session_state:
        st.session_state.raw_feedback = pd.read_csv("data/sample_feedback.csv")
        st.session_state.demo_mode = True
        st.session_state.events = ["Loaded demonstration dataset"]
        st.session_state.last_updated = pd.Timestamp.now(tz="UTC")


def append_source(frame: pd.DataFrame, label: str) -> None:
    if frame.empty:
        st.warning(f"{label} returned no reviews. Existing data is unchanged.")
        return
    st.session_state.raw_feedback = pd.concat([st.session_state.raw_feedback, frame], ignore_index=True)
    st.session_state.demo_mode = False
    st.session_state.last_updated = pd.Timestamp.now(tz="UTC")
    st.session_state.events.append(f"{label}: retrieved {len(frame)} records")
    st.success(f"Added {len(frame)} records from {label}.")


initialize_state()
st.title("Feedback Intelligence")
st.caption("Customer experience signals, consolidated across your feedback channels.")

with st.sidebar:
    st.header("Data sources")
    st.caption("The included demonstration dataset loads automatically.")
    with st.form("google_form"):
        package = st.text_input("Google Play package name", placeholder="com.example.app")
        review_limit = st.number_input("Review limit", min_value=1, max_value=2000, value=100)
        google_submit = st.form_submit_button("Fetch Google Play reviews", width="stretch")
    if google_submit:
        try:
            append_source(fetch_google_reviews(package, int(review_limit)), "Google Play")
        except (ValueError, RuntimeError) as error:
            st.error(str(error))
            st.session_state.events.append(f"Google Play failed: {error}")

    with st.form("apple_form"):
        app_id = st.text_input("Apple App Store app ID", placeholder="123456789")
        country = st.selectbox("Store country", ["us", "gb", "ca", "au", "in"])
        apple_submit = st.form_submit_button("Fetch Apple reviews", width="stretch")
    if apple_submit:
        try:
            append_source(fetch_apple_reviews(app_id, country), "Apple App Store")
        except (ValueError, RuntimeError) as error:
            st.error(str(error))
            st.session_state.events.append(f"Apple App Store failed: {error}")

    upload = st.file_uploader("Import survey CSV", type=["csv"])
    if upload is not None:
        try:
            columns = pd.read_csv(BytesIO(upload.getvalue()), nrows=0).columns.tolist()
            aliases = {
                "review_text": ("review_text", "feedback", "review", "comment", "text", "response"),
                "rating": ("rating", "stars", "score"),
                "review_date": ("review_date", "date", "created_at", "timestamp"),
                "source": ("source", "platform", "channel"),
            }

            def column_index(field, options, optional=False):
                matching = next((column for column in columns if column.strip().lower() in aliases[field]), None)
                return options.index(matching) if matching in options else (0 if not optional else 0)

            text_column = st.selectbox("Feedback text column", columns, index=column_index("review_text", columns))
            optional_columns = ["(None)"] + columns
            rating_column = st.selectbox("Rating column", optional_columns, index=column_index("rating", optional_columns, True))
            date_column = st.selectbox("Date column", optional_columns, index=column_index("review_date", optional_columns, True))
            source_column = st.selectbox("Source column", optional_columns, index=column_index("source", optional_columns, True))
            mapping = {"review_text": text_column}
            mapping.update({field: selected for field, selected in (
                ("rating", rating_column), ("review_date", date_column), ("source", source_column)
            ) if selected != "(None)"})
            uploaded = import_csv(BytesIO(upload.getvalue()), mapping)
            st.dataframe(uploaded.head(5), hide_index=True, width="stretch")
            if st.button("Add CSV feedback", width="stretch"):
                append_source(uploaded, "CSV Survey")
        except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as error:
            st.error(str(error))

    if st.button("Reset to demo data", width="stretch"):
        st.session_state.raw_feedback = pd.read_csv("data/sample_feedback.csv")
        st.session_state.demo_mode = True
        st.session_state.events.append("Reset to demonstration dataset")
        st.session_state.last_updated = pd.Timestamp.now(tz="UTC")
        st.rerun()

raw = st.session_state.raw_feedback.copy()
processed, pipeline = process_feedback(raw)
if st.session_state.demo_mode:
    st.info("Demonstration data is active. It is synthetic example data, not live customer feedback.")
if pipeline["errors"]:
    st.warning(" ".join(pipeline["errors"]))

summary = sentiment_summary(processed)
issues = pipeline["issues"]
high_priority = int(issues.priority_level.isin(["Critical", "High"]).sum()) if not issues.empty else 0

overview, explorer, trends, issue_tab, report_tab, status_tab = st.tabs(
    ["Overview", "Feedback explorer", "Trends", "Issues", "Reports", "Status"]
)

with overview:
    metrics = st.columns(7)
    metrics[0].metric("Feedback", f"{summary['total']:,}")
    metrics[1].metric("Sources", summary["sources"])
    metrics[2].metric("Positive", f"{summary['positive_pct']:.1f}%")
    metrics[3].metric("Negative", f"{summary['negative_pct']:.1f}%")
    metrics[4].metric("Neutral", f"{summary['neutral_pct']:.1f}%")
    metrics[5].metric("Average rating", f"{summary['average_rating']:.2f}" if pd.notna(summary["average_rating"]) else "N/A")
    metrics[6].metric("High priority", high_priority)
    chart_col, source_col = st.columns(2)
    if processed.empty:
        st.warning("No valid feedback to analyze. Add a source or load the demo dataset.")
    else:
        with chart_col:
            sentiment_counts = processed.sentiment.value_counts().rename_axis("Sentiment").reset_index(name="Feedback")
            fig = px.pie(sentiment_counts, names="Sentiment", values="Feedback", hole=0.58,
                         color="Sentiment", color_discrete_map=COLORS, title="Sentiment mix")
            st.plotly_chart(fig, width="stretch")
        with source_col:
            source_summary = processed.groupby(["source", "sentiment"]).size().reset_index(name="Feedback")
            fig = px.bar(source_summary, x="source", y="Feedback", color="sentiment", barmode="group",
                         color_discrete_map=COLORS, title="Sentiment by source")
            st.plotly_chart(fig, width="stretch")
        rating_counts = processed.dropna(subset=["rating"]).groupby("rating").size().reset_index(name="Feedback")
        if not rating_counts.empty:
            st.plotly_chart(px.bar(rating_counts, x="rating", y="Feedback", title="Rating distribution",
                                   labels={"rating": "Stars"}), width="stretch")

with explorer:
    st.subheader("Feedback explorer")
    if not processed.empty:
        filters = st.columns(4)
        selected_sources = filters[0].multiselect("Source", sorted(processed.source.unique()))
        selected_sentiments = filters[1].multiselect("Sentiment", ["positive", "neutral", "negative"])
        selected_categories = filters[2].multiselect("Category", sorted(processed.category.unique()))
        query = filters[3].text_input("Search feedback")
        more_filters = st.columns(3)
        date_values = pd.to_datetime(processed.review_date, utc=True, errors="coerce").dt.date.dropna()
        date_range = more_filters[0].date_input("Date range", (date_values.min(), date_values.max()))
        rating_range = more_filters[1].slider("Rating", 1.0, 5.0, (1.0, 5.0), 0.5)
        selected_priorities = more_filters[2].multiselect("Priority", ["Critical", "High", "Medium", "Low"])
        view = processed.copy()
        if selected_sources:
            view = view[view.source.isin(selected_sources)]
        if selected_sentiments:
            view = view[view.sentiment.isin(selected_sentiments)]
        if selected_categories:
            view = view[view.category.isin(selected_categories)]
        if query:
            view = view[view.review_text.str.contains(query, case=False, na=False)]
        if len(date_range) == 2:
            review_dates = pd.to_datetime(view.review_date, utc=True, errors="coerce").dt.date
            view = view[(review_dates >= date_range[0]) & (review_dates <= date_range[1])]
        if rating_range != (1.0, 5.0):
            view = view[view.rating.between(*rating_range).fillna(False) | view.rating.isna()]
        if selected_priorities:
            view = view[view.priority_level.isin(selected_priorities)]
        st.dataframe(view[["review_text", "source", "rating", "review_date", "sentiment", "category", "priority_level"]],
                 hide_index=True, width="stretch")
        st.caption(f"Showing {len(view)} of {len(processed)} entries")
    else:
        st.info("No feedback is available yet.")

with trends:
    st.subheader("Feedback over time")
    if not processed.empty:
        frequency_label = st.radio("Aggregation", ["Daily", "Weekly", "Monthly"], horizontal=True)
        frequency = {"Daily": "D", "Weekly": "W", "Monthly": "MS"}[frequency_label]
        series = volume_over_time(processed, frequency)
        st.plotly_chart(px.line(series, x="period", y="feedback_count", markers=True,
                    title=f"{frequency_label} feedback volume"), width="stretch")
        by_sentiment = processed.copy()
        period_frequency = "M" if frequency == "MS" else frequency
        by_sentiment["period"] = pd.to_datetime(by_sentiment.review_date, utc=True).dt.tz_convert(None).dt.to_period(period_frequency).astype(str)
        trend = by_sentiment.groupby(["period", "sentiment"]).size().reset_index(name="feedback")
        st.plotly_chart(px.line(trend, x="period", y="feedback", color="sentiment", markers=True,
                    color_discrete_map=COLORS, title="Sentiment counts over time"), width="stretch")
        trend_columns = st.columns(2)
        rating_trend = by_sentiment.groupby("period", as_index=False).rating.mean()
        trend_columns[0].plotly_chart(px.line(rating_trend, x="period", y="rating", markers=True,
                                              title="Average rating by period"), width="stretch")
        category_sentiment = processed.groupby(["category", "sentiment"]).size().reset_index(name="feedback")
        trend_columns[1].plotly_chart(px.bar(category_sentiment, x="category", y="feedback", color="sentiment",
                                             barmode="group", color_discrete_map=COLORS,
                                             title="Sentiment by category"), width="stretch")
        issue_trends = compare_issue_trends(processed)
        if not issue_trends.empty:
            st.subheader("Negative issue changes: latest 30 days vs previous 30 days")
            st.dataframe(issue_trends, hide_index=True, width="stretch")
            st.caption("Periods end at the latest dated negative review. Increasing/declining labels require at least two prior-period complaints; new or smaller topics are flagged as insufficient baseline.")
        comparison = period_comparison(processed)
        delta = f"{comparison['change_pct']:+.1f}%" if comparison["change_pct"] is not None else "No prior-period baseline"
        st.metric("Latest 7-day volume", comparison["current_count"], delta=delta)
        st.caption(f"Previous period: {comparison['previous_count']} entries. Period comparisons are descriptive; small samples are not statistically significant.")
    else:
        st.info("Add dated feedback to view trends.")

with issue_tab:
    st.subheader("Prioritized issues")
    if issues.empty:
        st.info("No issue categories are available yet.")
    else:
        st.dataframe(issues, hide_index=True, width="stretch")
        for _, issue in issues.head(5).iterrows():
            related = processed[(processed.category == issue.category) & processed.sentiment.eq("negative")]
            if not related.empty:
                st.markdown(f"**{issue.category}** · {issue.priority_level} · {issue.factors}")
                st.write("Representative feedback: " + " | ".join(related.review_text.head(2).tolist()))

with report_tab:
    st.subheader("PDF report")
    if not processed.empty:
        dates = pd.to_datetime(processed.review_date, utc=True, errors="coerce").dropna()
        lower, upper = st.columns(2)
        start_date = lower.date_input("Start date", value=dates.min().date())
        end_date = upper.date_input("End date", value=dates.max().date())
        if start_date > end_date:
            st.error("Start date must be on or before end date.")
        else:
            report_data = processed[(pd.to_datetime(processed.review_date, utc=True).dt.date >= start_date)
                                    & (pd.to_datetime(processed.review_date, utc=True).dt.date <= end_date)]
            report_summary = sentiment_summary(report_data)
            st.write(f"{report_summary['total']} entries · {report_summary['negative_pct']:.1f}% negative · {report_summary['positive_pct']:.1f}% positive")
            try:
                pdf = generate_pdf(processed, start_date, end_date)
                st.download_button("Download PDF report", pdf, file_name="feedback-report.pdf", mime="application/pdf")
            except Exception as error:
                st.error(f"Could not generate report: {error}")
    else:
        st.info("A report can be generated when feedback is available.")

with status_tab:
    st.subheader("Application status")
    status_columns = st.columns(4)
    status_columns[0].metric("Accepted", pipeline["accepted"])
    status_columns[1].metric("Rejected", pipeline["rejected"])
    status_columns[2].metric("Duplicates removed", pipeline["duplicates"])
    status_columns[3].metric("Last updated", st.session_state.last_updated.strftime("%H:%M UTC"))
    st.write("**Source records**")
    st.dataframe(raw.groupby("source", dropna=False).size().rename("Records").reset_index(), hide_index=True, width="stretch")
    st.write("**Recent ingestion activity**")
    for event in reversed(st.session_state.events[-10:]):
        st.write(f"- {event}")
    st.caption("Google Play retrieval uses an unofficial community scraper and may be affected by rate limits or upstream changes. Apple reviews are limited to entries exposed in Apple's public RSS feed.")