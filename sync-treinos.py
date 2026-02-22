"""
sync-treinos.py
Reads from the Activities database (Fitness Tracker Template) and
copies/updates entries into the Treinos database.

Runs AFTER garmin-activities.py in the same workflow.

FIX (2025-02): Changed unique key from Notion page ID (which changes on every
garmin-activities.py run) to a composite fingerprint of date + activity name.
This prevents duplicates when Activities pages are recreated.
"""
import os
from dotenv import load_dotenv
from notion_client import Client as NotionClient

# Mapping: Garmin Activity Type / Subactivity Type -> Treinos Modalidade
# Subactivity (more specific) is checked first, then Activity Type
MODALIDADE_MAP = {
    # Subactivity Type mappings (checked first - more specific)
    "Treadmill Running": "Corrida na Esteira",
    "Street Running": "Corrida",
    "Indoor Running": "Corrida na Esteira",
    "Indoor Cycling": "Bike Indoor",
    "Casual Walking": "Caminhada",
    "Speed Walking": "Caminhada",
    "Strength Training": "Treino de Força",
    "Strength": "Treino de Força",
    "Stair Climbing": "Caminhada",
    "Pilates": "Fisioterapia",  # Luiz uses Pilates on Garmin for Fisioterapia
    "Yoga": "Fisioterapia",
    "Lap Swimming": "Natação",
    "Open Water Swimming": "Natação",
    "Virtual Ride": "Bike Indoor",
    "Mixed Martial Arts": "BJJ",
    "Hiit": "HIIT",
    # Activity Type mappings (fallback)
    "Running": "Corrida",
    "Cycling": "Bike Indoor",
    "BJJ": "BJJ",
    "Swimming": "Natação",
    "Walking": "Caminhada",
    "Yoga/Pilates": "Fisioterapia",
}

# Aerobic Effect -> Intensidade
INTENSIDADE_MAP = {
    "Overreaching": "Intenso",
    "Highly Impacting": "Intenso",
    "Impacting": "Moderado",
    "Improving": "Moderado",
    "Maintaining": "Moderado",
    "Some Benefit": "Leve",
    "Recovery": "Recovery",
    "No Benefit": "Leve",
    "Unknown": "Moderado",
}

# Activity Name overrides (for custom Garmin activities where type is "Other")
NAME_OVERRIDE_MAP = {
    "Sauna": "Sauna",
}

# Modalidades where "Recovery" and "Leve" don't make sense - override to minimum
INTENSIDADE_FLOOR = {
    "HIIT": "Moderado",
    "BJJ": "Moderado",
}

# Skip these - not real workouts
SKIP_TYPES = {"Breathwork", "Relaxation", "Meditation"}


def get_prop(props, name, prop_type):
    """Safely extract a property value from Notion page properties."""
    prop = props.get(name)
    if not prop:
        return None
    if prop_type == "number":
        return prop.get("number")
    elif prop_type == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else None
    elif prop_type == "title":
        title = prop.get("title", [])
        return title[0]["text"]["content"] if title else ""
    elif prop_type == "rich_text":
        rt = prop.get("rich_text", [])
        return rt[0]["text"]["content"] if rt else ""
    elif prop_type == "date":
        date = prop.get("date")
        return date.get("start") if date else None
    elif prop_type == "checkbox":
        return prop.get("checkbox", False)
    return None


def get_modalidade(activity_type, subactivity_type, activity_name=""):
    """Determine Modalidade. Name override > Subtype > Type."""
    if activity_name and activity_name in NAME_OVERRIDE_MAP:
        return NAME_OVERRIDE_MAP[activity_name]
    if subactivity_type and subactivity_type in MODALIDADE_MAP:
        return MODALIDADE_MAP[subactivity_type]
    if activity_type and activity_type in MODALIDADE_MAP:
        return MODALIDADE_MAP[activity_type]
    return "Outro"


def get_intensidade(aerobic_effect):
    return INTENSIDADE_MAP.get(aerobic_effect, "Moderado")


def apply_intensidade_floor(modalidade, intensidade):
    """Override intensidade if it's below the floor for certain modalidades."""
    floor = INTENSIDADE_FLOOR.get(modalidade)
    if not floor:
        return intensidade
    rank = {"Recovery": 0, "Leve": 1, "Moderado": 2, "Intenso": 3}
    if rank.get(intensidade, 2) < rank.get(floor, 2):
        return floor
    return intensidade


def get_title(activity_name, modalidade):
    generic = {"unnamed activity", "unknown", ""}
    if activity_name.lower().strip() in generic:
        return modalidade
    return activity_name


def make_fingerprint(date_str, title):
    """Composite key used to detect duplicates: date (YYYY-MM-DD) + title."""
    date_part = (date_str or "")[:10]
    return f"{date_part}|{title}"


