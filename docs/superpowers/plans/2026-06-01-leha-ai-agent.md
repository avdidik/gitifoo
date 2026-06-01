# Лёха AI Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить ИИ-агента "Лёха AI" как пятого участника конкурса, который автономно делает прогнозы на матчи каждого игрового дня через Vercel Cron.

**Architecture:** Новый Vercel Cron (12:00 UTC / 15:00 МСК) запускает `api/cron_ai_predict.py`. Хендлер читает турнирный контекст из Supabase, вызывает Claude Haiku API, записывает прогнозы через существующую `upsert_prediction()`. При ошибке — личный алерт администратору в Telegram.

**Tech Stack:** Python, psycopg2, anthropic SDK, python-telegram-bot, Vercel Cron

---

## File Map

| Действие | Файл | Ответственность |
|---|---|---|
| Изменить | `requirements.txt` | добавить `anthropic` |
| Изменить | `bot/config.py` | добавить `ANTHROPIC_API_KEY` |
| Изменить | `bot/db.py` | 3 новые функции: get_ai_participant, get_group_standings, get_ai_predictions_count_for_game_day |
| Создать | `api/cron_ai_predict.py` | Vercel handler + build_prompt |
| Изменить | `vercel.json` | новый маршрут и cron schedule |
| Изменить | `schema.sql` | документировать миграцию |
| Создать | `tests/test_ai_predict.py` | тесты для build_prompt |
| Изменить | `tests/test_db.py` | тесты для 3 новых DB-функций |

---

## Task 1: Зависимости и конфиг

**Files:**
- Modify: `requirements.txt`
- Modify: `bot/config.py`

- [ ] **Step 1: Добавить anthropic в requirements.txt**

Открыть `requirements.txt` и добавить строку:

```
anthropic>=0.28.0
```

Итоговый файл:
```
python-telegram-bot==20.7
Flask==3.0.3
psycopg2-binary==2.9.9
pytest==8.2.0
python-dotenv==1.0.1
streamlit==1.35.0
plotly==5.22.0
pandas==2.2.2
anthropic>=0.28.0
```

- [ ] **Step 2: Добавить ANTHROPIC_API_KEY в bot/config.py**

Открыть `bot/config.py`. Текущее содержимое:
```python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
DB_URL = os.environ["DB_URL"]
GROUP_ID = int(os.environ["GROUP_ID"])
ADMIN_ID = int(os.environ["ADMIN_ID"])
CRON_SECRET = os.environ["CRON_SECRET"]
DASH_URL = os.environ.get("DASH_URL")
BOT_URL = "https://t.me/gitifoo_bot"
```

Добавить строку `ANTHROPIC_API_KEY` после `CRON_SECRET`:

```python
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
DB_URL = os.environ["DB_URL"]
GROUP_ID = int(os.environ["GROUP_ID"])
ADMIN_ID = int(os.environ["ADMIN_ID"])
CRON_SECRET = os.environ["CRON_SECRET"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
DASH_URL = os.environ.get("DASH_URL")
BOT_URL = "https://t.me/gitifoo_bot"
```

- [ ] **Step 3: Добавить ANTHROPIC_API_KEY в .env.example**

Открыть `.env.example` и добавить:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

- [ ] **Step 4: Установить зависимость локально**

```bash
pip install anthropic
```

Ожидаемый вывод: `Successfully installed anthropic-...`

- [ ] **Step 5: Коммит**

```bash
git add requirements.txt bot/config.py .env.example
git commit -m "feat: add anthropic dependency and ANTHROPIC_API_KEY config"
```

---

## Task 2: Новые DB-функции

**Files:**
- Modify: `bot/db.py`
- Modify: `tests/test_db.py`

**Контекст:** Три новые функции нужны для: (1) получения записи агента, (2) сбора турнирного контекста, (3) проверки идемпотентности.

**ВАЖНО:** Перед написанием тестов необходимо выполнить миграцию БД из Task 4, чтобы участник 'Лёха AI' существовал. Если миграция ещё не выполнена — сначала выполни Task 4, Step 1–2, затем вернись сюда.

- [ ] **Step 1: Написать падающий тест для get_ai_participant()**

Добавить в `tests/test_db.py`:

```python
from bot.db import add_participant, get_participant, open_game_day, get_today_game_day, get_ai_participant


def test_get_ai_participant():
    # Требует: миграция из Task 4 выполнена, Лёха AI в БД
    ai = get_ai_participant()
    assert ai is not None
    assert ai["name"] == "Лёха AI"
    assert ai["telegram_id"] is None
```

- [ ] **Step 2: Запустить тест, убедиться что падает**

```bash
pytest tests/test_db.py::test_get_ai_participant -v
```

Ожидаемый вывод: `FAILED` — `ImportError: cannot import name 'get_ai_participant'`

