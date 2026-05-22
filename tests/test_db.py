import pytest
from bot.db import add_participant, get_participant, open_game_day, get_today_game_day

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
