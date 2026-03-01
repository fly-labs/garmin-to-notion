# Notion Template Setup

## Template Structure

```
Fitness Tracker  🏋️
│
├── 👋 Welcome callout
│
├── Activity Summary    (Overview, This Month, YTD, Yearly, Monthly Trend, Sport Distribution)
├── Workouts            (Recent 30d, All, By Modality, Calendar)
├── Daily Steps         (Calendar, Recent 30d, All)
├── Sleep               (Calendar, Recent 30d, All, Sleep Score Trend)
├── ─── Raw Data ───
├── Activities          (Recent 30d, All, By Type, Activity Heatmap)
└── Personal Records    (Table, Gallery)
```

---

## Notion AI Prompts

| File | Use case |
|---|---|
| `docs/notion-ai-prompt.txt` | Create full template from scratch |
| `docs/notion-ai-update-prompt.txt` | Update existing template |

Copy the full contents and paste into Notion AI.

---

## After Running the Prompt

### 1. Convert date filters to relative

The prompt uses absolute dates (e.g. `is on or after 2025-03-01`) because Notion AI can't set relative filters. Convert them manually:

| View | Change filter to |
|---|---|
| Activity Summary → Overview | Start → is within → **Past year** |
| Activity Summary → This Month | Start → is within → **This month** |
| Activity Summary → Year to Date | Start → is within → **This year** |
| Activity Summary → Monthly Trend | Start → is within → **Past year** |
| Activity Summary → Sport Distribution | Start → is within → **This year** |
| Workouts → Recent | Date → is within → **Past month** |
| Daily Steps → Recent | Date → is within → **Past month** |
| Sleep → Recent | Date → is within → **Past month** |
| Sleep → Sleep Score Trend | Date → is within → **Past month** |
| Activities → Recent | Date → is within → **Past month** |

### 2. Verify Modality select colors

Match Activity Summary and Workouts DB colors (All=gray, Running=green, etc.)

### 3. Connect the integration

1. [notion.so/profile/integrations](https://www.notion.so/profile/integrations) → New integration → "Garmin Sync" → Internal
2. Go to the **Fitness Tracker** page → `...` → Connect to → Garmin Sync (all inline databases inherit access automatically)
3. Configure secrets in GitHub or `.env` locally (see `.env.example`)

### 4. Run the sync

```bash
python -m garmin_to_notion all
```

---

## Activity Summary Views

| View | Type | Shows | Filter |
|---|---|---|---|
| **Overview** (default) | Table | Last 12 months, all sports combined | Period=Month, Modality=All, Start within past year |
| **This Month** | Table | Current month per sport + total | Period=Month, Start within this month |
| **Year to Date** | Table | Current year per sport + total | Period=Year, Start within this year |
| **Yearly** | Table | Year-over-year totals | Period=Year, Modality=All |
| **Monthly Trend** | Bar chart | Workout volume per month (past year) | Period=Month, Modality=All, Start within past year. X-axis=Start (Date) ascending |
| **Sport Distribution** | Donut chart | Workout split by sport (current year) | Period=Year, Start within this year, Modality≠All |

> **Note:** "This Month" and "Year to Date" views include an "All" row at the top that serves as the consolidated total across all sports. Sorted by Total Workouts descending to keep the total first.

### Chart Configuration

| Chart | X-axis | Y-axis | Sort |
|---|---|---|---|
| **Monthly Trend** | Start (Date) | Total Workouts (Number, NOT Count) | X ascending |
| **Sleep Score Trend** | Date (Date) | Score (Number, NOT Count) | X ascending |
| **Sport Distribution** | — | Total Workouts (Number, NOT Count) | Slice by Modality |

### Sleep Views

| View | Type | Shows |
|---|---|---|
| **Calendar** (default) | Calendar | Monthly calendar |
| **Recent** | Table | Past 30 days |
| **All Nights** | Table | All sleep data |
| **Sleep Score Trend** | Line chart | Sleep quality score over past month |

### Activities Views

| View | Type | Shows |
|---|---|---|
| **Recent** (default) | Table | Past 30 days |
| **All Activities** | Table | All activities |
| **By Type** | Board | Grouped by activity type |
| **Activity Heatmap** | Board | Grouped by Day of Week, sorted by Hour Block |

### Activity Summary Properties

| Property | Type | "All" entries | Per-modality |
|---|---|---|---|
| Total Workouts | Number | Total across all sports | Sport-specific |
| Active Days | Number | Unique days with workouts | — |
| Total Duration (min) | Number | Sum all sports | Sport-specific |
| Total Distance (km) | Number | Sum all sports | Sport-specific |
| Total Calories | Number | Sum all sports | Sport-specific |
| Avg per Week | Number | Workouts/week | Sport-specific |
| Avg HR | Number | Avg heart rate across workouts | Sport-specific |
| Avg Sleep | Rich text | e.g. "7h 30m" | — |
| Avg Sleep Score | Number | Sleep quality 0-100 | — |
| Avg Resting HR | Number | e.g. 56 bpm | — |
| Avg Steps | Number | e.g. 8,450 | — |
| Step Goal % | Number | e.g. 73 | — |

### Supported Modalities

Running, Outdoor Cycling, Indoor Cycling, Swimming, Walking, Strength Training, BJJ, HIIT, Yoga, Pilates, Sauna, Crossfit, Racquet Sports, Team Sports, Combat Sports, Winter Sports, Water Sports, Climbing, Golf, Dance, Multi Sport, Other

---

## Migration Note

If upgrading from a previous version:
1. Rename "Summary" database to "Activity Summary"
2. Run the update prompt (`docs/notion-ai-update-prompt.txt`) in Notion AI to add new properties and views
3. Re-run: `python -m garmin_to_notion all`
4. Activities will be updated with correct timezones, emoji icons, and heatmap properties
5. Sleep entries with missing scores will be repaired automatically
6. Activity Summary entries are matched by Start date — Name format changes update in-place (no duplicates)