- [ ] **Step 3: Реализовать get_ai_participant() в bot/db.py**

Добавить функцию в конец `bot/db.py`:

```python
def get_ai_participant() -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM participants WHERE name = 'Лёха AI'")
            return cur.fetchone()
```

- [ ] **Step 4: Запустить тест, убедиться что проходит**

```bash
pytest tests/test_db.py::test_get_ai_participant -v
```

Ожидаемый вывод: `PASSED`

- [ ] **Step 5: Написать падающий тест для get_group_standings()**

Добавить в `tests/test_db.py`:

```python
from bot.db import add_participant, get_participant, open_game_day, get_today_game_day, get_ai_participant, get_group_standings


def test_get_group_standings_returns_list():
    standings = get_group_standings()
    assert isinstance(standings, list)
    # Если матчи с результатами есть — проверяем структуру строки
    if standings:
        row = standings[0]
        assert "match_group" in row
        assert "team" in row
        assert "pts" in row
        assert "gf" in row
        assert "ga" in row
```

- [ ] **Step 6: Запустить тест, убедиться что падает**

```bash
pytest tests/test_db.py::test_get_group_standings_returns_list -v
```

Ожидаемый вывод: `FAILED` — `ImportError: cannot import name 'get_group_standings'`

- [ ] **Step 7: Реализовать get_group_standings() в bot/db.py**

Добавить функцию в конец `bot/db.py`:

```python
def get_group_standings() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT match_group, team,
                       SUM(pts) AS pts, SUM(gf) AS gf, SUM(ga) AS ga
                FROM (
                    SELECT team_home AS team, match_group,
                           CASE WHEN result_home > result_away THEN 3
                                WHEN result_home = result_away THEN 1
                                ELSE 0 END AS pts,
                           result_home AS gf, result_away AS ga
                    FROM matches
                    WHERE stage = 'group' AND result_home IS NOT NULL
                    UNION ALL
                    SELECT team_away AS team, match_group,
                           CASE WHEN result_away > result_home THEN 3
                                WHEN result_home = result_away THEN 1
                                ELSE 0 END AS pts,
                           result_away AS gf, result_home AS ga
                    FROM matches
                    WHERE stage = 'group' AND result_home IS NOT NULL
                ) t
                GROUP BY match_group, team
                ORDER BY match_group,
                         SUM(pts) DESC,
                         (SUM(gf) - SUM(ga)) DESC,
                         SUM(gf) DESC
                """
            )
            return cur.fetchall()
```

- [ ] **Step 8: Запустить тест, убедиться что проходит**

```bash
pytest tests/test_db.py::test_get_group_standings_returns_list -v
```

Ожидаемый вывод: `PASSED`

- [ ] **Step 9: Написать падающий тест для get_ai_predictions_count_for_game_day()**

Добавить в `tests/test_db.py`:

```python
from bot.db import (
    add_participant, get_participant, open_game_day, get_today_game_day,
    get_ai_participant, get_group_standings, get_ai_predictions_count_for_game_day,
)


def test_get_ai_predictions_count_no_predictions():
    # Несуществующий game_day_id и participant_id → 0
    count = get_ai_predictions_count_for_game_day(999999, 999999)
    assert count == 0
```

- [ ] **Step 10: Запустить тест, убедиться что падает**

```bash
pytest tests/test_db.py::test_get_ai_predictions_count_no_predictions -v
```

Ожидаемый вывод: `FAILED` — `ImportError`

- [ ] **Step 11: Реализовать get_ai_predictions_count_for_game_day() в bot/db.py**

Добавить функцию в конец `bot/db.py`:

```python
def get_ai_predictions_count_for_game_day(game_day_id: int, participant_id: int) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) FROM predictions pr
                   JOIN matches m ON pr.match_id = m.id
                   WHERE m.game_day_id = %s AND pr.participant_id = %s""",
                (game_day_id, participant_id),
            )
            return cur.fetchone()[0]
```

- [ ] **Step 12: Запустить все тесты DB, убедиться что все проходят**

```bash
pytest tests/test_db.py -v
```

Ожидаемый вывод: все тесты `PASSED`

- [ ] **Step 13: Коммит**

```bash
git add bot/db.py tests/test_db.py
git commit -m "feat: add get_ai_participant, get_group_standings, get_ai_predictions_count_for_game_day"
```

---

## Task 3: Cron-хендлер и build_prompt

**Files:**
- Create: `api/cron_ai_predict.py`
- Create: `tests/test_ai_predict.py`

- [ ] **Step 1: Создать api/__init__.py (нужен для импорта в тестах)**

```bash
touch api/__init__.py
```

Без этого файла `from api.cron_ai_predict import build_prompt` в тестах упадёт с `ModuleNotFoundError`.

- [ ] **Step 2: Написать падающие тесты для build_prompt()**

