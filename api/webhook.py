import asyncio
import json
from http.server import BaseHTTPRequestHandler

from telegram import Update
from bot.application import build_application

_app = None


def get_app():
    global _app
    if _app is None:
        _app = build_application()
    return _app


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)
        app = get_app()
        update = Update.de_json(data, app.bot)

        async def process():
            async with app:
                await app.process_update(update)

        asyncio.run(process())
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"FWC2026 Bot is alive")
