"""Aggregate Workouts, Steps, and Sleep into monthly/yearly summaries.

Reads from the Workouts, Steps, and Sleep databases and creates/updates
entries in the Summary database with totals per period (Month/Year) and
per modality.

Each period generates:
  - 1 "All" entry with workout totals + lifestyle averages
  - N entries, one per modality present in that period

Runs AFTER the workouts sync.
"""

from __future__ import annotations

import logging
from collections import Counter
from datetime import date, timedelta

from notion_client import Client as NotionClient

from garmin_to_notion.config import Settings
from garmin_to_notion.notion_helpers import fetch_all_pages, get_prop

logger = logging.getLogger(__name__)


def _parse_duration_minutes(duration_str: str) -> float:
    """Parse duration string like '1h 23m 45s' or '45:30' into minutes."""
    if not duration_str or not duration_str.strip():
        return 0.0

    text = duration_str.strip()

    if "h" in text or "m" in text or "s" in text:
        hours = minutes = seconds = 0
        parts = text.replace("h", "h ").replace("m", "m ").replace("s", "s ").split()
        for part in parts:
            if part.endswith("h"):
                hours = int(part[:-1])
            elif part.endswith("m"):
                minutes = int(part[:-1])
            elif part.endswith("s"):
                seconds = int(part[:-1])
        return hours * 60 + minutes + seconds / 60

    if ":" in text:
        segments = text.split(":")
        if len(segments) == 3:
            return int(segments[0]) * 60 + int(segments[1]) + int(segments[2]) / 60
        if len(segments) == 2:
            return int(segments[0]) + int(segments[1]) / 60

    return 0.0


def _format_minutes(minutes: float) -> str:
    """Format minutes as 'Xh Ym' string."""
    if minutes <= 0:
        return ""
    h = int(minutes) // 60
    m = int(minutes) % 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def _month_range(d: date) -> tuple[date, date, str]:
    """Return (start, end, label) for the month containing date d."""
    start = d.replace(day=1)
    if d.month == 12:
        end = d.replace(day=31)
    else:
        end = d.replace(month=d.month + 1, day=1) - timedelta(days=1)
    label = f"{d.strftime('%B')} {d.year}"
    return start, end, label


def _year_range(d: date) -> tuple[date, date, str]:
    """Return (start, end, label) for the year containing date d."""
    start = date(d.year, 1, 1)
    end = date(d.year, 12, 31)
    label = str(d.year)
    return start, end, label


def _compute_lifestyle_averages(
    notion: NotionClient,
    settings: Settings,
) -> dict[tuple[str, str], dict]:
    """Compute avg sleep, resting HR, steps, and step goal % per period."""
    averages: dict[tuple[str, str], dict] = {}

    # --- Steps ---
    if settings.steps_db_id:
        steps_pages = fetch_all_pages(notion, settings.steps_db_id)
        steps_by_period: dict[tuple[str, str], list[dict]] = {}
        for page in steps_pages:
            props = page["properties"]
            date_str = get_prop(props, "Date", "date")
            steps = get_prop(props, "Steps", "number") or 0
            goal = get_prop(props, "Goal", "number") or 0
            if not date_str:
                continue
            d = date.fromisoformat(date_str[:10])
            for period, range_fn in [("Month", _month_range), ("Year", _year_range)]:
                _, _, label = range_fn(d)
                key = (period, label)
                steps_by_period.setdefault(key, []).append(
                    {"steps": steps, "goal": goal}
                )

        for key, values in steps_by_period.items():
            total_days = len(values)
            avg_steps = round(sum(v["steps"] for v in values) / total_days)
            goal_days = sum(1 for v in values if v["goal"] > 0)
            goal_hits = sum(
                1 for v in values if v["goal"] > 0 and v["steps"] >= v["goal"]
            )
            goal_pct = round(goal_hits / goal_days * 100) if goal_days > 0 else 0

            bucket = averages.setdefault(key, {})
            bucket["avg_steps"] = avg_steps
            bucket["step_goal_pct"] = goal_pct

    # --- Sleep ---
    if settings.sleep_db_id:
        sleep_pages = fetch_all_pages(notion, settings.sleep_db_id)
        sleep_by_period: dict[tuple[str, str], list[dict]] = {}
        for page in sleep_pages:
            props = page["properties"]
            date_str = get_prop(props, "Date", "date")
            duration_str = get_prop(props, "Duration", "rich_text") or ""
            resting_hr = get_prop(props, "Resting HR", "number") or 0
            score = get_prop(props, "Score", "number") or 0
            if not date_str:
                continue
            d = date.fromisoformat(date_str[:10])
            duration_min = _parse_duration_minutes(duration_str)
            for period, range_fn in [("Month", _month_range), ("Year", _year_range)]:
                _, _, label = range_fn(d)
                key = (period, label)
                sleep_by_period.setdefault(key, []).append(
                    {"duration_min": duration_min, "resting_hr": resting_hr, "score": score}
                )

        for key, values in sleep_by_period.items():
            durations = [v["duration_min"] for v in values if v["duration_min"] > 0]
            hrs = [v["resting_hr"] for v in values if v["resting_hr"] > 0]

            scores = [v["score"] for v in values if v["score"] > 0]

            bucket = averages.setdefault(key, {})
            if durations:
                bucket["avg_sleep_min"] = sum(durations) / len(durations)
            if hrs:
                bucket["avg_resting_hr"] = round(sum(hrs) / len(hrs))
            if scores:
                bucket["avg_sleep_score"] = round(sum(scores) / len(scores))

    return averages