Создать файл `tests/test_ai_predict.py`:

```python
import pytest
from api.cron_ai_predict import build_prompt


def test_build_prompt_includes_match_ids():
    matches = [
        {"id": 42, "team_home": "Бразилия", "team_away": "Германия"},
        {"id": 43, "team_home": "Франция", "team_away": "Аргентина"},
    ]
    prompt = build_prompt(matches, [])
    assert "match_id=42" in prompt
    assert "Бразилия vs Германия" in prompt
    assert "match_id=43" in prompt
    assert "Франция vs Аргентина" in prompt


def test_build_prompt_with_standings():
    matches = [{"id": 1, "team_home": "Бразилия", "team_away": "Германия"}]
    standings = [
        {"match_group": "E", "team": "Бразилия", "pts": 6, "gf": 5, "ga": 1},
        {"match_group": "E", "team": "Германия", "pts": 4, "gf": 3, "ga": 2},
        {"match_group": "F", "team": "Франция", "pts": 3, "gf": 2, "ga": 0},
    ]
    prompt = build_prompt(matches, standings)
    assert "Группа E" in prompt
    assert "Бразилия — 6 очков" in prompt
    assert "Германия — 4 очков" in prompt
    assert "Группа F" in prompt


def test_build_prompt_no_standings_message():
    matches = [{"id": 5, "team_home": "США", "team_away": "Мексика"}]
    prompt = build_prompt(matches, [])
    assert "только начался" in prompt


def test_build_prompt_contains_format_instruction():
    matches = [{"id": 1, "team_home": "X", "team_away": "Y"}]
    prompt = build_prompt(matches, [])
    assert "pred_home" in prompt
    assert "pred_away" in prompt
```

- [ ] **Step 3: Запустить тесты, убедиться что падают**

```bash
pytest tests/test_ai_predict.py -v
```

Ожидаемый вывод: `FAILED` — `ModuleNotFoundError: No module named 'api.cron_ai_predict'`

- [ ] **Step 4: Создать api/cron_ai_predict.py**

```python
import asyncio
import json
from http.server import BaseHTTPRequestHandler
from datetime import date

import anthropic
from telegram import Bot

from bot.config import CRON_SECRET, BOT_TOKEN, ADMIN_ID, ANTHROPIC_API_KEY
from bot.db import (
    get_today_game_day,
    get_matches_for_game_day,
    get_ai_participant,
    get_group_standings,
    get_ai_predictions_count_for_game_day,
    upsert_prediction,
)

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


async def _send_alert(text: str) -> None:
    bot = Bot(token=BOT_TOKEN)
    await bot.send_message(chat_id=ADMIN_ID, text=text)


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
                f"Лёха AI не смог поставить сегодня ({today}): {exc}\n"
                "Прогнозы не записаны."
            ))
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(exc).encode())
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
```

- [ ] **Step 5: Запустить тесты, убедиться что проходят**

```bash
pytest tests/test_ai_predict.py -v
```

Ожидаемый вывод: все 4 теста `PASSED`

- [ ] **Step 6: Запустить все тесты проекта**

```bash
pytest tests/ -v
```

Ожидаемый вывод: все тесты `PASSED`

- [ ] **Step 7: Коммит**

```bash
git add api/__init__.py api/cron_ai_predict.py tests/test_ai_predict.py
git commit -m "feat: add Лёха AI cron handler with build_prompt"
```

---

## Task 4: Миграция БД и schema.sql

**Files:**
- Modify: `schema.sql`

**ВАЖНО:** Шаги 1–2 выполняются вручную в Supabase SQL Editor (не через код).

- [ ] **Step 1: Выполнить миграцию в Supabase SQL Editor**

Открыть Supabase → SQL Editor, выполнить:

```sql
ALTER TABLE participants ALTER COLUMN telegram_id DROP NOT NULL;
```

Ожидаемый вывод: `Success. No rows returned`

- [ ] **Step 2: Добавить участника Лёха AI в Supabase SQL Editor**

```sql
INSERT INTO participants (telegram_id, name) VALUES (NULL, 'Лёха AI');
```

Ожидаемый вывод: `Success. 1 row affected`

Проверить: `SELECT * FROM participants WHERE name = 'Лёха AI';` → должна вернуться строка с `telegram_id = null`.

- [ ] **Step 3: Задокументировать миграцию в schema.sql**

Открыть `schema.sql`. Найти строку:
```sql
  telegram_id BIGINT UNIQUE NOT NULL,
```

Заменить на:
```sql
  telegram_id BIGINT UNIQUE,  -- NULL для AI-участников
```

Добавить в конец файла:

```sql
-- Migration 2026-06-01: allow NULL telegram_id for AI participants
-- ALTER TABLE participants ALTER COLUMN telegram_id DROP NOT NULL;
-- INSERT INTO participants (telegram_id, name) VALUES (NULL, 'Лёха AI');
```

