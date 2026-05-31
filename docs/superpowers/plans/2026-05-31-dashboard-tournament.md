# Dashboard — Страница «Турнир» Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Построить страницу «Турнир» Streamlit-дашборда с таблицей очков, race chart, двумя bar-чартами и drill-down по игроку.

**Architecture:** Два модуля — `dashboard/db.py` (SQL-запросы → DataFrame) и `dashboard/app.py` (Streamlit-лейаут + Plotly-чарты). Все запросы кэшируются через `@st.cache_data(ttl=300)`. Деплой на Streamlit Community Cloud из того же GitHub-репозитория.

**Tech Stack:** Python 3.10+, Streamlit, Plotly Express, pandas, psycopg2-binary (уже в requirements.txt)

---

## Файловая структура

```
dashboard/
  app.py            — Streamlit-лейаут, все секции страницы Турнир
  db.py             — SQL-запросы к Supabase, возвращают DataFrame
tests/
  test_dashboard.py — тесты трансформаций данных (без реального DB)
requirements.txt    — добавить streamlit, plotly, pandas
.streamlit/
  secrets.toml      — локальный dev (в .gitignore)
```

---

## Task 1: Зависимости и структура файлов

**Files:**
- Modify: `requirements.txt`
- Create: `dashboard/__init__.py`
- Create: `dashboard/app.py` (заглушка)
- Create: `dashboard/db.py` (заглушка)
- Create: `.streamlit/secrets.toml` (локально, не в git)
- Modify: `.gitignore`

- [ ] **Step 1: Добавить зависимости в requirements.txt**

```
python-telegram-bot==20.7
Flask==3.0.3
psycopg2-binary==2.9.9
pytest==8.2.0
python-dotenv==1.0.1
streamlit==1.35.0
plotly==5.22.0
pandas==2.2.2
```

- [ ] **Step 2: Создать `dashboard/__init__.py`**

Пустой файл.

- [ ] **Step 3: Создать заглушку `dashboard/app.py`**

```python
import streamlit as st

st.set_page_config(page_title="FWC 2026", page_icon="⚽", layout="wide")
st.title("⚽ FWC 2026 — Турнир")
st.info("Загрузка данных...")
```

- [ ] **Step 4: Создать заглушку `dashboard/db.py`**

```python
import os
import pandas as pd
import psycopg2
import psycopg2.extras
import streamlit as st


def _get_db_url() -> str:
    try:
        return st.secrets["DB_URL"]
    except Exception:
        return os.environ.get("DB_URL", "")


def _query(sql: str, params=None) -> pd.DataFrame:
    conn = psycopg2.connect(_get_db_url())
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        conn.close()
```

- [ ] **Step 5: Добавить `.streamlit/secrets.toml` (локально)**

Создать файл `.streamlit/secrets.toml` вручную (не коммитить):
```toml
DB_URL = "postgresql://postgres.ypjbnsksszhhgfougzto:...@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
```
Значение взять из `.env`.

- [ ] **Step 6: Обновить `.gitignore`**

Добавить строку:
```
.streamlit/secrets.toml
```

- [ ] **Step 7: Проверить запуск**

```bash
cd "/Users/avdidik/Проекты с Лёхой/FWC2026"
pip install streamlit plotly pandas
streamlit run dashboard/app.py
```

Ожидаемый результат: браузер открывает страницу с заголовком "⚽ FWC 2026 — Турнир" и текстом "Загрузка данных...".

- [ ] **Step 8: Commit**

```bash
git add requirements.txt dashboard/ .gitignore
git commit -m "feat: dashboard scaffold — app and db stubs"
git push
```

---

## Task 2: DB-модуль — запросы данных

**Files:**
- Modify: `dashboard/db.py`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Написать failing-тест на трансформацию race chart**

```python
# tests/test_dashboard.py
import pandas as pd
from dashboard.db import _build_race_df


def test_build_race_df_cumsum():
    raw = pd.DataFrame({
        "name": ["Андрей", "Андрей", "Лёха", "Лёха"],
        "game_date": ["2026-06-11", "2026-06-12", "2026-06-11", "2026-06-12"],
        "day_points": [3, 1, 2, 3],
    })
    result = _build_race_df(raw)
    andrey = result[result["name"] == "Андрей"].sort_values("game_date")
    assert list(andrey["cumpoints"]) == [3, 4]
    lekha = result[result["name"] == "Лёха"].sort_values("game_date")
    assert list(lekha["cumpoints"]) == [2, 5]
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
pytest tests/test_dashboard.py -v
```

