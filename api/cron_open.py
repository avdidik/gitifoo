import asyncio
from http.server import BaseHTTPRequestHandler
from datetime import date

from bot.config import CRON_SECRET, GROUP_ID, BOT_TOKEN, BOT_URL
from bot.db import open_game_day, get_matches_for_game_day, get_today_game_day
from bot.teams import flag
from telegram import Bot


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Authorization") != f"Bearer {CRON_SECRET}":
            self.send_response(401)
            self.end_headers()
            return

        today = date.today().isoformat()
        # Не создаём пустой день в выходной: открываем только уже существующий
        # день, у которого есть матчи (расписание грузится заранее).
        game_day = get_today_game_day(today)
        matches = get_matches_for_game_day(game_day["id"]) if game_day else []

        if not matches:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"No matches today")
            return

        open_game_day(today)

        lines = [f"🌅 Игровой день {today} открыт! Принимаю прогнозы до 18:00.\n\nМатчи:"]
        for m in matches:
            kickoff = m["kickoff_at"].strftime("%H:%M")
            lines.append(f"  ⚽ {flag(m['team_home'])} vs {flag(m['team_away'])} в {kickoff}")
        lines.append(f"\n👉 Сделать прогноз: {BOT_URL}")

        bot = Bot(token=BOT_TOKEN)
        asyncio.run(bot.send_message(chat_id=GROUP_ID, text="\n".join(lines)))

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
