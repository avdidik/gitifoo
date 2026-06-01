import pytest
from bot.ai_prompt import build_prompt


def test_build_prompt_includes_match_ids():
    matches = [
        {"id": 42, "team_home": "Бразилия", "team_away": "Германия"},
        {"id": 43, "team_home": "Франция", "team_away": "Аргентина"},
    ]
    prompt = build_prompt(matches, [])
    assert "match_id=42" in prompt
    assert "Бразилия vs Германия" in prompt
    assert "match_id=43" in prompt
    assert "Франция vs Аргентина" in prompt


def test_build_prompt_with_standings():
    matches = [{"id": 1, "team_home": "Бразилия", "team_away": "Германия"}]
    standings = [
        {"match_group": "E", "team": "Бразилия", "pts": 6, "gf": 5, "ga": 1},
        {"match_group": "E", "team": "Германия", "pts": 4, "gf": 3, "ga": 2},
        {"match_group": "F", "team": "Франция", "pts": 3, "gf": 2, "ga": 0},
    ]
    prompt = build_prompt(matches, standings)
    assert "Группа E" in prompt
    assert "Бразилия — 6 очков" in prompt
    assert "Германия — 4 очков" in prompt
    assert "Группа F" in prompt


def test_build_prompt_no_standings_message():
    matches = [{"id": 5, "team_home": "США", "team_away": "Мексика"}]
    prompt = build_prompt(matches, [])
    assert "только начался" in prompt


def test_build_prompt_contains_format_instruction():
    matches = [{"id": 1, "team_home": "X", "team_away": "Y"}]
    prompt = build_prompt(matches, [])
    assert "pred_home" in prompt
    assert "pred_away" in prompt
