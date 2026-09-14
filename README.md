# Data Vortex — Round 1: Data Intake Restoration

AARUUSH '26 · Data Vortex · Theme: Rebuilding the Social Engine

## Overview

This repository restores the corrupted intake pipeline for the "Social Engine" dataset:
recovering the raw data, cleaning it, and producing an exploratory data analysis (EDA) of
the result.

## Data Recovery

The raw dataset was not distributed directly — it had to be recovered from
`https://datavortex-social-engine.vercel.app/`, a React single-page application presented
as a failed "recovery terminal". The terminal's dashboard hides a floating "recovery shell"
button; running `logs` inside it repeatedly surfaces the last responsive node,
**`node_07`**, and running a command like `connect node_07` unlocks the archive screen with
two "RECOVER" buttons.

Under the hood, that UI is cosmetic: both CSV files (`Social_Engine_Users.csv` and
`Social_Engine_Posts_Corrupted.csv`) are embedded as plain string constants inside the
site's compiled JavaScript bundle (`assets/index-*.js`), served to every visitor's browser
on page load. The two files were located by inspecting that bundle and extracted directly
from it. They are stored here unmodified in `data/raw/`.

## Repository Structure

```
data/
  raw/                          # recovered, untouched source files
  processed/                    # cleaned outputs (CSV + JSON) + cleaning_summary.json
notebooks/
  eda_and_cleaning.ipynb        # full narrative walkthrough: profiling -> cleaning -> EDA
scripts/
  clean.py                      # standalone cleaning pipeline (raw -> data/processed/)
  eda.py                        # standalone EDA chart + summary generator
reports/
  EDA_REPORT.md                 # written findings with embedded charts
  eda_summary.json              # all numeric detail behind the charts
  figures/                      # chart PNGs referenced by the report
requirements.txt
```

## Reproducing the Pipeline

```bash
pip install -r requirements.txt
python scripts/clean.py     # data/raw/*.csv -> data/processed/*.csv, *.json
python scripts/eda.py       # data/processed/*.csv -> reports/figures/*.png, reports/eda_summary.json
```

Or open `notebooks/eda_and_cleaning.ipynb` and run all cells for the same pipeline with
inline narrative and charts.

## Cleaning Summary

Full reasoning is in `reports/EDA_REPORT.md`; the short version:

| Issue found | Fix applied | Why |
|---|---|---|
| 360 exact-duplicate rows | Dropped | Confirmed identical copies, not conflicting records |
| 328 posts with trailing `&amp;` in `text_content` | HTML-unescaped to `&` | Only entity type present; standard decoding, not content invention |
| Timestamps mixed across 3 formats (Unix epoch / ISO datetime / `DD-MM-YYYY` date-only) | Parsed to one consistent datetime; date-only rows flagged via `timestamp_time_estimated` | Keeps precision honest instead of inventing a time |
| 509 negative `likes` values | Converted to absolute value | Magnitudes matched the valid-likes distribution, consistent with a sign-flip corruption |
| `platform`, `text_content`, `likes` missing in ~15% of rows each | Left as `NULL`, not imputed | Verified the missingness is statistically independent/random across the three columns (not a correlated block) — no defensible basis to guess a value |

`Users.csv` required no cleaning — no missing values, duplicates, bad dates, or negative
follower counts were found.

## Key EDA Findings

- Platform and posting volume are both evenly distributed — no dominant platform, no
  seasonal trend (see `reports/EDA_REPORT.md` §3–4).
- `likes`, `shares`, and `comments` are each **uniformly distributed** with near-zero
  pairwise correlation, unlike the long-tailed, correlated pattern real engagement data
  usually shows — suggesting these fields were generated independently at random rather
  than reflecting organic behavior (§5).
- `follower_count` is likewise uniform, with no "mega-influencer" long tail.
- USA is the single largest user location; the remainder is spread broadly across ~15
  other countries.

Full detail, all 9 charts, and the exact reasoning behind each conclusion are in
`reports/EDA_REPORT.md`.
