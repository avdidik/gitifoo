import asyncio
import json
from http.server import BaseHTTPRequestHandler
from datetime import date

from bot.ai_prompt import SYSTEM_PROMPT, build_prompt


async def _send_alert(bot_token: str, admin_id: int, text: str) -> None:
    from telegram import Bot
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=admin_id, text=text)


def _fallback_predictions(matches: list) -> list:
    """1:1 for all matches when YandexGPT is unavailable."""
    return [{"match_id": m["id"], "pred_home": 1, "pred_away": 1} for m in matches]


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Lazy imports so pure functions (build_prompt) are testable without env vars
        import requests
        from bot.config import CRON_SECRET, BOT_TOKEN, ADMIN_ID, YANDEX_API_KEY, YANDEX_FOLDER_ID
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
        ai = None
        matches = []

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

            resp = requests.post(
                "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
                headers={
                    "Authorization": f"Api-Key {YANDEX_API_KEY}",
                    "x-folder-id": YANDEX_FOLDER_ID,
                },
                json={
                    "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite/latest",
                    "completionOptions": {"stream": False, "temperature": 0.6, "maxTokens": "1500"},
                    "messages": [
                        {"role": "system", "text": SYSTEM_PROMPT},
                        {"role": "user", "text": prompt},
                    ],
                },
                timeout=30,
            )
            resp.raise_for_status()
            resp_json = resp.json()
            raw = resp_json["result"]["alternatives"][0]["message"]["text"].strip()
            if not raw:
                raise RuntimeError(f"YandexGPT вернул пустой текст. Полный ответ: {resp_json}")
            data = json.loads(raw)
            predictions = data["predictions"]
            quote = data.get("quote", "")

            for pred in predictions:
                upsert_prediction(
                    participant_id=ai["id"],
                    match_id=int(pred["match_id"]),
                    pred_home=int(pred["pred_home"]),
                    pred_away=int(pred["pred_away"]),
                )

            match_by_id = {m["id"]: m for m in matches}
            lines = ["🤖 Лёха AI поставил прогнозы:\n"]
            for pred in predictions:
                m = match_by_id.get(int(pred["match_id"]))
                if not m:
                    continue
                lines.append(
                    f"⚽ {m['team_home']} vs {m['team_away']}\n"
                    f"   Прогноз: {pred['pred_home']}:{pred['pred_away']}\n"
                    f"   💭 {pred.get('reason', '—')}"
                )
            if quote:
                lines.append(f'\n💬 "{quote}"')
            asyncio.run(_send_alert(BOT_TOKEN, ADMIN_ID, "\n\n".join(lines)))

        except Exception as exc:
            try:
                if ai and matches:
                    for pred in _fallback_predictions(matches):
                        upsert_prediction(ai["id"], pred["match_id"], pred["pred_home"], pred["pred_away"])
                    fallback_note = "Поставил 1:1 на все матчи как запасной вариант."
                else:
                    fallback_note = "Прогнозы не записаны (ошибка до загрузки матчей)."
            except Exception:
                fallback_note = "Прогнозы не записаны (ошибка при fallback)."
            asyncio.run(_send_alert(
                BOT_TOKEN,
                ADMIN_ID,
                f"⚠️ Лёха AI ({today}): {exc}\n{fallback_note}\n"
                "Если 401 — проверь YANDEX_API_KEY в Vercel: нужен Api-Key, не IAM-токен.",
            ))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Fallback predictions saved")
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
