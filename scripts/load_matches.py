"""One-time script to load all matches (group + play-off) into Supabase."""
import csv
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

import psycopg2
import psycopg2.extras
from bot.config import DB_URL


def parse_row(row):
    game_date = datetime.strptime(row["game_date"].strip(), "%d.%m.%Y").strftime("%Y-%m-%d")
    time_str = row["kickoff_utc"].strip().rstrip(";")
    kickoff_at = f"{game_date} {time_str}:00+00"
    return {
        "stage": row["stage"].strip(),
        "label": row["label"].strip() or None,
        "team_home": row["team_home"].strip(),
        "team_away": row["team_away"].strip(),
        "match_group": row["group"].strip() or None,
        "game_date": game_date,
        "kickoff_at": kickoff_at,
    }


def main():
    # Parse entire CSV before touching the DB
    rows = []
    with open("data/wc2026_group_stage.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f, delimiter=";"):
            rows.append(parse_row(row))

    unique_dates = sorted({r["game_date"] for r in rows})
    print(f"Parsed {len(rows)} matches across {len(unique_dates)} game days. Connecting...")

    conn = psycopg2.connect(
        DB_URL,
        connect_timeout=30,
        keepalives=1,
        keepalives_idle=10,
        keepalives_interval=5,
        keepalives_count=5,
    )
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Insert all game_days
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO game_days (game_date, status) VALUES %s ON CONFLICT (game_date) DO NOTHING",
            [(d, "pending") for d in unique_dates],
        )

        # Fetch all game_day ids in one query
        cur.execute("SELECT id, game_date FROM game_days WHERE game_date = ANY(%s::date[])", (unique_dates,))
        date_to_id = {str(r["game_date"]): r["id"] for r in cur.fetchall()}

        # Insert all matches in one batch
        match_rows = [
            (
                date_to_id[r["game_date"]],
                r["team_home"],
                r["team_away"],
                r["kickoff_at"],
                r["stage"],
                r["label"],
                r["match_group"],
            )
            for r in rows
        ]
        psycopg2.extras.execute_values(
            cur,
            """INSERT INTO matches
               (game_day_id, team_home, team_away, kickoff_at, stage, label, match_group)
               VALUES %s""",
            match_rows,
        )

        conn.commit()
        for r in rows:
            label = f"[{r['label']}] " if r["label"] else ""
            print(f"  {label}{r['team_home']} vs {r['team_away']} on {r['game_date']}")
        print(f"\nDone! {len(rows)} matches loaded.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
