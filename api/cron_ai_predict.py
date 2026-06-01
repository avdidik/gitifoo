import asyncio
import json
from http.server import BaseHTTPRequestHandler
from datetime import date


SYSTEM_PROMPT = (
    "Ты Лёха AI — участник конкурса прогнозов на ЧМ-2026. "
    "Ты умный аналитик, но с характером: иногда ставишь на нестандартный счёт "
    "или веришь в аутсайдера. Анализируй данные турнира, но не бойся рискнуть. "
    "Отвечай строго JSON-массивом без пояснений."
)


def build_prompt(matches: list[dict], standings: list[dict]) -> str:
    lines = ["Сегодня игровой день. Матчи:"]
    for m in matches:
        lines.append(f"- match_id={m['id']}: {m['team_home']} vs {m['team_away']}")

    if standings:
        lines.append("\nТекущая статистика турнира по группам:")
        current_group = None
        for row in standings:
            if row["match_group"] != current_group:
                current_group = row["match_group"]
                lines.append(f"Группа {current_group}:")
            lines.append(
                f"  {row['team']} — {row['pts']} очков (GF:{row['gf']}, GA:{row['ga']})"
            )
    else:
        lines.append("\nТурнир только начался, исторических данных нет.")

    lines.append(
        "\nПредскажи счёт каждого матча. Формат ответа:\n"
        '[{"match_id": 42, "pred_home": 2, "pred_away": 1}, ...]'
    )
    return "\n".join(lines)


async def _send_alert(bot_token: str, admin_id: int, text: str) -> None:
    from telegram import Bot
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=admin_id, text=text)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Lazy imports so pure functions (build_prompt) are testable without env vars
        import anthropic
        from bot.config import CRON_SECRET, BOT_TOKEN, ADMIN_ID, ANTHROPIC_API_KEY
        from bot.db import (
            get_today_game_day,
            get_matches_for_game_day,
            get_ai_participant,
            get_group_standings,
            get_ai_predictions_count_for_game_day,
            upsert_prediction,
        )

        if self.headers.get("Authorization") != f"Bearer {CRON_SECRET}":
            self.send_response(401)
            self.end_headers()
            return

        today = date.today().isoformat()

        try:
            game_day = get_today_game_day(today)
            if game_day is None or game_day["status"] != "open":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"No open game day today")
                return

            ai = get_ai_participant()
            if ai is None:
                raise RuntimeError("Участник 'Лёха AI' не найден в БД")

            matches = get_matches_for_game_day(game_day["id"])
            if not matches:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"No matches today")
                return

            if get_ai_predictions_count_for_game_day(game_day["id"], ai["id"]) > 0:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"Already predicted today")
                return

            standings = get_group_standings()
            prompt = build_prompt(matches, standings)

            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            message = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            predictions = json.loads(raw)

            for pred in predictions:
                upsert_prediction(
                    participant_id=ai["id"],
                    match_id=int(pred["match_id"]),
                    pred_home=int(pred["pred_home"]),
                    pred_away=int(pred["pred_away"]),
                )

        except Exception as exc:
            asyncio.run(_send_alert(
                BOT_TOKEN,
                ADMIN_ID,
                f"Лёха AI не смог поставить сегодня ({today}): {exc}\n"
                "Прогнозы не записаны.",
            ))
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(exc).encode())
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
