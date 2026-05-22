import asyncio
from http.server import BaseHTTPRequestHandler
from datetime import date

from bot.config import CRON_SECRET, GROUP_ID, BOT_TOKEN
from bot.db import close_game_day, get_today_game_day, get_all_predictions_for_game_day
from telegram import Bot


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Authorization") != f"Bearer {CRON_SECRET}":
            self.send_response(401)
            self.end_headers()
            return

        today = date.today().isoformat()
        close_game_day(today)

        game_day = get_today_game_day(today)
        if game_day is None:
            self.send_response(200)
            self.end_headers()
            return

        preds = get_all_predictions_for_game_day(game_day["id"])
        lines = ["⏰ Приём прогнозов закрыт!\n"]
        current_match = None
        for row in preds:
            match_label = f"{row['team_home']} vs {row['team_away']}"
            if match_label != current_match:
                lines.append(f"\n⚽ {match_label}")
                current_match = match_label
            lines.append(f"  {row['name']}: {row['pred_home']}:{row['pred_away']}")

        if not preds:
            lines.append("Никто не сделал прогнозов сегодня 😢")

        bot = Bot(token=BOT_TOKEN)
        asyncio.run(bot.send_message(chat_id=GROUP_ID, text="\n".join(lines)))

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
