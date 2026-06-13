"""Выводит матчи и статистику текущего открытого игрового дня — для передачи агенту."""
import sys
import json
from pathlib import Path
from datetime import date

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from bot.db import get_today_game_day, get_matches_for_game_day, get_group_standings
from bot.ai_prompt import build_prompt

today = date.today().isoformat()
game_day = get_today_game_day(today)

if game_day is None or game_day["status"] != "open":
    print(f"Нет открытого игрового дня на {today} (статус: {game_day['status'] if game_day else 'нет'})")
    sys.exit(1)

matches = get_matches_for_game_day(game_day["id"])
standings = get_group_standings()

print(f"game_day_id={game_day['id']}")
print(json.dumps([{"id": m["id"], "home": m["team_home"], "away": m["team_away"]} for m in matches],
                 ensure_ascii=False))
print("---PROMPT---")
print(build_prompt(matches, standings))
