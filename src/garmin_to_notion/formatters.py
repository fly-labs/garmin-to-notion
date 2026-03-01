"""Formatting functions for Garmin data -> Notion display values."""

from __future__ import annotations

from datetime import datetime, timezone, UTC
from zoneinfo import ZoneInfo


def format_activity_type(
    activity_type: str,
    activity_name: str = "",
) -> tuple[str, str]:
    """Map a Garmin activity type key to (main_type, subtype) for Notion."""
    formatted = activity_type.replace("_", " ").title() if activity_type else "Unknown"
    activity_subtype = formatted
    main_type = formatted

    type_map = {
        # Running variants
        "Treadmill Running": "Running",
        "Street Running": "Running",
        "Indoor Running": "Running",
        "Trail Running": "Running",
        "Track Running": "Running",
        "Ultra Running": "Running",
        # Walking variants (includes Hiking)
        "Hiking": "Walking",
        # Cycling variants
        "Indoor Cycling": "Cycling",
        "Mountain Biking": "Cycling",
        "Gravel Cycling": "Cycling",
        "E Biking": "Cycling",
        "Cyclocross": "Cycling",
        "Virtual Ride": "Cycling",
        # Swimming variants
        "Lap Swimming": "Swimming",
        "Open Water Swimming": "Swimming",
        # Rowing variants
        "Indoor Rowing": "Rowing",
        # Walking variants
        "Speed Walking": "Walking",
        "Casual Walking": "Walking",
        "Stair Climbing": "Walking",
        # Strength / Fitness
        "Strength Training": "Strength",
        "Barre": "Strength",
        "Functional Training": "Strength",
        "Hiit": "HIIT",
        "Indoor Cardio": "Cardio",
        "Elliptical": "Cardio",
        # Racquet sports
        "Tennis": "Racquet Sports",
        "Padel": "Racquet Sports",
        "Badminton": "Racquet Sports",
        "Pickleball": "Racquet Sports",
        "Squash": "Racquet Sports",
        "Table Tennis": "Racquet Sports",
        # Team sports
        "Soccer": "Team Sports",
        "Basketball": "Team Sports",
        "Volleyball": "Team Sports",
        "Football": "Team Sports",
        "Rugby": "Team Sports",
        "Hockey": "Team Sports",
        # Combat
        "Mixed Martial Arts": "Combat Sports",
        "Boxing": "Combat Sports",
        "Kickboxing": "Combat Sports",
        # Winter
        "Resort Skiing Snowboarding": "Winter Sports",
        "Cross Country Skiing": "Winter Sports",
        "Snowshoeing": "Winter Sports",
        "Ice Skating": "Winter Sports",
        # Water
        "Kayaking": "Water Sports",
        "Stand Up Paddleboarding": "Water Sports",
        "Surfing": "Water Sports",
        # Climbing
        "Rock Climbing": "Climbing",
        "Bouldering": "Climbing",
        "Indoor Climbing": "Climbing",
        "Mountaineering": "Climbing",
        # Other
        "Multi Sport": "Multi Sport",
    }

    if formatted == "Rowing V2":
        main_type = "Rowing"
    elif formatted in ("Yoga", "Pilates"):
        main_type = "Yoga/Pilates"
        activity_subtype = formatted

    if formatted in type_map:
        main_type = type_map[formatted]
        activity_subtype = formatted

    # Activity-name overrides
    if activity_name:
        name_lower = activity_name.lower()
        if "meditation" in name_lower:
            return "Meditation", "Meditation"
        if "barre" in name_lower:
            return "Strength", "Barre"
        if "stretch" in name_lower:
            return "Stretching", "Stretching"

    return main_type, activity_subtype


def format_training_message(message: str) -> str:
    """Map a Garmin training effect message prefix to a readable label."""
    messages = {
        "NO_": "No Benefit",
        "MINOR_": "Some Benefit",
        "RECOVERY_": "Recovery",
        "MAINTAINING_": "Maintaining",
        "IMPROVING_": "Improving",
        "IMPACTING_": "Impacting",
        "HIGHLY_": "Highly Impacting",
        "OVERREACHING_": "Overreaching",
    }
    for prefix, label in messages.items():
        if message.startswith(prefix):
            return label
    return message


def format_training_effect(training_effect_label: str) -> str:
    """Convert Garmin's underscored training effect label to title case."""
    return training_effect_label.replace("_", " ").title()