def _build_summaries(workouts: list[dict]) -> list[dict]:
    """Group workouts into month/year buckets, then aggregate All + per-modality."""
    records: list[dict] = []
    for w in workouts:
        props = w["properties"]
        date_str = get_prop(props, "Date", "date")
        if not date_str:
            continue

        d = date.fromisoformat(date_str[:10])
        modality = get_prop(props, "Modality", "select") or "Other"
        duration_str = get_prop(props, "Duration", "rich_text") or ""
        distance = get_prop(props, "Distance (km)", "number") or 0
        calories = get_prop(props, "Calories", "number") or 0
        avg_hr = get_prop(props, "Avg HR", "number") or 0

        records.append({
            "date": d,
            "modality": modality,
            "duration_min": _parse_duration_minutes(duration_str),
            "distance": distance,
            "calories": calories,
            "avg_hr": avg_hr,
        })

    buckets: dict[tuple[str, str], dict] = {}
    for rec in records:
        for period, range_fn in [("Month", _month_range), ("Year", _year_range)]:
            start, end, label = range_fn(rec["date"])
            key = (period, label)
            if key not in buckets:
                buckets[key] = {"start": start, "end": end, "records": []}
            buckets[key]["records"].append(rec)

    summaries: list[dict] = []
    for (period, label), bucket in buckets.items():
        recs = bucket["records"]
        start = bucket["start"]
        end = bucket["end"]

        total_workouts = len(recs)
        total_duration = round(sum(r["duration_min"] for r in recs))
        total_distance = round(sum(r["distance"] for r in recs), 1)
        total_calories = round(sum(r["calories"] for r in recs))
        active_days = len(set(r["date"] for r in recs))

        modality_counts = Counter(r["modality"] for r in recs)
        top_modality = modality_counts.most_common(1)[0][0] if modality_counts else "N/A"
        breakdown = " / ".join(f"{m}: {c}" for m, c in modality_counts.most_common())

        weeks_in_period = max(1, ((end - start).days + 1) / 7)
        avg_per_week = round(total_workouts / weeks_in_period, 1)

        hr_values = [r["avg_hr"] for r in recs if r["avg_hr"] > 0]
        avg_hr = round(sum(hr_values) / len(hr_values)) if hr_values else 0

        summaries.append({
            "name": label,
            "period": period,
            "modality": "All",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "total_workouts": total_workouts,
            "total_duration": total_duration,
            "total_distance": total_distance,
            "total_calories": total_calories,
            "top_modality": top_modality,
            "breakdown": breakdown,
            "avg_per_week": avg_per_week,
            "active_days": active_days,
            "avg_hr": avg_hr,
        })

        by_modality: dict[str, list[dict]] = {}
        for r in recs:
            by_modality.setdefault(r["modality"], []).append(r)

        for modality, mod_recs in by_modality.items():
            mod_workouts = len(mod_recs)
            mod_duration = round(sum(r["duration_min"] for r in mod_recs))
            mod_distance = round(sum(r["distance"] for r in mod_recs), 1)
            mod_calories = round(sum(r["calories"] for r in mod_recs))
            mod_avg = round(mod_workouts / weeks_in_period, 1)

            mod_hr_values = [r["avg_hr"] for r in mod_recs if r["avg_hr"] > 0]
            mod_avg_hr = round(sum(mod_hr_values) / len(mod_hr_values)) if mod_hr_values else 0

            summaries.append({
                "name": label,
                "period": period,
                "modality": modality,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "total_workouts": mod_workouts,
                "total_duration": mod_duration,
                "total_distance": mod_distance,
                "total_calories": mod_calories,
                "top_modality": modality,
                "breakdown": "",
                "avg_per_week": mod_avg,
                "active_days": 0,
                "avg_hr": mod_avg_hr,
            })

    return summaries


