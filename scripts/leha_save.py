"""
Сохраняет прогнозы Лёхи AI в БД и отправляет сообщение в группу.

Использование:
  python scripts/leha_save.py '<json>'

Где <json>:
  '[{"match_id": 42, "pred_home": 2, "pred_away": 1, "reason": "..."}, ...]'
"""
import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from bot.db import get_ai_participant, upsert_prediction, get_matches_for_game_day, get_today_game_day
from bot.config import BOT_TOKEN, GROUP_ID
from bot.teams import flag
from datetime import date


async def send_to_group(text: str) -> None:
    from telegram import Bot
    await Bot(token=BOT_TOKEN).send_message(chat_id=GROUP_ID, text=text)


parser = argparse.ArgumentParser()
parser.add_argument("predictions_json", help="JSON со списком прогнозов")
parser.add_argument("--send", action="store_true", help="Отправить сообщение в Telegram-группу")
args = parser.parse_args()

predictions = json.loads(args.predictions_json)

ai = get_ai_participant()
if ai is None:
    print("❌ Участник 'Лёха AI' не найден в БД")
    sys.exit(1)

today = date.today().isoformat()
game_day = get_today_game_day(today)
matches = get_matches_for_game_day(game_day["id"]) if game_day else []
match_by_id = {m["id"]: m for m in matches}

lines = [f"🤖 Лёха AI поставил прогнозы:\n"]
for pred in predictions:
    upsert_prediction(
        participant_id=ai["id"],
        match_id=int(pred["match_id"]),
        pred_home=int(pred["pred_home"]),
        pred_away=int(pred["pred_away"]),
    )
    m = match_by_id.get(int(pred["match_id"]))
    if m:
        lines.append(
            f"⚽ {flag(m['team_home'])} {pred['pred_home']}:{pred['pred_away']} {flag(m['team_away'])}\n"
            f"   💭 {pred.get('reason', '—')}"
        )

message = "\n\n".join(lines)
print(message)

try:
    asyncio.run(send_to_group(message))
    print(f"\n✅ {len(predictions)} прогнозов сохранено и отправлено в группу.")
except Exception as e:
    print(f"\n✅ {len(predictions)} прогнозов сохранено в БД.")
    print(f"⚠️  Telegram недоступен (VPN?): {e}")