def format_effect_rich(value: float, message: str) -> str:
    """Combine a numeric training effect value and label into rich text.

    Example: format_effect_rich(3.2, "HIGHLY_IMPACTING_AEROBIC") -> "3.2 - Highly Impacting"
    """
    label = format_training_message(message)
    return f"{value:.1f} - {label}"


def format_pace(average_speed: float) -> str:
    """Convert m/s average speed to 'M:SS min/km' pace string."""
    if average_speed <= 0:
        return ""
    pace_min_km = 1000 / (average_speed * 60)
    minutes = int(pace_min_km)
    seconds = int((pace_min_km - minutes) * 60)
    return f"{minutes}:{seconds:02d} min/km"


def gmt_to_local(gmt_string: str, tz: ZoneInfo) -> datetime:
    """Convert a GMT datetime string from Garmin to a local timezone datetime.

    Handles multiple Garmin formats:
      - "2024-01-15 10:30:45"    (activities)
      - "2024-01-15T10:30:45.0"  (personal records)
    """
    return datetime.fromisoformat(gmt_string).replace(tzinfo=UTC).astimezone(tz)


def format_duration(seconds: int | float | None) -> str:
    """Convert seconds to a clean duration string.

    Examples: 2700 -> "45m", 5400 -> "1h 30m", 0 -> "0m"
    """
    total_minutes = int((seconds or 0)) // 60
    hours = total_minutes // 60
    minutes = total_minutes % 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def format_date_for_display(date_str: str | None) -> str:
    """Convert 'YYYY-MM-DD' to 'DD.MM.YYYY' for display."""
    if not date_str:
        return "Unknown"
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")


def timestamp_to_iso(timestamp_ms: int | None) -> str | None:
    """Convert a Garmin millisecond timestamp to an ISO 8601 UTC string."""
    if not timestamp_ms:
        return None
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def timestamp_to_local_time(timestamp_ms: int | None, tz: ZoneInfo) -> str:
    """Convert a Garmin millisecond timestamp to a local 'HH:MM' string."""
    if not timestamp_ms:
        return "Unknown"
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=tz)
    return dt.strftime("%H:%M")


def format_garmin_record_value(
    value: float,
    activity_type: str,
    type_id: int,
) -> tuple[str, str]:
    """Format a Garmin personal record value based on its type.

    Returns (formatted_value, pace_string). Pace is empty for non-pace records.
    """
    if type_id == 1:  # 1K
        total_seconds = round(value)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        formatted = f"{minutes}:{seconds:02d} /km"
        return formatted, formatted

    if type_id == 2:  # 1 mile
        total_seconds = round(value)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        km_seconds = total_seconds / 1.60934
        pm = int(km_seconds // 60)
        ps = int(km_seconds % 60)
        return f"{minutes}:{seconds:02d}", f"{pm}:{ps:02d} /km"

    if type_id == 3:  # 5K
        total_seconds = round(value)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        pace_seconds = total_seconds // 5
        pm = pace_seconds // 60
        ps = pace_seconds % 60
        return f"{minutes}:{seconds:02d}", f"{pm}:{ps:02d} /km"

    if type_id == 4:  # 10K
        total_seconds = round(value)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        if hours > 0:
            formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            formatted = f"{minutes}:{seconds:02d}"
        pace_seconds = total_seconds // 10
        pm = (pace_seconds % 3600) // 60
        ps = pace_seconds % 60
        return formatted, f"{pm}:{ps:02d} /km"

    if type_id in (7, 8):  # Longest Run / Longest Ride
        return f"{value / 1000:.2f} km", ""

    if type_id == 9:  # Total Ascent
        return f"{int(value):,} m", ""

    if type_id == 10:  # Max Avg Power (20 min)
        return f"{round(value)} W", ""

    if type_id in (12, 13, 14):  # Step counts
        return f"{round(value):,}", ""

    if type_id == 15:  # Longest Goal Streak
        return f"{round(value)} days", ""

    # Default: time format
    if int(value // 60) < 60:
        minutes = int(value // 60)
        seconds = round((value / 60 - minutes) * 60, 2)
        return f"{minutes}:{seconds:05.2f}", ""
    else:
        hours = int(value // 3600)
        minutes = int((value % 3600) // 60)
        seconds = round(value % 60, 2)
        return f"{hours}:{minutes:02}:{seconds:05.2f}", ""
