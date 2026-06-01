CREATE TABLE participants (
  id          SERIAL PRIMARY KEY,
  telegram_id BIGINT UNIQUE,  -- NULL для AI-участников
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
  stage        TEXT NOT NULL,  -- group | play_off
  label        TEXT,           -- bracket id: A01..A16, B01..B08, QF1..QF4, SF1, SF2, F1, F3
  match_group  TEXT,           -- group letter A-L (group stage only)
  result_home  INT,
  result_away  INT
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

CREATE VIEW v_scores AS
SELECT
  p.participant_id,
  p.match_id,
  m.game_day_id,
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

-- Migration 2026-06-01: allow NULL telegram_id for AI participants
-- ALTER TABLE participants ALTER COLUMN telegram_id DROP NOT NULL;
-- INSERT INTO participants (telegram_id, name) VALUES (NULL, 'Лёха AI');
