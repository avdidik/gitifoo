from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bot.teams import flag

MAX_GOALS = 6


def build_picker_keyboard(mode: str, match_idx: int,
                          home: int, away: int,
                          total_matches: int) -> InlineKeyboardMarkup:
    def goal_btn(team: str, value: int) -> InlineKeyboardButton:
        label = f"✓{value}" if (team == "home" and value == home) or \
                               (team == "away" and value == away) else str(value)
        new_h = value if team == "home" else home
        new_a = value if team == "away" else away
        return InlineKeyboardButton(label, callback_data=f"{mode}|{match_idx}|{new_h}|{new_a}")

    home_row = [goal_btn("home", i) for i in range(MAX_GOALS + 1)]
    away_row = [goal_btn("away", i) for i in range(MAX_GOALS + 1)]

    nav_row = []
    if match_idx > 0:
        nav_row.append(InlineKeyboardButton(
            "← Назад",
            callback_data=f"nav|{mode}|{match_idx - 1}|{home}|{away}|{match_idx}"
        ))
    nav_row.append(InlineKeyboardButton(
        "✅ Подтвердить",
        callback_data=f"done|{mode}|{match_idx}|{home}|{away}"
    ))
    if match_idx < total_matches - 1:
        nav_row.append(InlineKeyboardButton(
            "Далее →",
            callback_data=f"nav|{mode}|{match_idx + 1}|{home}|{away}|{match_idx}"
        ))

    return InlineKeyboardMarkup([home_row, away_row, nav_row])


def build_picker_text(match: dict, match_idx: int, total: int,
                      home: int, away: int) -> str:
    from datetime import timezone, timedelta
    MSK = timezone(timedelta(hours=3))
    kickoff = match["kickoff_at"].astimezone(MSK).strftime("%H:%M")
    home_name = flag(match["team_home"])
    away_name = flag(match["team_away"])
    return (
        f"⚽ Матч {match_idx + 1} из {total} — {kickoff}\n"
        f"{home_name}  vs  {away_name}\n\n"
        f"Счёт: {home_name} {home} — {away} {away_name}\n\n"
        f"{home_name} (верхний ряд) / {away_name} (нижний ряд)"
    )


def parse_picker_callback(data: str) -> tuple[str, int, int, int]:
    """Parse 'mode|match_idx|home|away' → (mode, match_idx, home, away)"""
    parts = data.split("|")
    return parts[0], int(parts[1]), int(parts[2]), int(parts[3])


def parse_nav_callback(data: str) -> tuple[str, int, int, int, int]:
    """Parse 'nav|mode|new_idx|old_home|old_away|old_match_idx' → (mode, new_idx, old_home, old_away, old_match_idx)"""
    parts = data.split("|")
    return parts[1], int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])


def parse_done_callback(data: str) -> tuple[str, int, int, int]:
    """Parse 'done|mode|match_idx|home|away' → (mode, match_idx, home, away)"""
    parts = data.split("|")
    return parts[1], int(parts[2]), int(parts[3]), int(parts[4])
