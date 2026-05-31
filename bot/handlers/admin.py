from telegram import Update
from telegram.ext import ContextTypes
from bot.db import (
    get_participant, add_participant, get_today_game_day, get_matches_for_game_day,
    set_match_result, get_standings, get_day_scores, add_match, open_game_day,
    resolve_bracket_after_result,
)
from bot.handlers.picker import build_picker_keyboard, build_picker_text, parse_done_callback
from bot.config import ADMIN_ID, GROUP_ID
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
    today = date.today().isoformat()
    game_day = get_today_game_day(today)
    if game_day is None:
        await query.edit_message_text("📭 Сегодня нет игрового дня.")
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
    today = date.today().isoformat()
    game_day = get_today_game_day(today)
    matches = get_matches_for_game_day(game_day["id"])
    match = matches[match_idx]
    set_match_result(match["id"], home, away)
    resolve_bracket_after_result(match["id"])
    scores = get_day_scores(game_day["id"])
    lines = [f"✅ Результат: {match['team_home']} {home}:{away} {match['team_away']}\n"]
    lines.append("📊 Очки за матч:")
    for row in scores:
        if row["match_id"] == match["id"]:
            pts = {3: "⭐", 2: "🟡", 1: "🟢", 0: "❌"}[row["points"]]
            lines.append(f"  {row['name']}: {row['pred_home']}:{row['pred_away']} {pts} {row['points']} pts")
    standings = get_standings()
    lines.append("\n🏆 Турнирная таблица:")
    for i, s in enumerate(standings, 1):
        lines.append(f"  {i}. {s['name']} — {s['total_points']} pts")
    await context.bot.send_message(GROUP_ID, "\n".join(lines))
    await query.edit_message_text("✅ Результат сохранён, итоги отправлены в группу.")


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


async def standings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    standings = get_standings()
    lines = ["🏆 Турнирная таблица:\n"]
    for i, s in enumerate(standings, 1):
        lines.append(
            f"{i}. {s['name']} — {s['total_points']} pts "
            f"(⭐{s['exact']} 🟡{s['diff']} 🟢{s['winner']} ❌{s['miss']})"
        )
    await update.message.reply_text("\n".join(lines))
