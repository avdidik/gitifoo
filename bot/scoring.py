def calculate_points(pred_home: int, pred_away: int,
                     result_home: int, result_away: int) -> int:
    if pred_home == result_home and pred_away == result_away:
        return 3
    if (pred_home - pred_away) == (result_home - result_away):
        return 2
    if _sign(pred_home - pred_away) == _sign(result_home - result_away):
        return 1
    return 0


def _sign(n: int) -> int:
    if n > 0:
        return 1
    if n < 0:
        return -1
    return 0