Ожидаемый результат: `ImportError: cannot import name '_build_race_df'`

- [ ] **Step 3: Реализовать все функции в `dashboard/db.py`**

```python
import os
import pandas as pd
import psycopg2
import psycopg2.extras
import streamlit as st


def _get_db_url() -> str:
    try:
        return st.secrets["DB_URL"]
    except Exception:
        return os.environ.get("DB_URL", "")


def _query(sql: str, params=None) -> pd.DataFrame:
    conn = psycopg2.connect(_get_db_url())
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        return pd.DataFrame([dict(r) for r in rows])
    finally:
        conn.close()


@st.cache_data(ttl=300)
def get_standings() -> pd.DataFrame:
    """Rank, name, total_points, exact, diff, winner, miss."""
    return _query("""
        SELECT p.name,
               COALESCE(SUM(s.points), 0)                    AS total_points,
               COUNT(CASE WHEN s.points = 3 THEN 1 END)      AS exact,
               COUNT(CASE WHEN s.points = 2 THEN 1 END)      AS diff,
               COUNT(CASE WHEN s.points = 1 THEN 1 END)      AS winner,
               COUNT(CASE WHEN s.points = 0 THEN 1 END)      AS miss
        FROM participants p
        LEFT JOIN v_scores s ON p.id = s.participant_id
        GROUP BY p.name
        ORDER BY total_points DESC
    """)


@st.cache_data(ttl=300)
def get_daily_points() -> pd.DataFrame:
    """Points per participant per closed game day (for race chart)."""
    raw = _query("""
        SELECT p.name, gd.game_date, COALESCE(SUM(s.points), 0) AS day_points
        FROM participants p
        CROSS JOIN game_days gd
        LEFT JOIN v_scores s ON s.participant_id = p.id AND s.game_day_id = gd.id
        WHERE gd.status = 'closed'
        GROUP BY p.name, gd.game_date
        ORDER BY p.name, gd.game_date
    """)
    if raw.empty:
        return raw
    return _build_race_df(raw)


def _build_race_df(raw: pd.DataFrame) -> pd.DataFrame:
    """Add cumulative points column to daily points DataFrame."""
    raw = raw.copy()
    raw["game_date"] = pd.to_datetime(raw["game_date"])
    raw = raw.sort_values(["name", "game_date"])
    raw["cumpoints"] = raw.groupby("name")["day_points"].cumsum()
    return raw


@st.cache_data(ttl=300)
def get_scores_by_stage() -> pd.DataFrame:
    """Avg points per match per participant per stage (group vs play_off)."""
    return _query("""
        SELECT p.name, m.stage,
               ROUND(AVG(s.points)::numeric, 2) AS avg_points,
               COUNT(*)                          AS matches
        FROM v_scores s
        JOIN participants p ON p.id = s.participant_id
        JOIN matches m ON m.id = s.match_id
        GROUP BY p.name, m.stage
        ORDER BY p.name, m.stage
    """)
```

- [ ] **Step 4: Запустить тест — убедиться что проходит**

```bash
pytest tests/test_dashboard.py -v
```

Ожидаемый результат: `PASSED`

- [ ] **Step 5: Commit**

```bash
git add dashboard/db.py tests/test_dashboard.py
git commit -m "feat: dashboard db module with standings, race, stage queries"
git push
```

---

## Task 3: Таблица очков (Standings)

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Заменить заглушку в app.py на реальный лейаут с таблицей**

```python
import streamlit as st
import pandas as pd
import plotly.express as px
from dashboard.db import get_standings, get_daily_points, get_scores_by_stage

st.set_page_config(page_title="FWC 2026", page_icon="⚽", layout="wide")
st.title("⚽ FWC 2026 — Турнир")

# --- Standings ---
st.subheader("🏆 Таблица очков")
standings = get_standings()

if standings.empty:
    st.info("Данных пока нет — игровые дни ещё не завершены.")
    st.stop()

display = standings.copy()
display.index = range(1, len(display) + 1)
display.index.name = "№"
display.columns = ["Участник", "Очки", "⭐ Точный", "🟢 Разница", "🟡 Победитель", "❌ Мимо"]
st.dataframe(display, use_container_width=True)
```