def _summary_exists(
    notion: NotionClient,
    db_id: str,
    start_date: str,
    period: str,
    modality: str,
) -> dict | None:
    """Check if a summary entry already exists by Start date + period + modality."""
    query = notion.databases.query(
        database_id=db_id,
        filter={
            "and": [
                {"property": "Start", "date": {"equals": start_date}},
                {"property": "Period", "select": {"equals": period}},
                {"property": "Modality", "select": {"equals": modality}},
            ]
        },
    )
    return query["results"][0] if query["results"] else None


def _build_properties(summary: dict) -> dict:
    """Build Notion properties from a summary dict."""
    return {
        "Name": {"title": [{"text": {"content": summary["name"]}}]},
        "Period": {"select": {"name": summary["period"]}},
        "Modality": {"select": {"name": summary["modality"]}},
        "Start": {"date": {"start": summary["start"]}},
        "End": {"date": {"start": summary["end"]}},
        "Total Workouts": {"number": summary["total_workouts"]},
        "Total Duration (min)": {"number": summary["total_duration"]},
        "Total Distance (km)": {"number": summary["total_distance"]},
        "Total Calories": {"number": summary["total_calories"]},
        "Top Modality": {"rich_text": [{"text": {"content": summary["top_modality"]}}]},
        "Breakdown": {"rich_text": [{"text": {"content": summary["breakdown"]}}]},
        "Avg per Week": {"number": summary["avg_per_week"]},
        "Active Days": {"number": summary.get("active_days") or None},
        "Avg HR": {"number": summary.get("avg_hr") or None},
        "Avg Sleep": {"rich_text": [{"text": {"content": summary.get("avg_sleep", "")}}]},
        "Avg Sleep Score": {"number": summary.get("avg_sleep_score") or None},
        "Avg Resting HR": {"number": summary.get("avg_resting_hr") or None},
        "Avg Steps": {"number": summary.get("avg_steps") or None},
        "Step Goal %": {"number": summary.get("step_goal_pct") or None},
    }


def sync_summary(notion: NotionClient, settings: Settings) -> None:
    """Sync aggregated summaries from Workouts to Summary database."""
    if not settings.summary_db_id:
        logger.info("No summary database configured, skipping")
        return

    if not settings.workouts_db_id:
        logger.info("No workouts database configured, cannot build summaries")
        return

    logger.info("Fetching workouts for summary aggregation...")
    workouts = fetch_all_pages(notion, settings.workouts_db_id)
    logger.info("Found %d workouts to aggregate", len(workouts))

    summaries = _build_summaries(workouts)
    logger.info("Generated %d summary entries (month/year x modality)", len(summaries))

    lifestyle = _compute_lifestyle_averages(notion, settings)
    logger.info("Computed lifestyle averages for %d periods", len(lifestyle))

    for summary in summaries:
        if summary["modality"] == "All":
            key = (summary["period"], summary["name"])
            avgs = lifestyle.get(key, {})
            avg_sleep_min = avgs.get("avg_sleep_min", 0)
            summary["avg_sleep"] = _format_minutes(avg_sleep_min) if avg_sleep_min else ""
            summary["avg_resting_hr"] = avgs.get("avg_resting_hr", 0)
            summary["avg_sleep_score"] = avgs.get("avg_sleep_score", 0)
            summary["avg_steps"] = avgs.get("avg_steps", 0)
            summary["step_goal_pct"] = avgs.get("step_goal_pct", 0)

    created, updated = 0, 0

    for summary in summaries:
        props = _build_properties(summary)
        existing = _summary_exists(
            notion,
            settings.summary_db_id,
            summary["start"],
            summary["period"],
            summary["modality"],
        )

        if existing:
            notion.pages.update(page_id=existing["id"], properties=props)
            updated += 1
        else:
            notion.pages.create(
                parent={"database_id": settings.summary_db_id},
                properties=props,
            )
            created += 1

    logger.info(
        "Summary sync complete: %d created, %d updated",
        created, updated,
    )