- [ ] **Step 4: Обновить vercel.json**

Открыть `vercel.json`. Текущее содержимое:
```json
{
  "builds": [
    { "src": "api/*.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/api/webhook", "dest": "/api/webhook.py" },
    { "src": "/api/cron_open", "dest": "/api/cron_open.py" },
    { "src": "/api/cron_close", "dest": "/api/cron_close.py" }
  ],
  "crons": [
    { "path": "/api/cron_open",  "schedule": "0 6 * * *"  },
    { "path": "/api/cron_close", "schedule": "0 15 * * *" }
  ]
}
```

Заменить на:
```json
{
  "builds": [
    { "src": "api/*.py", "use": "@vercel/python" }
  ],
  "routes": [
    { "src": "/api/webhook",        "dest": "/api/webhook.py" },
    { "src": "/api/cron_open",      "dest": "/api/cron_open.py" },
    { "src": "/api/cron_close",     "dest": "/api/cron_close.py" },
    { "src": "/api/cron_ai_predict","dest": "/api/cron_ai_predict.py" }
  ],
  "crons": [
    { "path": "/api/cron_open",       "schedule": "0 6 * * *"  },
    { "path": "/api/cron_close",      "schedule": "0 15 * * *" },
    { "path": "/api/cron_ai_predict", "schedule": "0 12 * * *" }
  ]
}
```

- [ ] **Step 5: Коммит**

```bash
git add schema.sql vercel.json
git commit -m "feat: add cron_ai_predict route and schedule, update schema"
```

---

## Task 5: Деплой и переменные окружения

**Files:** без изменений кода

- [ ] **Step 1: Получить ADMIN_TELEGRAM_ID**

Написать любое сообщение боту `@userinfobot` в Telegram.
Бот ответит твоим `Id` — это и есть значение. Скопировать.

**Примечание:** В проекте уже есть `ADMIN_ID` в `bot/config.py` — он используется для алертов. Если `ADMIN_ID` уже настроен в Vercel и совпадает с твоим Telegram ID, этот шаг можно пропустить.

- [ ] **Step 2: Добавить ANTHROPIC_API_KEY в Vercel**

1. Открыть [vercel.com](https://vercel.com) → твой проект → Settings → Environment Variables
2. Добавить переменную:
   - Name: `ANTHROPIC_API_KEY`
   - Value: ключ из [console.anthropic.com](https://console.anthropic.com) → API Keys
   - Environment: Production, Preview, Development (все три)
3. Сохранить

- [ ] **Step 3: Получить Anthropic API Key (если нет)**

1. Открыть [console.anthropic.com](https://console.anthropic.com)
2. Settings → API Keys → Create Key
3. Скопировать ключ (показывается один раз)

- [ ] **Step 4: Добавить ключ в локальный .env**

В файл `.env` добавить:
```
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 5: Задеплоить**

```bash
git push origin main
```

Vercel автоматически подхватит новый `cron_ai_predict.py` из папки `api/`.

- [ ] **Step 6: Проверить деплой**

Открыть Vercel → твой проект → Deployments → последний деплой → Functions.
Должна появиться функция `api/cron_ai_predict`.

В разделе Cron Jobs (Settings → Cron Jobs) должны быть видны три задачи, включая `0 12 * * *`.

- [ ] **Step 7: Ручное тестирование cron**

Из Vercel Dashboard → Cron Jobs → нажать "Run" рядом с `cron_ai_predict`.

Ожидаемые варианты:
- Если сегодня не игровой день: функция вернёт `200 No open game day today` — это норма
- Если сегодня игровой день: в таблице `predictions` появятся строки от Лёхи AI, в рейтинге дашборда он будет виден

---

## Чеклист покрытия спека

- [x] Виртуальный участник в БД без telegram_id → Task 4 Step 1–2
- [x] Миграция `ALTER TABLE` → Task 4 Step 1
- [x] Сбор турнирного контекста из Supabase → `get_group_standings()`, Task 2
- [x] Проверка идемпотентности → `get_ai_predictions_count_for_game_day()`, Task 2
- [x] Вызов Claude Haiku API → Task 3, `handler.do_GET()`
- [x] Промпт "с характером" → `SYSTEM_PROMPT`, Task 3
- [x] Запись прогнозов через `upsert_prediction()` → Task 3
- [x] Алерт администратору при ошибке → `_send_alert()`, Task 3
- [x] Ранний выход если нет игрового дня → Task 3
- [x] Новый Vercel Cron 12:00 UTC → Task 4 Step 4
- [x] `ANTHROPIC_API_KEY` в конфиге → Task 1
- [x] Тесты для `build_prompt()` → Task 3 Step 1
- [x] Тесты для новых DB-функций → Task 2
