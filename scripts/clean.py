"""
Data Vortex - Round 1: Cleaning pipeline
Reads data/raw/*.csv, applies documented fixes, writes data/processed/*.csv + *.json
plus a cleaning_summary.json describing every change made and why.

Run: python scripts/clean.py
"""
import json
import re
from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)

USERS_IN = RAW_DIR / "Social_Engine_Users.csv"
POSTS_IN = RAW_DIR / "Social_Engine_Posts_Corrupted.csv"


def classify_timestamp_format(value: str) -> str:
    """Identify which of the three known raw timestamp formats a value is in."""
    value = str(value)
    if re.fullmatch(r"\d{10}", value):
        return "unix_epoch"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", value):
        return "iso_datetime"
    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", value):
        return "dd_mm_yyyy"
    return "unknown"


def parse_timestamp(value: str):
    """Parse a raw timestamp of any of the three known formats into a pandas Timestamp.
    dd_mm_yyyy values carry no time-of-day information, so they are set to midnight
    and flagged separately via `timestamp_time_estimated` rather than silently treated
    as equally precise to the other two formats.
    """
    fmt = classify_timestamp_format(value)
    if fmt == "unix_epoch":
        return pd.to_datetime(int(value), unit="s"), fmt, False
    if fmt == "iso_datetime":
        return pd.to_datetime(value), fmt, False
    if fmt == "dd_mm_yyyy":
        return pd.to_datetime(value, format="%d-%m-%Y"), fmt, True
    return pd.NaT, fmt, False


def clean_users(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    notes = {
        "input_rows": len(df),
        "duplicates_dropped": 0,
        "missing_values_found": int(df.isnull().sum().sum()),
        "negative_follower_counts_found": int((df["follower_count"] < 0).sum()),
    }
    before = len(df)
    df = df.drop_duplicates()
    notes["duplicates_dropped"] = before - len(df)
    notes["output_rows"] = len(df)
    return df.reset_index(drop=True), notes


def clean_posts(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    notes = {"input_rows": len(df)}

    # 1. Exact duplicate rows -> drop. Confirmed identical copies (same post_id
    #    and every other field), not conflicting records that need reconciling.
    before = len(df)
    df = df.drop_duplicates()
    notes["exact_duplicates_dropped"] = before - len(df)

    # 2. HTML-entity artifact in text_content. `&amp;` was the only entity type
    #    present across the column, so this is a standard decode, not content
    #    invention.
    entity_mask = df["text_content"].str.contains("&amp;", na=False)
    notes["rows_with_html_entities_fixed"] = int(entity_mask.sum())
    df["text_content"] = df["text_content"].str.replace("&amp;", "&", regex=False)

    # 3. Timestamps arrive in three different formats: Unix epoch (10-digit),
    #    ISO 8601 datetime, and a date-only DD-MM-YYYY format. Parse all three
    #    into one consistent datetime column. The date-only format has no time
    #    component, so rows parsed from it are flagged via
    #    `timestamp_time_estimated` rather than pretending we know a time we don't.
    parsed = df["timestamp"].apply(parse_timestamp)
    df["timestamp_parsed"] = parsed.apply(lambda x: x[0])
    df["timestamp_source_format"] = parsed.apply(lambda x: x[1])
    df["timestamp_time_estimated"] = parsed.apply(lambda x: x[2])
    notes["timestamp_format_counts"] = df["timestamp_source_format"].value_counts().to_dict()
    notes["timestamp_unparseable"] = int(df["timestamp_parsed"].isna().sum())

    # 4. Negative likes values. Their absolute magnitudes match the distribution
    #    of valid (positive) likes values, consistent with a sign-flip corruption
    #    rather than genuinely different data -> take absolute value.
    neg_mask = df["likes"] < 0
    notes["negative_likes_fixed"] = int(neg_mask.sum())
    df["likes"] = df["likes"].abs()

    # 5. Missingness in platform / text_content / likes (~15% each). Verified
    #    independent/random across the three columns (see reports/EDA_REPORT.md
    #    for the missingness-correlation check) -- not a correlated block that
    #    would justify a joint explanation. Left as NULL rather than imputed:
    #    there is no defensible basis to guess a value, and inventing one would
    #    misrepresent the data.
    notes["missing_values"] = {
        col: int(df[col].isnull().sum()) for col in ["platform", "text_content", "likes"]
    }

    # 6. Referential integrity check: every post.user_id should exist in users.csv.
    notes["output_rows"] = len(df)
    return df.reset_index(drop=True), notes


def main():
    users = pd.read_csv(USERS_IN)
    posts = pd.read_csv(POSTS_IN)

    users_clean, users_notes = clean_users(users)
    posts_clean, posts_notes = clean_posts(posts)

    # Referential integrity cross-check (uses both tables, so done here).
    orphan_user_ids = int((~posts_clean["user_id"].isin(users_clean["user_id"])).sum())
    posts_notes["orphan_user_ids_in_posts"] = orphan_user_ids

    # Merge into a single cleaned dataset: one row per post, enriched with the
    # posting user's profile info. Left join on user_id -- every post_id is kept,
    # and referential integrity (checked above) means no new nulls are introduced.
    merged = posts_clean.merge(users_clean, on="user_id", how="left")
    merged = merged[
        [
            "post_id", "user_id", "platform", "text_content", "timestamp",
            "timestamp_parsed", "timestamp_source_format", "timestamp_time_estimated",
            "likes", "shares", "comments",
            "location", "language", "account_created", "follower_count",
        ]
    ]

    # Write outputs -- single merged file, both formats
    merged.to_csv(OUT_DIR / "Social_Engine_clean.csv", index=False)
    merged.to_json(OUT_DIR / "Social_Engine_clean.json", orient="records", indent=2, date_format="iso")

    summary = {"users": users_notes, "posts": posts_notes, "merged_rows": len(merged)}
    with open(OUT_DIR / "cleaning_summary.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
