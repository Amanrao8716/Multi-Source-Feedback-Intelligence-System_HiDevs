"""Generate a concise, data-grounded PDF summary with a sentiment chart."""

from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from xml.sax.saxutils import escape

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.analytics.metrics import sentiment_summary, volume_over_time
from src.analytics.trends import compare_issue_trends
from src.processing.priority import prioritize_issues


def generate_pdf(data: pd.DataFrame, start_date=None, end_date=None) -> bytes:
    frame = data.copy()
    if not frame.empty and start_date is not None and end_date is not None:
        dates = pd.to_datetime(frame.review_date, utc=True, errors="coerce")
        start = pd.Timestamp(start_date, tz="UTC") if pd.Timestamp(start_date).tzinfo is None else pd.Timestamp(start_date).tz_convert("UTC")
        end = pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1) if pd.Timestamp(end_date).tzinfo is None else pd.Timestamp(end_date).tz_convert("UTC")
        frame = frame[(dates >= start) & (dates < end)]
    summary = sentiment_summary(frame)
    output = BytesIO()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#173b35")))
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=0.65 * inch, leftMargin=0.65 * inch)
    story = [Paragraph("Multi-Source Feedback Intelligence", styles["ReportTitle"]),
             Paragraph(f"Customer feedback report | {start_date or 'All available dates'} to {end_date or 'present'}", styles["Normal"]),
             Paragraph(f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}", styles["Normal"]), Spacer(1, 18),
             Paragraph("Executive Summary", styles["Heading1"]),
             Paragraph(f"{summary['total']} feedback entries from {summary['sources']} source(s). "
                       f"Positive: {summary['positive_pct']:.1f}%; negative: {summary['negative_pct']:.1f}%; "
                       f"neutral: {summary['neutral_pct']:.1f}%.", styles["BodyText"]), Spacer(1, 10)]
    avg = summary["average_rating"]
    story.append(Paragraph(f"Average rating: {avg:.2f} / 5" if pd.notna(avg) else "Average rating: unavailable", styles["BodyText"]))
    sources = ", ".join(sorted(frame.source.dropna().astype(str).unique())) if summary["total"] else "No sources available"
    story.extend([Spacer(1, 6), Paragraph(f"Sources included: {escape(sources)}", styles["BodyText"])])
    if summary["total"]:
        chart = BytesIO()
        counts = frame.sentiment.value_counts().reindex(["positive", "neutral", "negative"], fill_value=0)
        plt.figure(figsize=(5, 2.8))
        plt.bar(counts.index.str.title(), counts.values, color=["#25856a", "#d6a32f", "#c6534b"])
        plt.ylabel("Feedback entries")
        plt.tight_layout()
        plt.savefig(chart, format="png", dpi=130)
        plt.close()
        chart.seek(0)
        story.extend([Spacer(1, 10), Image(chart, width=4.8 * inch, height=2.7 * inch)])
        volume = volume_over_time(frame, "W")
        if not volume.empty:
            volume_chart = BytesIO()
            plt.figure(figsize=(6, 2.5))
            plt.plot(volume.period, volume.feedback_count, marker="o", color="#25856a")
            plt.ylabel("Feedback entries")
            plt.xticks(rotation=25, ha="right")
            plt.tight_layout()
            plt.savefig(volume_chart, format="png", dpi=130)
            plt.close()
            volume_chart.seek(0)
            story.extend([Paragraph("Feedback Trends", styles["Heading1"]),
                          Image(volume_chart, width=5.8 * inch, height=2.5 * inch)])
    story.extend([Spacer(1, 10), Paragraph("Priority Issues", styles["Heading1"])])
    issues = prioritize_issues(frame)
    table_data = [["Issue", "Negative", "Negative %", "Avg rating", "Priority"]]
    for _, issue in issues.head(8).iterrows():
        rating = f"{issue.average_rating:.2f}" if pd.notna(issue.average_rating) else "N/A"
        table_data.append([str(issue.category), str(issue.negative_count), f"{issue.negative_pct:.1f}%", rating, str(issue.priority_level)])
    table = Table(table_data, repeatRows=1, colWidths=[2.25 * inch, 0.75 * inch, 0.85 * inch, 0.8 * inch, 0.8 * inch])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173b35")),
                               ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5d1")),
                               ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f3")]),
                               ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")] ))
    story.append(table)
    issue_trends = compare_issue_trends(frame)
    story.extend([Spacer(1, 14), Paragraph("Issue Changes", styles["Heading1"])])
    if issue_trends.empty:
        story.append(Paragraph("No dated negative issue data is available for a period comparison.", styles["BodyText"]))
    else:
        trend_rows = [["Issue", "Current 30d", "Previous 30d", "Change", "Direction"]]
        for _, trend in issue_trends.head(8).iterrows():
            trend_rows.append([escape(str(trend.category)), str(trend.current_negative),
                               str(trend.previous_negative), f"{trend.change:+d}", trend.trend])
        trend_table = Table(trend_rows, repeatRows=1, colWidths=[2.1 * inch, 0.9 * inch, 0.95 * inch, 0.65 * inch, 1.35 * inch])
        trend_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173b35")),
                                         ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                         ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5d1")),
                                         ("FONTSIZE", (0, 0), (-1, -1), 8), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.extend([trend_table, Paragraph("Comparison windows end at the latest dated negative review. Increasing or declining labels require at least two complaints in the prior period.", styles["BodyText"])])

    story.extend([Spacer(1, 14), Paragraph("Actionable Insights", styles["Heading1"])])
    negative_issues = issues[issues.negative_count > 0].head(5)
    if negative_issues.empty:
        story.append(Paragraph("No negative issue categories were observed in this period.", styles["BodyText"]))
    else:
        dated = frame.copy()
        dated["review_date"] = pd.to_datetime(dated.review_date, utc=True, errors="coerce")
        for _, issue in negative_issues.iterrows():
            related = dated[(dated.category == issue.category) & dated.sentiment.eq("negative")].sort_values("review_date", ascending=False)
            comment = str(related.review_text.iloc[0])[:320]
            story.append(Paragraph(
                f"Observed: {escape(str(issue.category))} has {issue.negative_count} negative report(s) among {issue.total_feedback} related entries ({issue.negative_pct:.1f}% negative). {escape(issue.factors)}.",
                styles["BodyText"]))
            story.append(Paragraph(f"Customer comment: &quot;{escape(comment)}&quot;", styles["BodyText"]))
            story.append(Paragraph("Suggested investigation: reproduce the reported experience and review the related recent feedback before selecting a product or support change.", styles["BodyText"]))
            story.append(Spacer(1, 6))

    story.extend([Spacer(1, 8), Paragraph("Data Limitations", styles["Heading1"]),
                  Paragraph("Sentiment labels use VADER plus a narrow explicit-failure fallback. The score is not a calibrated probability; the confidence field is an absolute polarity-strength proxy. Small samples and source coverage can limit trend interpretation. Priority scores are heuristic triage indicators, not statistical significance claims.", styles["BodyText"])])
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()


def _footer(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#62716c"))
    canvas.drawString(0.65 * inch, 0.4 * inch, "Multi-Source Feedback Intelligence | Internal analysis")
    canvas.drawRightString(7.85 * inch, 0.4 * inch, f"Page {document.page}")
    canvas.restoreState()