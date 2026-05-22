import psycopg2
import psycopg2.extras
from contextlib import contextmanager
from bot.config import DB_URL


@contextmanager
def get_conn():
    conn = psycopg2.connect(DB_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_participant(telegram_id: int) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM participants WHERE telegram_id = %s", (telegram_id,))
            return cur.fetchone()


def add_participant(telegram_id: int, name: str, is_admin: bool = False) -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO participants (telegram_id, name, is_admin)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (telegram_id) DO UPDATE SET name = EXCLUDED.name
                   RETURNING *""",
                (telegram_id, name, is_admin),
            )
            return cur.fetchone()


def get_today_game_day(date_str: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM game_days WHERE game_date = %s", (date_str,))
            return cur.fetchone()


def open_game_day(date_str: str) -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO game_days (game_date, status) VALUES (%s, 'open')
                   ON CONFLICT (game_date) DO UPDATE SET status = 'open'
                   RETURNING *""",
                (date_str,),
            )
            return cur.fetchone()


def close_game_day(date_str: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE game_days SET status = 'closed' WHERE game_date = %s", (date_str,))


def get_matches_for_game_day(game_day_id: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM matches WHERE game_day_id = %s ORDER BY kickoff_at", (game_day_id,))
            return cur.fetchall()


def add_match(game_day_id: int, team_home: str, team_away: str, kickoff_at: str, stage: str) -> dict:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """INSERT INTO matches (game_day_id, team_home, team_away, kickoff_at, stage)
                   VALUES (%s, %s, %s, %s, %s) RETURNING *""",
                (game_day_id, team_home, team_away, kickoff_at, stage),
            )
            return cur.fetchone()


def upsert_prediction(participant_id: int, match_id: int, pred_home: int, pred_away: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO predictions (participant_id, match_id, pred_home, pred_away)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (participant_id, match_id)
                   DO UPDATE SET pred_home = EXCLUDED.pred_home,
                                 pred_away = EXCLUDED.pred_away,
                                 submitted_at = now()""",
                (participant_id, match_id, pred_home, pred_away),
            )


def get_prediction(participant_id: int, match_id: int) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM predictions WHERE participant_id=%s AND match_id=%s",
                (participant_id, match_id),
            )
            return cur.fetchone()


def get_all_predictions_for_game_day(game_day_id: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT p.name, pr.pred_home, pr.pred_away,
                          m.team_home, m.team_away, m.kickoff_at, m.id as match_id
                   FROM predictions pr
                   JOIN participants p ON pr.participant_id = p.id
                   JOIN matches m ON pr.match_id = m.id
                   WHERE m.game_day_id = %s
                   ORDER BY m.kickoff_at, p.name""",
                (game_day_id,),
            )
            return cur.fetchall()


def set_match_result(match_id: int, result_home: int, result_away: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE matches SET result_home=%s, result_away=%s WHERE id=%s",
                (result_home, result_away, match_id),
            )


def get_standings() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT p.name, COALESCE(SUM(s.points), 0) AS total_points,
                          COUNT(CASE WHEN s.points=3 THEN 1 END) AS exact,
                          COUNT(CASE WHEN s.points=2 THEN 1 END) AS diff,
                          COUNT(CASE WHEN s.points=1 THEN 1 END) AS winner,
                          COUNT(CASE WHEN s.points=0 THEN 1 END) AS miss
                   FROM participants p
                   LEFT JOIN v_scores s ON p.id = s.participant_id
                   GROUP BY p.name
                   ORDER BY total_points DESC"""
            )
            return cur.fetchall()


def get_day_scores(game_day_id: int) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """SELECT p.name, m.id as match_id, m.team_home, m.team_away,
                          pr.pred_home, pr.pred_away,
                          m.result_home, m.result_away, s.points
                   FROM v_scores s
                   JOIN participants p ON s.participant_id = p.id
                   JOIN matches m ON s.match_id = m.id
                   JOIN predictions pr ON pr.participant_id = s.participant_id
                                      AND pr.match_id = s.match_id
                   WHERE s.game_day_id = %s
                   ORDER BY m.kickoff_at, p.name""",
                (game_day_id,),
            )
            return cur.fetchall()
