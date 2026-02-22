"""
cleanup-duplicatas-treinos.py

Removes duplicate entries from the Treinos database.

Logic:
- Groups all records by (date YYYY-MM-DD, title, modalidade)
- Within each group, keeps the OLDEST record (first created — most likely the original)
- Archives all others via Notion API (soft delete — recoverable from Trash)

Run ONCE after deploying the fixed sync-treinos.py.
Set DRY_RUN = True first to preview what would be deleted.

Usage:
    DRY_RUN=true python cleanup-duplicatas-treinos.py
    DRY_RUN=false python cleanup-duplicatas-treinos.py
"""
import os
from collections import defaultdict
from dotenv import load_dotenv
from notion_client import Client as NotionClient

DRY_RUN = os.getenv("DRY_RUN", "true").lower() != "false"


def get_prop(props, name, prop_type):
    prop = props.get(name)
    if not prop:
        return None
    if prop_type == "title":
        title = prop.get("title", [])
        return title[0]["text"]["content"] if title else ""
    elif prop_type == "select":
        sel = prop.get("select")
        return sel.get("name") if sel else None
    elif prop_type == "date":
        date = prop.get("date")
        return date.get("start") if date else None
    elif prop_type == "rich_text":
        rt = prop.get("rich_text", [])
        return rt[0]["text"]["content"] if rt else ""
    return None


def fetch_all_pages(notion, database_id):
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


def make_group_key(title, date_str, modalidade):
    """
    Group key for deduplication.
    Uses date (YYYY-MM-DD only) + title + modalidade.
    """
    date_part = (date_str or "unknown")[:10]
    return (date_part, title or "untitled", modalidade or "Outro")


def main():
    load_dotenv()

    notion_token = os.getenv("NOTION_TOKEN")
    treinos_db_id = os.getenv("NOTION_TREINOS_DB_ID")

    if not treinos_db_id:
        print("NOTION_TREINOS_DB_ID not set. Exiting.")
        return

    notion = NotionClient(auth=notion_token)

    print(f"{'[DRY RUN] ' if DRY_RUN else ''}Fetching all Treinos records...")
    pages = fetch_all_pages(notion, treinos_db_id)
    print(f"Total records: {len(pages)}")

    # Group by (date, title, modalidade)
    groups = defaultdict(list)
    for page in pages:
        props = page["properties"]
        title = get_prop(props, "Treino", "title") or ""
        date_str = get_prop(props, "Data", "date") or ""
        modalidade = get_prop(props, "Modalidade", "select") or ""
        key = make_group_key(title, date_str, modalidade)
        groups[key].append(page)

    duplicates_found = 0
    groups_with_dupes = 0
    to_archive = []

    for key, group in groups.items():
        if len(group) <= 1:
            continue

        groups_with_dupes += 1
        date_part, title, modalidade = key

        # Sort by created_time ascending — keep the oldest (index 0)
        group_sorted = sorted(group, key=lambda p: p.get("created_time", ""))
        keep = group_sorted[0]
        discard = group_sorted[1:]

        duplicates_found += len(discard)

        print(f"\n  Group: [{date_part}] {title} ({modalidade}) — {len(group)} records")
        print(f"    KEEP:    {keep['id']} (created {keep.get('created_time', 'unknown')[:19]})")
        for p in discard:
            print(f"    ARCHIVE: {p['id']} (created {p.get('created_time', 'unknown')[:19]})")
            to_archive.append(p)

    print(f"\n{'=' * 60}")
    print(f"Groups with duplicates: {groups_with_dupes}")
    print(f"Total records to archive: {duplicates_found}")

    if duplicates_found == 0:
        print("No duplicates found. Nothing to do.")
        return

    if DRY_RUN:
        print("\n[DRY RUN] No changes made. Set DRY_RUN=false to execute.")
        return

    print("\nArchiving duplicates...")
    archived = 0
    errors = 0

    for page in to_archive:
        try:
            notion.pages.update(page_id=page["id"], archived=True)
            archived += 1
            print(f"  Archived: {page['id']}")
        except Exception as e:
            errors += 1
            print(f"  ERROR archiving {page['id']}: {e}")

    print(f"\nDone: {archived} archived, {errors} errors.")
    print("Records are in Notion Trash and can be restored if needed.")


if __name__ == "__main__":
    main()
