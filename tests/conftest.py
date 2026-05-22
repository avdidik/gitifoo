import os
import pytest
import psycopg2
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture(scope="session")
def db_conn():
    conn = psycopg2.connect(os.environ["DB_URL"])
    yield conn
    conn.close()