- [ ] **Step 2: Проверить в браузере**

```bash
streamlit run dashboard/app.py
```

Ожидаемый результат: таблица с данными из БД (если есть закрытые дни) или сообщение "Данных пока нет".

- [ ] **Step 3: Commit**

```bash
git add dashboard/app.py
git commit -m "feat: dashboard standings table"
git push
```

---

## Task 4: Race Chart — накопленные очки

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Добавить race chart после таблицы очков**

```python
# --- Race Chart ---
st.subheader("📈 Гонка очков")
daily = get_daily_points()

if daily.empty:
    st.info("Ещё нет завершённых игровых дней.")
else:
    fig = px.line(
        daily,
        x="game_date",
        y="cumpoints",
        color="name",
        markers=True,
        labels={"game_date": "Дата", "cumpoints": "Очки (накопленные)", "name": "Участник"},
    )
    fig.update_layout(legend_title_text="", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
```

- [ ] **Step 2: Проверить в браузере**

```bash
streamlit run dashboard/app.py
```

Ожидаемый результат: линейный чарт с одной линией на участника (или пустой placeholder).

- [ ] **Step 3: Commit**

```bash
git add dashboard/app.py
git commit -m "feat: dashboard race chart"
git push
```

---

## Task 5: Grouped Bar — сравнение компонентов

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Добавить grouped bar chart**

```python
# --- Component comparison ---
st.subheader("📊 Из чего складываются очки")
melted = standings.melt(
    id_vars=["name"],
    value_vars=["exact", "diff", "winner", "miss"],
    var_name="type",
    value_name="count",
)
melted["type"] = melted["type"].map({
    "exact": "⭐ Точный счёт (3)",
    "diff": "🟢 Разница (2)",
    "winner": "🟡 Победитель (1)",
    "miss": "❌ Мимо (0)",
})
fig2 = px.bar(
    melted,
    x="type",
    y="count",
    color="name",
    barmode="group",
    labels={"type": "", "count": "Кол-во матчей", "name": "Участник"},
)
fig2.update_layout(legend_title_text="")
st.plotly_chart(fig2, use_container_width=True)
```

- [ ] **Step 2: Проверить в браузере**

```bash
streamlit run dashboard/app.py
```

Ожидаемый результат: сгруппированные бары по 4 типам результата.

- [ ] **Step 3: Commit**

```bash
git add dashboard/app.py
git commit -m "feat: dashboard component comparison bar chart"
git push
```

---

## Task 6: Stacked Bar — доля точности

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Написать failing-тест нормализации**

Добавить в `tests/test_dashboard.py`:

```python
from dashboard.app import _normalize_accuracy


def test_normalize_accuracy():
    df = pd.DataFrame({
        "name": ["Андрей", "Андрей", "Лёха", "Лёха"],
        "type": ["exact", "miss", "exact", "miss"],
        "count": [3, 1, 1, 3],
    })
    result = _normalize_accuracy(df)
    andrey = result[result["name"] == "Андрей"]
    assert abs(andrey[andrey["type"] == "exact"]["pct"].values[0] - 75.0) < 0.01
```

- [ ] **Step 2: Запустить — убедиться что падает**

```bash
pytest tests/test_dashboard.py::test_normalize_accuracy -v
```

- [ ] **Step 3: Добавить `_normalize_accuracy` и stacked bar в `dashboard/app.py`**

