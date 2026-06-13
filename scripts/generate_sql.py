"""Generate SQL file with all matches — paste into Supabase SQL Editor."""
import csv
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

OUTPUT = "scripts/load_matches.sql"


def parse_row(row):
    game_date = datetime.strptime(row["game_date"].strip(), "%d.%m.%Y").strftime("%Y-%m-%d")
    time_str = row["kickoff_utc"].strip().rstrip(";")
    kickoff_at = f"{game_date} {time_str}:00+00"
    # Matches before 07:00 MSK belong to the previous day's game session (19:00–07:00 window)
    hour = int(time_str.split(":")[0])
    if hour < 7:
        game_day_date = (datetime.strptime(game_date, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        game_day_date = game_date
    return {
        "stage": row["stage"].strip(),
        "label": row["label"].strip() or None,
        "team_home": row["team_home"].strip(),
        "team_away": row["team_away"].strip(),
        "match_group": row["group"].strip() or None,
        "game_day_date": game_day_date,
        "kickoff_at": kickoff_at,
    }


def esc(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("'", "''") + "'"


def main():
    rows = []
    with open("data/wc2026_group_stage.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            rows.append(parse_row(row))

    unique_dates = sorted({r["game_day_date"] for r in rows})

    lines = ["-- Auto-generated. Run in Supabase SQL Editor.\n"]

    lines.append("-- 1. game_days")
    for d in unique_dates:
        lines.append(
            f"INSERT INTO game_days (game_date, status) VALUES ('{d}', 'pending')"
            f" ON CONFLICT (game_date) DO NOTHING;"
        )

    lines.append("\n-- 2. matches")
    for r in rows:
        lines.append(
            f"INSERT INTO matches (game_day_id, team_home, team_away, kickoff_at, stage, label, match_group)"
            f" SELECT id, {esc(r['team_home'])}, {esc(r['team_away'])},"
            f" '{r['kickoff_at']}', {esc(r['stage'])}, {esc(r['label'])}, {esc(r['match_group'])}"
            f" FROM game_days WHERE game_date = '{r['game_day_date']}';"
        )

    with open(OUTPUT, "w", encoding="utf-8") as out:
        out.write("\n".join(lines) + "\n")

    print(f"Generated {OUTPUT} ({len(rows)} matches, {len(unique_dates)} game days)")
    print("Open Supabase → SQL Editor → paste the file contents → Run")


if __name__ == "__main__":
    main()
