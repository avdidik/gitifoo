"""One-time script to load group stage matches into Supabase."""
import csv
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from bot.db import get_today_game_day, open_game_day, add_match, get_conn


def main():
    with open("data/wc2026_group_stage.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            game_date = row["game_date"]
            game_day = get_today_game_day(game_date)
            if game_day is None:
                game_day = open_game_day(game_date)
                # Reset to pending (open_game_day sets 'open')
                with get_conn() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "UPDATE game_days SET status='pending' WHERE game_date=%s",
                            (game_date,)
                        )

            add_match(
                game_day_id=game_day["id"],
                team_home=row["team_home"],
                team_away=row["team_away"],
                kickoff_at=row["kickoff_utc"],
                stage=row["stage"],
            )
            print(f"Added: {row['team_home']} vs {row['team_away']} on {game_date}")

    print("Done!")


if __name__ == "__main__":
    main()
