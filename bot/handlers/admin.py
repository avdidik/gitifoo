from telegram import Update
from telegram.ext import ContextTypes
from bot.db import (
    get_participant, add_participant, get_today_game_day, get_matches_for_game_day,
    set_match_result, get_standings, get_day_scores, add_match, open_game_day,
    resolve_bracket_after_result, get_last_game_day_with_pending_results,
    set_match_winner, get_play_off_match_by_label,
)
from bot.handlers.picker import build_picker_keyboard, build_picker_text, parse_done_callback
from bot.config import ADMIN_ID, GROUP_ID, DASH_URL
from bot.teams import flag
from datetime import date


def _is_admin(user_id: int) -> bool:
    p = get_participant(user_id)
    return p is not None and p["is_admin"]


async def handle_admin_result_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not _is_admin(update.effective_user.id):
        await query.answer("🚫 Только для администратора.", show_alert=True)
        return
    game_day = get_last_game_day_with_pending_results()
    if game_day is None:
        await query.edit_message_text("✅ Все результаты уже внесены.")
        return
    matches = get_matches_for_game_day(game_day["id"])
    if not matches:
        await query.edit_message_text("📭 Матчей нет.")
        return
    idx = next((i for i, m in enumerate(matches) if m["result_home"] is None), 0)
    match = matches[idx]
    home = match["result_home"] or 0
    away = match["result_away"] or 0
    text = "✏️ Внести результат\n\n" + build_picker_text(match, idx, len(matches), home, away)
    keyboard = build_picker_keyboard("r", idx, home, away, len(matches))
    await query.edit_message_text(text, reply_markup=keyboard)


async def handle_picker_callback_admin_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    if not _is_admin(update.effective_user.id):
        await query.answer("🚫 Только для администратора.", show_alert=True)
        return
    mode, match_idx, home, away = parse_done_callback(data)
    game_day = get_last_game_day_with_pending_results()
    if game_day is None:
        await query.edit_message_text("✅ Все результаты уже внесены.")
        return
    matches = get_matches_for_game_day(game_day["id"])
    match = matches[match_idx]
    set_match_result(match["id"], home, away)
    resolve_bracket_after_result(match["id"])

    # Ничья в плей-офф: счёт идёт в зачёт, но сетка не двинется без победителя
    if match["stage"] == "play_off" and home == away:
        await context.bot.send_message(
            update.effective_user.id,
            f"⚠️ Ничья в плей-офф ({match['label']}: {match['team_home']} vs {match['team_away']}).\n"
            f"Кто прошёл по пенальти? Отправьте:\n"
            f"/set_winner {match['label']} <Команда>",
        )

    matches = get_matches_for_game_day(game_day["id"])
    next_match = next((m for m in matches if m["result_home"] is None), None)
    if next_match:
        idx = matches.index(next_match)
        text = "✏️ Внести результат\n\n" + build_picker_text(next_match, idx, len(matches), 0, 0)
        keyboard = build_picker_keyboard("r", idx, 0, 0, len(matches))
        await query.edit_message_text(text, reply_markup=keyboard)
    else:
        scores = get_day_scores(game_day["id"])
        lines = ["📊 Результаты дня:\n"]
        current_label = None
        for row in scores:
            match_label = f"{flag(row['team_home'])} {row['result_home']}:{row['result_away']} {flag(row['team_away'])}"
            if match_label != current_label:
                lines.append(f"\n⚽ {match_label}")
                current_label = match_label
            pts = {3: "⭐", 2: "🟢", 1: "🟡", 0: "❌"}[row["points"]]
            lines.append(f"  {row['name']}: {row['pred_home']}:{row['pred_away']} {pts} {row['points']} pts")
        standings = get_standings()
        lines.append("\n🏆 Турнирная таблица:")
        for i, s in enumerate(standings, 1):
            lines.append(f"  {i}. {s['name']} — {s['total_points']} pts")
        if DASH_URL:
            lines.append(f"\n📊 Статистика: {DASH_URL}")
        await context.bot.send_message(GROUP_ID, "\n".join(lines))
        await query.edit_message_text("✅ Все результаты сохранены.")


async def add_player_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /add_player <telegram_id> <Name>")
        return
    try:
        tg_id = int(args[0])
    except ValueError:
        await update.message.reply_text("telegram_id must be an integer")
        return
    name = " ".join(args[1:])
    add_participant(tg_id, name, is_admin=False)
    await update.message.reply_text(f"✅ Добавлен: {name} (id: {tg_id})")


async def add_match_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 5:
        await update.message.reply_text(
            "Usage: /add_match TeamHome TeamAway YYYY-MM-DD HH:MM stage\n"
            "stage: group|r32|r16|qf|sf|final"
        )
        return
    team_home, team_away, date_str, time_str, stage = args[0], args[1], args[2], args[3], args[4]
    kickoff_at = f"{date_str} {time_str}:00+03:00"
    game_day = get_today_game_day(date_str)
    if game_day is None:
        game_day = open_game_day(date_str)
    add_match(game_day["id"], team_home, team_away, kickoff_at, stage)
    await update.message.reply_text(f"✅ Матч добавлен: {team_home} vs {team_away} {date_str} {time_str}")


async def set_winner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /set_winner <match_id|label> <Команда>\n"
            "Пример: /set_winner A03 Канада\n"
            "Нужно только для плей-офф при ничьей в основное время."
        )
        return
    ident, team = args[0], " ".join(args[1:])
    if ident.isdigit():
        winner_match = set_match_winner(int(ident), team)
    else:
        m = get_play_off_match_by_label(ident)
        winner_match = set_match_winner(m["id"], team) if m else None
    if winner_match is None:
        await update.message.reply_text(f"❌ Матч не найден: {ident}")
        return
    if team not in (winner_match["team_home"], winner_match["team_away"]):
        set_match_winner(winner_match["id"], None)  # откат битого значения
        await update.message.reply_text(
            f"❌ «{team}» не играет в этом матче "
            f"({winner_match['team_home']} vs {winner_match['team_away']})."
        )
        return
    resolve_bracket_after_result(winner_match["id"])
    await update.message.reply_text(
        f"✅ Прошёл дальше: {team} ({winner_match['label']}). Сетка обновлена."
    )


async def standings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    standings = get_standings()
    lines = ["🏆 Турнирная таблица:\n"]
    for i, s in enumerate(standings, 1):
        lines.append(
            f"{i}. {s['name']} — {s['total_points']} pts "
            f"(⭐{s['exact']} 🟢{s['diff']} 🟡{s['winner']} ❌{s['miss']})"
        )
    await update.message.reply_text("\n".join(lines))
