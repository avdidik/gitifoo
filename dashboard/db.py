import os
import pandas as pd
import psycopg
from psycopg.rows import dict_row
import streamlit as st


def _get_db_url() -> str:
    try:
        return st.secrets["DB_URL"]
    except Exception:
        return os.environ.get("DB_URL", "")


def _query(sql: str, params=None) -> pd.DataFrame:
    with psycopg.connect(_get_db_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def get_standings() -> pd.DataFrame:
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
    raw = raw.copy()
    raw["game_date"] = pd.to_datetime(raw["game_date"])
    raw = raw.sort_values(["name", "game_date"])
    raw["cumpoints"] = raw.groupby("name")["day_points"].cumsum()
    return raw


def normalize_accuracy(melted: pd.DataFrame) -> pd.DataFrame:
    totals = melted.groupby("name")["count"].transform("sum")
    result = melted.copy()
    result["pct"] = (result["count"] / totals * 100).round(1)
    return result


@st.cache_data(ttl=300)
def get_matches_predictions() -> pd.DataFrame:
    return _query("""
        SELECT
            m.id          AS match_id,
            m.match_group,
            m.team_home,
            m.team_away,
            m.kickoff_at,
            m.result_home,
            m.result_away,
            p.name        AS participant_name,
            pr.pred_home,
            pr.pred_away,
            s.points
        FROM matches m
        CROSS JOIN participants p
        LEFT JOIN predictions pr
            ON pr.match_id = m.id AND pr.participant_id = p.id
        LEFT JOIN v_scores s
            ON s.match_id = m.id AND s.participant_id = p.id
        ORDER BY m.kickoff_at, p.name
    """)


@st.cache_data(ttl=300)
def get_scores_by_stage() -> pd.DataFrame:
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
