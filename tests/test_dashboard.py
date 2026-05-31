import pandas as pd
from dashboard.db import _build_race_df, normalize_accuracy


def test_build_race_df_cumsum():
    raw = pd.DataFrame({
        "name": ["Андрей", "Андрей", "Лёха", "Лёха"],
        "game_date": ["2026-06-11", "2026-06-12", "2026-06-11", "2026-06-12"],
        "day_points": [3, 1, 2, 3],
    })
    result = _build_race_df(raw)
    andrey = result[result["name"] == "Андрей"].sort_values("game_date")
    assert list(andrey["cumpoints"]) == [3, 4]
    lekha = result[result["name"] == "Лёха"].sort_values("game_date")
    assert list(lekha["cumpoints"]) == [2, 5]


def test_normalize_accuracy():
    df = pd.DataFrame({
        "name": ["Андрей", "Андрей", "Лёха", "Лёха"],
        "type": ["exact", "miss", "exact", "miss"],
        "count": [3, 1, 1, 3],
    })
    result = normalize_accuracy(df)
    andrey = result[result["name"] == "Андрей"]
    assert abs(andrey[andrey["type"] == "exact"]["pct"].values[0] - 75.0) < 0.01
