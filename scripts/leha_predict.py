"""
Лёха AI — локальный запуск прогнозов через Claude.

Запуск: python scripts/leha_predict.py
Флаги:
  --force   перезаписать прогнозы, если они уже есть
  --dry-run не сохранять в БД, только показать что получилось

Запускать до 18:00 МСК в день матчей.
"""
import sys
import json
import re
import argparse
import asyncio
import os
from datetime import date
from pathlib import Path

# Make bot/ importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

# import anthropic
# from bot.ai_prompt import SYSTEM_PROMPT, build_prompt
from bot.db import (
    get_today_game_day,
    get_matches_for_game_day,
    get_ai_participant,
    get_group_standings,
    get_ai_predictions_count_for_game_day,
    upsert_prediction,
)
from bot.config import BOT_TOKEN, ADMIN_ID, GROUP_ID
from bot.teams import flag


async def send_to_group(text: str) -> None:
    from telegram import Bot
    await Bot(token=BOT_TOKEN).send_message(chat_id=GROUP_ID, text=text)


# def call_claude(prompt: str) -> dict:
#     client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
#     message = client.messages.create(
#         model="claude-sonnet-4-6",
#         max_tokens=2048,
#         system=SYSTEM_PROMPT,
#         messages=[{"role": "user", "content": prompt}],
#     )
#     raw = message.content[0].text.strip()
#     match = re.search(r'\{.*\}', raw, re.DOTALL)
#     if not match:
#         raise RuntimeError(f"JSON не найден в ответе:\n{raw[:500]}")
#     return json.loads(match.group())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Перезаписать существующие прогнозы")
    parser.add_argument("--dry-run", action="store_true", help="Не сохранять в БД")
    args = parser.parse_args()

    today = date.today().isoformat()
    game_day = get_today_game_day(today)

    if game_day is None:
        print(f"❌ Нет игрового дня на {today}")
        sys.exit(1)

    if game_day["status"] != "open":
        print(f"⚠️  Игровой день {today} не открыт (статус: {game_day['status']})")
        print("Открой день в Supabase или дождись 09:00 МСК")
        sys.exit(1)

    ai = get_ai_participant()
    if ai is None:
        print("❌ Участник 'Лёха AI' не найден в БД")
        sys.exit(1)

    matches = get_matches_for_game_day(game_day["id"])
    if not matches:
        print(f"❌ Матчей на {today} нет")
        sys.exit(1)

    existing = get_ai_predictions_count_for_game_day(game_day["id"], ai["id"])
    if existing > 0 and not args.force:
        print(f"⚠️  Лёха AI уже сделал {existing} прогноз(ов) на {today}. Используй --force для перезаписи.")
        sys.exit(0)

    # Прогнозы генерирует Claude Code в чате, сохраняет leha_save.py
    print("ℹ️  Используй leha_context.py + leha_save.py для генерации прогнозов через Claude Code.")
    sys.exit(0)

    # standings = get_group_standings()
    # prompt = build_prompt(matches, standings)
    # data = call_claude(prompt)
    # predictions = data["predictions"]

    match_by_id = {m["id"]: m for m in matches}

    lines = [f"🤖 Лёха AI — прогнозы на {today}:\n"]
    for pred in predictions:
        m = match_by_id.get(int(pred["match_id"]))
        if not m:
            continue
        home_score = int(pred["pred_home"])
        away_score = int(pred["pred_away"])
        reason = pred.get("reason", "—")
        lines.append(
            f"⚽ {flag(m['team_home'])} {m['team_home']} {home_score}:{away_score} "
            f"{m['team_away']} {flag(m['team_away'])}\n"
            f"   💭 {reason}"
        )
        if not args.dry_run:
            upsert_prediction(
                participant_id=ai["id"],
                match_id=int(pred["match_id"]),
                pred_home=home_score,
                pred_away=away_score,
            )

    message = "\n\n".join(lines)
    print(message)

    if args.dry_run:
        print("\n[dry-run] В БД не сохранено.")
        return

    print(f"\n✅ Сохранено {len(predictions)} прогнозов.")
    asyncio.run(send_to_group(message))
    print("📨 Отправлено в группу.")


if __name__ == "__main__":
    main()
