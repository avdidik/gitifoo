import pytest
from bot.scoring import calculate_points


@pytest.mark.parametrize("ph, pa, rh, ra, expected", [
    (2, 1, 2, 1, 3),   # exact score
    (0, 0, 0, 0, 3),
    (3, 2, 3, 2, 3),
    (2, 1, 1, 0, 2),   # same diff (both home win by 1)
    (1, 1, 2, 2, 2),   # both draws
    (2, 0, 3, 1, 2),   # both home win by 2
    (1, 3, 0, 2, 2),   # both away win by 2
    (2, 0, 1, 0, 1),   # correct winner, different diff
    (0, 2, 0, 1, 1),
    (1, 0, 3, 0, 1),
    (2, 0, 0, 1, 0),   # wrong winner
    (1, 1, 2, 0, 0),   # predicted draw, home won
    (0, 1, 1, 0, 0),   # predicted away, home won
])
def test_calculate_points(ph, pa, rh, ra, expected):
    assert calculate_points(ph, pa, rh, ra) == expected
