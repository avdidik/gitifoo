# FWC 2026 Prediction Contest — Design Doc

**Date:** 2026-05-22  
**Status:** Approved

---

## Overview

A Telegram-based prediction contest platform for 4 friends across different cities during the 2026 FIFA World Cup. Participants submit score predictions for each day's matches via a Telegram bot; an admin enters results; the system calculates points and displays statistics on a Streamlit dashboard.

---

## Constraints

- **Participants:** 4 people (1 admin + 3 players), different cities
- **Budget:** Free (no credit card required)
- **Tech profile:** Admin is an analyst/DS — comfortable with Python and SQL, no backend/deploy experience
- **Duration:** ~2 months (WC 2026 group + knockout stages, ~80 matches)

---

## Tech Stack

| Component | Service | Notes |
|---|---|---|
| Telegram Bot | Vercel (webhook mode) | Free Hobby plan, no credit card |
| Database | Supabase (PostgreSQL) | Free tier, 500MB, no credit card |
| Dashboard | Streamlit Community Cloud | Free, deploys from GitHub |

**Why Vercel over Fly.io:** Russian-issued bank cards are blocked on Fly.io due to sanctions. Vercel Hobby plan requires only a GitHub account.

**Bot library:** `python-telegram-bot` v20+ (async, webhook-compatible)

---

## Scoring Rules

| Result | Points |
|---|---|
| Exact score (e.g. predicted 2:1, result 2:1) | 3 |
| Correct goal difference (e.g. predicted 2:1, result 1:0) | 2 |
| Correct draw (e.g. predicted 1:1, result 0:0) | 2 |
| Correct winner, wrong score | 1 |
| Wrong winner or predicted draw but team won | 0 |

---

## Game Day Flow

- **Prediction window:** opens automatically at **09:00**, closes at **18:00** (Vercel Cron)
- **Matches:** played between 18:00 and 09:00 (evening/overnight), up to 5 per day
- **On open (09:00):** bot posts list of today's matches to group chat, accepts predictions in private
- **On close (18:00):** bot stops accepting predictions, publishes all participants' predictions to group
- **Results:** admin enters them via bot anytime during the next day's prediction window (09:00–18:00); bot posts points breakdown to group immediately after each result is entered

---

## Telegram Bot

### Roles

- **Participant:** can submit predictions, view results
- **Admin:** same as participant, plus can enter match results

### Main Menu

Inline keyboard shown on `/start` or any unrecognized message:

```
[📝 Мой прогноз]
[📊 Результаты дня]
[✏️ Внести результат]   ← admin only
```

### Prediction / Result Entry UI (shared component)

One match at a time, bot edits the same message in place (no new messages):

```
⚽ Матч 2 из 3 — 15 июня, 21:00
🇫🇷 France vs Germany 🇩🇪

  France:  [0] [1] [✓2] [3] [4] [5+]
  Germany: [✓1] [2] [3]  [4] [5] [6+]

  Твой прогноз: France 2 — 1 Germany

  [← Назад]        [Далее →]
```

- Score selected via inline buttons (no free-text input → no DB errors)
- "Далее" saves current match and advances to next
- After last match: bot shows summary and returns to main menu
- **Admin result entry** uses the same component; on confirmation it calculates points and posts results to the group

### Commands (admin, group chat)

| Command | Action |
|---|---|
| `/add_match France Germany 2026-06-15 21:00` | Add a knockout match to the schedule |
| `/standings` | Post current standings to group |

Cron-triggered actions (no command needed):
- `09:00` → open predictions, post match list to group
- `18:00` → close predictions, post all predictions to group

### Participant Registration

Admin registers all 4 participants once at setup via `/add_player @username Name`. The bot stores their Telegram ID and display name. No self-registration flow — the participant list is fixed and known in advance.

---

## Database Schema (Supabase / PostgreSQL)

```sql
CREATE TABLE participants (
  id          SERIAL PRIMARY KEY,
  telegram_id BIGINT UNIQUE NOT NULL,
  name        TEXT NOT NULL,
  is_admin    BOOLEAN DEFAULT false
);

CREATE TABLE game_days (
  id          SERIAL PRIMARY KEY,
  game_date   DATE UNIQUE NOT NULL,
  status      TEXT DEFAULT 'pending'  -- pending | open | closed
);

CREATE TABLE matches (
  id           SERIAL PRIMARY KEY,
  game_day_id  INT REFERENCES game_days(id),
  team_home    TEXT NOT NULL,
  team_away    TEXT NOT NULL,
  kickoff_at   TIMESTAMPTZ NOT NULL,
  stage        TEXT NOT NULL,  -- group | r32 | r16 | qf | sf | final
  result_home  INT,            -- NULL until entered by admin
  result_away  INT             -- NULL until entered by admin
);

CREATE TABLE predictions (
  id             SERIAL PRIMARY KEY,
  participant_id INT REFERENCES participants(id),
  match_id       INT REFERENCES matches(id),
  pred_home      INT NOT NULL,
  pred_away      INT NOT NULL,
  submitted_at   TIMESTAMPTZ DEFAULT now(),
  UNIQUE(participant_id, match_id)
);
```

**Scores view** (no separate table — computed on read):

```sql
CREATE VIEW v_scores AS
SELECT
  p.participant_id,
  p.match_id,
  CASE
    WHEN p.pred_home = m.result_home
     AND p.pred_away = m.result_away         THEN 3
    WHEN (p.pred_home - p.pred_away)
       = (m.result_home - m.result_away)     THEN 2
    WHEN SIGN(p.pred_home - p.pred_away)
       = SIGN(m.result_home - m.result_away) THEN 1
    ELSE                                          0
  END AS points
FROM predictions p
JOIN matches m ON p.match_id = m.id
WHERE m.result_home IS NOT NULL;
```

**Initial data load:** group stage schedule (all 48 matches) loaded from CSV at setup time. Knockout matches added by admin via `/add_match` as the bracket fills.

---

## Streamlit Dashboard

Two pages.

### Page 1 — Турнир

1. **Standings table** — rank, name, total points, count of ⭐3 / 🟢2 / 🟡1 / ❌0
2. **Race chart** — line chart, accumulated points per participant over game days
3. **Component comparison** — grouped bar chart: 4 groups (⭐🟢🟡❌), one bar per participant per group; shows who excels at exact scores vs. picking winners
4. **Accuracy stacked bar** — share of ⭐/🟢/🟡/❌ per participant (100% stacked)
5. **Per-player drill-down** — dropdown to select participant; shows: avg points/match, best/worst game day, accuracy by stage (group vs knockout)

### Page 2 — Матчи

1. **Upcoming game day** — list of today's matches with kickoff times; predictions shown as "скрыты до 18:00" before close, then revealed
2. **Match history** — table of all completed matches with each participant's prediction and points earned; filterable by stage and participant

---

## What the Admin Needs to Set Up (One-Time)

1. Create a Telegram bot via @BotFather → get bot token
2. Create a GitHub repo and push the code
3. Create a Supabase project → get connection string, run schema SQL
4. Create a Vercel account (GitHub login) → deploy bot as serverless function, set Vercel Cron for 09:00 and 18:00, add env vars (bot token, DB URL)
5. Connect Streamlit Community Cloud to GitHub repo → add DB connection string as secret

Total setup time estimate: ~2–3 hours.

---

## Out of Scope

- Automatic match result fetching via external API (admin enters manually)
- Mobile app or web frontend beyond Streamlit
- Payment or prize tracking
- Historical data from previous tournaments
