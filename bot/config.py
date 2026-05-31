import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
DB_URL = os.environ["DB_URL"]
GROUP_ID = int(os.environ["GROUP_ID"])
ADMIN_ID = int(os.environ["ADMIN_ID"])
CRON_SECRET = os.environ["CRON_SECRET"]
DASH_URL = os.environ.get("DASH_URL")  # Optional: set after Streamlit deploy
BOT_URL = "https://t.me/gitifoo_bot"
