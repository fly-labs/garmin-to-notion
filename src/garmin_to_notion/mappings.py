"""All mapping constants for activity types, icons, modalities, and records."""

# ---------------------------------------------------------------------------
# Activity Emojis (used by Activities sync)
# Maps activity subtype/type to native Notion emoji icons
# ---------------------------------------------------------------------------
ACTIVITY_EMOJIS: dict[str, str] = {
    # Running
    "Running": "\U0001f3c3",
    "Treadmill Running": "\U0001f3c3",
    "Street Running": "\U0001f3c3",
    "Indoor Running": "\U0001f3c3",
    "Trail Running": "\U0001f3d4\ufe0f",
    "Track Running": "\U0001f3c3",
    "Ultra Running": "\U0001f3c3",
    # Cycling
    "Cycling": "\U0001f6b4",
    "Indoor Cycling": "\U0001f6b4",
    "Mountain Biking": "\U0001f6b5",
    "Gravel Cycling": "\U0001f6b4",
    "E Biking": "\U0001f6b4",
    "Cyclocross": "\U0001f6b4",
    "Virtual Ride": "\U0001f6b4",
    # Swimming
    "Swimming": "\U0001f3ca",
    "Lap Swimming": "\U0001f3ca",
    "Open Water Swimming": "\U0001f30a",
    # Walking
    "Walking": "\U0001f6b6",
    "Hiking": "\U0001f97e",
    "Speed Walking": "\U0001f6b6",
    "Casual Walking": "\U0001f6b6",
    "Stair Climbing": "\U0001f6b6",
    # Strength & Fitness
    "Strength Training": "\U0001f3cb\ufe0f",
    "Barre": "\U0001f3cb\ufe0f",
    "Functional Training": "\U0001f3cb\ufe0f",
    "Crossfit": "\U0001f3cb\ufe0f",
    "HIIT": "\U0001f525",
    "Cardio": "\U0001f4aa",
    "Indoor Cardio": "\U0001f4aa",
    "Elliptical": "\U0001f3c3",
    "Jump Rope": "\u23ed\ufe0f",
    # Yoga & Mindfulness
    "Yoga": "\U0001f9d8",
    "Pilates": "\U0001f9d8",
    "Stretching": "\U0001f938",
    "Meditation": "\U0001f9d8",
    "Breathwork": "\U0001fac1",
    # Rowing
    "Rowing": "\U0001f6a3",
    "Indoor Rowing": "\U0001f6a3",
    # Racquet Sports
    "Tennis": "\U0001f3be",
    "Padel": "\U0001f3be",
    "Badminton": "\U0001f3f8",
    "Pickleball": "\U0001f3d3",
    "Squash": "\U0001f3be",
    "Table Tennis": "\U0001f3d3",
    # Team Sports
    "Soccer": "\u26bd",
    "Basketball": "\U0001f3c0",
    "Volleyball": "\U0001f3d0",
    "Football": "\U0001f3c8",
    "Rugby": "\U0001f3c9",
    "Hockey": "\U0001f3d2",
    # Combat
    "Mixed Martial Arts": "\U0001f94b",
    "Boxing": "\U0001f94a",
    "Kickboxing": "\U0001f94a",
    # Winter Sports
    "Skiing": "\u26f7\ufe0f",
    "Resort Skiing Snowboarding": "\u26f7\ufe0f",
    "Snowboarding": "\U0001f3c2",
    "Cross Country Skiing": "\u26f7\ufe0f",
    "Snowshoeing": "\U0001f97e",
    "Ice Skating": "\u26f8\ufe0f",
    # Water Sports
    "Kayaking": "\U0001f6f6",
    "Stand Up Paddleboarding": "\U0001f3c4",
    "Surfing": "\U0001f3c4",
    # Climbing
    "Rock Climbing": "\U0001f9d7",
    "Bouldering": "\U0001f9d7",
    "Indoor Climbing": "\U0001f9d7",
    "Mountaineering": "\U0001f9d7",
    # Other
    "Golf": "\u26f3",
    "Skateboarding": "\U0001f6f9",
    "Dance": "\U0001f483",
    "Horseback Riding": "\U0001f3c7",
    "Multi Sport": "\U0001f3c5",
    "Triathlon": "\U0001f3c5",
    "Other": "\U0001f3c5",
}

# ---------------------------------------------------------------------------
# Personal Records: typeId -> display name
# ---------------------------------------------------------------------------
RECORD_TYPE_NAMES: dict[int, str] = {
    1: "1K",
    2: "1mi",
    3: "5K",
    4: "10K",
    7: "Longest Run",
    8: "Longest Ride",
    9: "Total Ascent",
    10: "Max Avg Power (20 min)",
    12: "Most Steps in a Day",
    13: "Most Steps in a Week",
    14: "Most Steps in a Month",
    15: "Longest Goal Streak",
}

# ---------------------------------------------------------------------------
# Personal Records: emoji icons
# ---------------------------------------------------------------------------
RECORD_ICONS: dict[str, str] = {
    "1K": "\U0001f947",
    "1mi": "\u26a1",
    "5K": "\U0001f45f",
    "10K": "\u2b50",
    "Longest Run": "\U0001f3c3",
    "Longest Ride": "\U0001f6b4",
    "Total Ascent": "\U0001f6b5",
    "Max Avg Power (20 min)": "\U0001f50b",
    "Most Steps in a Day": "\U0001f463",
    "Most Steps in a Week": "\U0001f6b6",
    "Most Steps in a Month": "\U0001f4c5",
    "Longest Goal Streak": "\u2714\ufe0f",
    "Other": "\U0001f3c5",
}

