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
