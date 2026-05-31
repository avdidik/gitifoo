from telegram import Update
from telegram.ext import ContextTypes
from bot.db import (
    get_today_game_day, get_matches_for_game_day,
    get_all_predictions_for_game_day, get_day_scores, get_standings,
)
from bot.teams import flag
from datetime import date


async def handle_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    today = date.today().isoformat()
    game_day = get_today_game_day(today)
    if game_day is None:
        await query.edit_message_text("📭 Сегодня игрового дня нет.")
        return
    matches = get_matches_for_game_day(game_day["id"])
    results_entered = any(m["result_home"] is not None for m in matches)
    if game_day["status"] == "open":
        await query.edit_message_text("🔒 Прогнозы ещё принимаются. Результаты будут доступны после 18:00.")
        return
    if results_entered:
        scores = get_day_scores(game_day["id"])
        lines = ["📊 Результаты дня:\n"]
        current_match = None
        for row in scores:
            match_label = f"{flag(row['team_home'])} {row['result_home']}:{row['result_away']} {flag(row['team_away'])}"
            if match_label != current_match:
                lines.append(f"\n⚽ {match_label}")
                current_match = match_label
            pts = {3: "⭐", 2: "🟢", 1: "🟡", 0: "❌"}[row["points"]]
            lines.append(f"  {row['name']}: {row['pred_home']}:{row['pred_away']} {pts} {row['points']} pts")
        standings = get_standings()
        lines.append("\n🏆 Турнирная таблица:")
        for i, s in enumerate(standings, 1):
            lines.append(
                f"  {i}. {s['name']} — {s['total_points']} pts"
                f" (⭐{s['exact']} 🟢{s['diff']} 🟡{s['winner']} ❌{s['miss']})"
            )
        await query.edit_message_text("\n".join(lines))
    else:
        preds = get_all_predictions_for_game_day(game_day["id"])
        if not preds:
            await query.edit_message_text("📭 Прогнозов пока нет.")
            return
        lines = ["📋 Прогнозы на сегодня:\n"]
        current_match = None
        for row in preds:
            match_label = f"{flag(row['team_home'])} vs {flag(row['team_away'])}"
            if match_label != current_match:
                lines.append(f"\n⚽ {match_label}")
                current_match = match_label
            lines.append(f"  {row['name']}: {row['pred_home']}:{row['pred_away']}")
        await query.edit_message_text("\n".join(lines))