# ---------------------------------------------------------------------------
# Personal Records: Unsplash cover images
# ---------------------------------------------------------------------------
RECORD_COVERS: dict[str, str] = {
    "1K": "https://images.unsplash.com/photo-1526676537331-7747bf8278fc?w=4800",
    "1mi": "https://images.unsplash.com/photo-1638183395699-2c0db5b6afbb?w=4800",
    "5K": "https://images.unsplash.com/photo-1571008887538-b36bb32f4571?w=4800",
    "10K": "https://images.unsplash.com/photo-1529339944280-1a37d3d6fa8c?w=4800",
    "Longest Run": "https://images.unsplash.com/photo-1532383282788-19b341e3c422?w=4800",
    "Longest Ride": "https://images.unsplash.com/photo-1471506480208-91b3a4cc78be?w=4800",
    "Max Avg Power (20 min)": "https://images.unsplash.com/photo-1591741535018-d042766c62eb?w=4800",
    "Most Steps in a Day": "https://images.unsplash.com/photo-1476480862126-209bfaa8edc8?w=4800",
    "Most Steps in a Week": "https://images.unsplash.com/photo-1602174865963-9159ed37e8f1?w=4800",
    "Most Steps in a Month": "https://images.unsplash.com/photo-1580058572462-98e2c0e0e2f0?w=4800",
    "Longest Goal Streak": "https://images.unsplash.com/photo-1477332552946-cfb384aeaf1c?w=4800",
}

DEFAULT_COVER = "https://images.unsplash.com/photo-1471506480208-91b3a4cc78be?w=4800"

# ---------------------------------------------------------------------------
# Workouts: Garmin Activity Type / Subactivity Type -> Modality
# Subactivity (more specific) is checked first, then Activity Type
# ---------------------------------------------------------------------------
MODALITY_MAP: dict[str, str] = {
    # Subactivity Type mappings (checked first)
    "Treadmill Running": "Running",
    "Street Running": "Running",
    "Indoor Running": "Running",
    "Trail Running": "Running",
    "Track Running": "Running",
    "Ultra Running": "Running",
    "Indoor Cycling": "Indoor Cycling",
    "Virtual Ride": "Indoor Cycling",
    "Mountain Biking": "Outdoor Cycling",
    "Gravel Cycling": "Outdoor Cycling",
    "E Biking": "Outdoor Cycling",
    "Cyclocross": "Outdoor Cycling",
    "Casual Walking": "Walking",
    "Speed Walking": "Walking",
    "Stair Climbing": "Walking",
    "Strength Training": "Strength Training",
    "Strength": "Strength Training",
    "Functional Training": "Strength Training",
    "Barre": "Strength Training",
    "Pilates": "Pilates",
    "Yoga": "Yoga",
    "Lap Swimming": "Swimming",
    "Open Water Swimming": "Swimming",
    "Mixed Martial Arts": "BJJ",
    "Hiit": "HIIT",
    "Crossfit": "Crossfit",
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
    "Boxing": "Combat Sports",
    "Kickboxing": "Combat Sports",
    # Winter
    "Skiing": "Winter Sports",
    "Resort Skiing Snowboarding": "Winter Sports",
    "Snowboarding": "Winter Sports",
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
    "Golf": "Golf",
    "Dance": "Dance",
    "Multi Sport": "Multi Sport",
    "Triathlon": "Multi Sport",
    # Activity Type mappings (fallback)
    "Running": "Running",
    "Cycling": "Outdoor Cycling",
    "BJJ": "BJJ",
    "HIIT": "HIIT",
    "Swimming": "Swimming",
    "Walking": "Walking",
    "Yoga/Pilates": "Yoga",
    "Racquet Sports": "Racquet Sports",
    "Team Sports": "Team Sports",
    "Combat Sports": "Combat Sports",
    "Winter Sports": "Winter Sports",
    "Water Sports": "Water Sports",
    "Climbing": "Climbing",
    "Multi Sport": "Multi Sport",
}

# ---------------------------------------------------------------------------
# Workouts: Aerobic Effect -> Intensity
# ---------------------------------------------------------------------------
INTENSITY_MAP: dict[str, str] = {
    "Overreaching": "Maximum",
    "Highly Impacting": "Hard",
    "Impacting": "Moderate",
    "Improving": "Moderate",
    "Maintaining": "Moderate",
    "Some Benefit": "Easy",
    "Recovery": "Easy",
    "No Benefit": "Easy",
    "Unknown": "Moderate",
}

# ---------------------------------------------------------------------------
# Workouts: Activity Name overrides (for custom Garmin activities)
# ---------------------------------------------------------------------------
NAME_OVERRIDE_MAP: dict[str, str] = {
    "Sauna": "Sauna",
}

# ---------------------------------------------------------------------------
# Workouts: Modalities where Easy intensity doesn't apply -> minimum
# ---------------------------------------------------------------------------
INTENSITY_FLOOR: dict[str, str] = {
    "HIIT": "Moderate",
    "BJJ": "Moderate",
}

# ---------------------------------------------------------------------------
# Workouts: Skip these activity types (not real workouts)
# ---------------------------------------------------------------------------
SKIP_TYPES: set[str] = {"Breathwork", "Relaxation", "Meditation"}
