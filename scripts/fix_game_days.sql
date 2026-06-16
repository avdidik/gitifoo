-- Run in Supabase SQL Editor.

-- Fix 1: move matches before 09:00 MSK to the previous day's game_day.
-- Times in DB are stored as MSK with wrong +00 suffix, so EXTRACT(HOUR) gives MSK hour.
-- Rule: 19:00 MSK day D → 08:59 MSK day D+1 = same game session.
UPDATE matches m
SET game_day_id = gd.id
FROM game_days gd
WHERE gd.game_date = (DATE(m.kickoff_at) - INTERVAL '1 day')::date
  AND EXTRACT(HOUR FROM m.kickoff_at) < 9
  AND m.game_day_id != gd.id;

-- Fix 2: close game_days for days where results were entered manually.
-- Adjust the list of dates if needed.
UPDATE game_days
SET status = 'closed'
WHERE game_date IN ('2026-06-11', '2026-06-12')
  AND status != 'closed';
