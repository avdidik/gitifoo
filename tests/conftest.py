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