def treino_exists(notion, db_id, date_str, title):
    """
    Check if a treino already exists by date + title composite key.
    Queries the Garmin ID field (which stores our fingerprint) for an exact match.
    Falls back to querying date + title directly in case of legacy records.
    """
    fingerprint = make_fingerprint(date_str, title)

    # Primary: look up by fingerprint stored in Garmin ID field
    query = notion.databases.query(
        database_id=db_id,
        filter={"property": "Garmin ID", "rich_text": {"equals": fingerprint}}
    )
    if query["results"]:
        return query["results"][0]

    # Fallback: legacy records may have Notion page ID in Garmin ID — match by date+title
    if date_str:
        date_only = date_str[:10]
        query2 = notion.databases.query(
            database_id=db_id,
            filter={
                "and": [
                    {"property": "Data", "date": {"equals": date_only}},
                    {"property": "Treino", "title": {"equals": title}},
                ]
            }
        )
        if query2["results"]:
            return query2["results"][0]

    return None


def build_properties(activity_page):
    """Build Treinos properties from an Activities page."""
    props = activity_page["properties"]

    activity_type = get_prop(props, "Activity Type", "select") or ""
    subactivity_type = get_prop(props, "Subactivity Type", "select") or ""
    activity_name = get_prop(props, "Activity Name", "title") or ""
    date_start = get_prop(props, "Date", "date")
    duration = get_prop(props, "Duration (min)", "number")
    calories = get_prop(props, "Calories", "number")
    distance = get_prop(props, "Distance (km)", "number")
    avg_pace = get_prop(props, "Avg Pace", "rich_text") or ""
    aerobic_effect = get_prop(props, "Aerobic Effect", "select") or "Unknown"

    modalidade = get_modalidade(activity_type, subactivity_type, activity_name)
    intensidade = get_intensidade(aerobic_effect)
    intensidade = apply_intensidade_floor(modalidade, intensidade)
    title = get_title(activity_name, modalidade)

    treino_props = {
        "Treino": {"title": [{"text": {"content": title}}]},
        "Modalidade": {"select": {"name": modalidade}},
        "Intensidade": {"select": {"name": intensidade}},
    }

    if date_start:
        treino_props["Data"] = {"date": {"start": date_start}}
    if duration and duration > 0:
        treino_props["Duração (min)"] = {"number": round(duration, 1)}
    if distance and distance > 0:
        treino_props["Distância (km)"] = {"number": round(distance, 2)}
    if calories and calories > 0:
        treino_props["Calorias"] = {"number": round(calories)}
    if avg_pace and avg_pace.strip():
        treino_props["Pace Médio"] = {"rich_text": [{"text": {"content": avg_pace}}]}

    return treino_props, title, date_start


def fetch_all_pages(notion, database_id):
    """Fetch all pages from a database with pagination."""
    pages = []
    has_more = True
    cursor = None
    while has_more:
        kwargs = {"database_id": database_id, "page_size": 100}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = notion.databases.query(**kwargs)
        pages.extend(resp["results"])
        has_more = resp.get("has_more", False)
        cursor = resp.get("next_cursor")
    return pages


def main():
    load_dotenv()

    notion_token = os.getenv("NOTION_TOKEN")
    activities_db_id = os.getenv("NOTION_DB_ID")
    treinos_db_id = os.getenv("NOTION_TREINOS_DB_ID")

    if not treinos_db_id:
        print("NOTION_TREINOS_DB_ID not set, skipping treinos sync")
        return

    notion = NotionClient(auth=notion_token)

    print("Fetching activities from Fitness Tracker...")
    activities = fetch_all_pages(notion, activities_db_id)
    print(f"Found {len(activities)} activities")

    created = 0
    updated = 0
    skipped = 0

    for activity in activities:
        props = activity["properties"]
        activity_type = get_prop(props, "Activity Type", "select") or ""
        subactivity_type = get_prop(props, "Subactivity Type", "select") or ""

        # Skip non-workout types
        if activity_type in SKIP_TYPES or subactivity_type in SKIP_TYPES:
            skipped += 1
            continue

        treino_props, title, date_start = build_properties(activity)

        existing = treino_exists(notion, treinos_db_id, date_start, title)

        if existing:
            notion.pages.update(page_id=existing["id"], properties=treino_props)
            updated += 1
        else:
            fingerprint = make_fingerprint(date_start, title)
            treino_props["Fonte"] = {"select": {"name": "Garmin"}}
            treino_props["Garmin ID"] = {"rich_text": [{"text": {"content": fingerprint}}]}
            notion.pages.create(
                parent={"database_id": treinos_db_id},
                properties=treino_props
            )
            created += 1
            print(f"  Created: {title} ({date_start})")

    print(f"\nTreinos sync done: {created} created, {updated} updated, {skipped} skipped")


if __name__ == "__main__":
    main()
