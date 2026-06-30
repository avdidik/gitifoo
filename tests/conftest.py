import os
import sys
import pytest
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

@pytest.fixture(scope="session")
def db_conn():
    conn = psycopg2.connect(os.environ["DB_URL"])
    yield conn
    conn.close()


# Артефакты, которые тесты создают в боевой Supabase
TEST_TG_ID = 9999999999
TEST_GAME_DATE = "2099-01-01"


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_artifacts():
    """После всего прогона удаляет тестовые строки из БД (FK-безопасный порядок),
    чтобы они не накапливались в боевой базе."""
    yield
    conn = psycopg2.connect(os.environ["DB_URL"])
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(
            "DELETE FROM predictions WHERE participant_id IN "
            "(SELECT id FROM participants WHERE telegram_id = %s)",
            (TEST_TG_ID,),
        )
        cur.execute(
            "DELETE FROM matches WHERE game_day_id IN "
            "(SELECT id FROM game_days WHERE game_date = %s)",
            (TEST_GAME_DATE,),
        )
        cur.execute("DELETE FROM game_days WHERE game_date = %s", (TEST_GAME_DATE,))
        cur.execute("DELETE FROM participants WHERE telegram_id = %s", (TEST_TG_ID,))
    conn.close()