```python
def _normalize_accuracy(melted: pd.DataFrame) -> pd.DataFrame:
    totals = melted.groupby("name")["count"].transform("sum")
    result = melted.copy()
    result["pct"] = (result["count"] / totals * 100).round(1)
    return result


# --- Accuracy stacked bar ---
st.subheader("🎯 Точность (доля типов)")
normalized = _normalize_accuracy(melted)
fig3 = px.bar(
    normalized,
    x="name",
    y="pct",
    color="type",
    text="pct",
    labels={"name": "Участник", "pct": "%", "type": ""},
    color_discrete_map={
        "⭐ Точный счёт (3)": "#FFD700",
        "🟢 Разница (2)": "#22C55E",
        "🟡 Победитель (1)": "#EAB308",
        "❌ Мимо (0)": "#EF4444",
    },
)
fig3.update_traces(texttemplate="%{text}%", textposition="inside")
fig3.update_layout(barmode="stack", legend_title_text="", yaxis_ticksuffix="%")
st.plotly_chart(fig3, use_container_width=True)
```

- [ ] **Step 4: Запустить тесты**

```bash
pytest tests/test_dashboard.py -v
```

Ожидаемый результат: все тесты PASSED.

- [ ] **Step 5: Проверить в браузере**

```bash
streamlit run dashboard/app.py
```

Ожидаемый результат: 100%-stacked bar с 4 цветами на участника.

- [ ] **Step 6: Commit**

```bash
git add dashboard/app.py tests/test_dashboard.py
git commit -m "feat: dashboard accuracy stacked bar"
git push
```

---

## Task 7: Drill-down по игроку

**Files:**
- Modify: `dashboard/app.py`

- [ ] **Step 1: Добавить drill-down секцию**

```python
# --- Per-player drill-down ---
st.subheader("🔍 Детали по участнику")
players = standings["name"].tolist()
selected = st.selectbox("Выбери участника", players)

p_row = standings[standings["name"] == selected].iloc[0]
total = int(p_row["total_points"])
n_matches = int(p_row[["exact", "diff", "winner", "miss"]].sum())
avg = round(total / n_matches, 2) if n_matches > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Всего очков", total)
col2.metric("Матчей сыграно", n_matches)
col3.metric("Очков за матч (avg)", avg)

# Best / worst game day
daily_player = get_daily_points()
if not daily_player.empty:
    p_daily = daily_player[daily_player["name"] == selected].sort_values("game_date")
    if not p_daily.empty:
        best = p_daily.loc[p_daily["day_points"].idxmax()]
        worst = p_daily.loc[p_daily["day_points"].idxmin()]
        col4, col5 = st.columns(2)
        col4.metric("Лучший день", str(best["game_date"].date()), f"{int(best['day_points'])} очков")
        col5.metric("Худший день", str(worst["game_date"].date()), f"{int(worst['day_points'])} очков")

# Accuracy by stage
stage_df = get_scores_by_stage()
if not stage_df.empty:
    p_stage = stage_df[stage_df["name"] == selected]
    if not p_stage.empty:
        st.write("**Точность по стадии турнира:**")
        stage_display = p_stage[["stage", "avg_points", "matches"]].copy()
        stage_display.columns = ["Стадия", "Avg очков/матч", "Матчей"]
        stage_display["Стадия"] = stage_display["Стадия"].map(
            {"group": "Групповой этап", "play_off": "Плей-офф"}
        )
        st.dataframe(stage_display.set_index("Стадия"), use_container_width=True)
```

- [ ] **Step 2: Проверить в браузере**

```bash
streamlit run dashboard/app.py
```

Ожидаемый результат: дропдаун с именами участников, метрики и таблица по стадиям.

- [ ] **Step 3: Commit**

```bash
git add dashboard/app.py
git commit -m "feat: dashboard per-player drill-down"
git push
```

---

## Task 8: Деплой на Streamlit Community Cloud

**Files:** нет изменений кода

- [ ] **Step 1: Зайти на share.streamlit.io**

Авторизоваться через GitHub (личный аккаунт adidik@yandex.ru).

- [ ] **Step 2: Создать новое приложение**

New app → выбрать репозиторий `gitifoo` → Main file path: `dashboard/app.py` → Deploy.

- [ ] **Step 3: Добавить секрет**

После деплоя: Settings → Secrets → вставить:

```toml
DB_URL = "postgresql://postgres.ypjbnsksszhhgfougzto:...@aws-0-eu-west-1.pooler.supabase.com:5432/postgres"
```

Значение взять из локального `.env`.

- [ ] **Step 4: Перезапустить приложение**

Reboot app → убедиться что дашборд открывается и данные загружаются.
