import pytest
from bot.db import add_participant, get_participant, open_game_day, get_today_game_day
from bot.db import (
    get_ai_participant, get_group_standings, get_ai_predictions_count_for_game_day,
)

TEST_TG_ID = 9999999999


def test_add_and_get_participant():
    p = add_participant(TEST_TG_ID, "TestUser", is_admin=False)
    assert p["telegram_id"] == TEST_TG_ID
    assert p["name"] == "TestUser"
    fetched = get_participant(TEST_TG_ID)
    assert fetched is not None
    assert fetched["name"] == "TestUser"


def test_get_participant_missing():
    result = get_participant(0)
    assert result is None


def test_open_game_day():
    gd = open_game_day("2099-01-01")
    assert gd["status"] == "open"
    assert str(gd["game_date"]) == "2099-01-01"
    fetched = get_today_game_day("2099-01-01")
    assert fetched is not None
    assert fetched["status"] == "open"


def test_get_ai_participant():
    # Requires: migration already run in Supabase (ALTER TABLE + INSERT Лёха AI)
    # Skip with a clear message if Лёха AI not in DB yet
    ai = get_ai_participant()
    if ai is None:
        import pytest
        pytest.skip("Лёха AI not in DB yet — run Supabase migration first")
    assert ai["name"] == "Лёха AI"
    assert ai["telegram_id"] is None


def test_get_group_standings_returns_list():
    standings = get_group_standings()
    assert isinstance(standings, list)
    if standings:
        row = standings[0]
        assert "match_group" in row
        assert "team" in row
        assert "pts" in row
        assert "gf" in row
        assert "ga" in row


def test_get_ai_predictions_count_no_predictions():
    count = get_ai_predictions_count_for_game_day(999999, 999999)
    assert count == 0
