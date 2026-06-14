from telegram import Update
from telegram.ext import ContextTypes
from bot.db import (
    get_participant, get_today_game_day, get_matches_for_game_day,
    upsert_prediction, get_prediction, get_last_game_day_with_pending_results,
    set_match_result, resolve_bracket_after_result,
)
from bot.handlers.picker import (
    build_picker_keyboard, build_picker_text,
    parse_picker_callback, parse_nav_callback, parse_done_callback,
)
from datetime import date


async def handle_predict_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    today = date.today().isoformat()
    game_day = get_today_game_day(today)
    if game_day is None or game_day["status"] != "open":
        await query.edit_message_text("🚫 Сегодня окно прогнозов закрыто (принимаем с 9:00 до 18:00).")
        return
    matches = get_matches_for_game_day(game_day["id"])
    if not matches:
        await query.edit_message_text("📭 На сегодня матчей не запланировано.")
        return
    participant = get_participant(update.effective_user.id)
    if participant is None:
        await query.edit_message_text("❌ Ты не зарегистрирован. Напиши /start.")
        return
    await _show_match(query, matches, 0, participant["id"], mode="p")


async def handle_picker_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    participant = get_participant(update.effective_user.id)

    mode_prefix = data.split("|")[0]
    raw_mode = data.split("|")[1] if mode_prefix in ("nav", "done") else data.split("|")[0]

    if raw_mode == "r":
        game_day = get_last_game_day_with_pending_results()
    else:
        today = date.today().isoformat()
        game_day = get_today_game_day(today)

    if game_day is None:
        await query.edit_message_text("🚫 Нет активного игрового дня.")
        return
    matches = get_matches_for_game_day(game_day["id"])

    if data.startswith("nav|"):
        mode, new_idx, old_home, old_away, old_match_idx = parse_nav_callback(data)
        if mode == "r" and (not participant or not participant["is_admin"]):
            await query.answer("🚫 Только для администратора.", show_alert=True)
            return
        if mode == "r":
            set_match_result(matches[old_match_idx]["id"], old_home, old_away)
            resolve_bracket_after_result(matches[old_match_idx]["id"])
        if mode == "p" and participant and game_day["status"] == "open":
            upsert_prediction(participant["id"], matches[old_match_idx]["id"], old_home, old_away)
        await _show_match(query, matches, new_idx, participant["id"] if participant else None, mode)

    elif data.startswith("done|"):
        mode, match_idx, home, away = parse_done_callback(data)
        if mode == "p":
            if participant and game_day["status"] == "open":
                upsert_prediction(participant["id"], matches[match_idx]["id"], home, away)
            await _show_prediction_summary(query, matches, participant)
        elif mode == "r":
            from bot.handlers.admin import handle_picker_callback_admin_done
            await handle_picker_callback_admin_done(update, context)

    else:
        mode, match_idx, home, away = parse_picker_callback(data)
        if mode == "r" and (not participant or not participant["is_admin"]):
            await query.answer("🚫 Только для администратора.", show_alert=True)
            return
        match = matches[match_idx]
        text = build_picker_text(match, match_idx, len(matches), home, away)
        keyboard = build_picker_keyboard(mode, match_idx, home, away, len(matches))
        await query.edit_message_text(text, reply_markup=keyboard)


async def _show_match(query, matches: list, idx: int,
                      participant_id: int | None, mode: str):
    match = matches[idx]
    home, away = 0, 0
    if mode == "r":
        home = match["result_home"] or 0
        away = match["result_away"] or 0
    elif participant_id:
        existing = get_prediction(participant_id, match["id"])
        if existing:
            home, away = existing["pred_home"], existing["pred_away"]
    text = build_picker_text(match, idx, len(matches), home, away)
    keyboard = build_picker_keyboard(mode, idx, home, away, len(matches))
    await query.edit_message_text(text, reply_markup=keyboard)


async def _show_prediction_summary(query, matches: list, participant: dict):
    lines = ["✅ Твои прогнозы на сегодня:\n"]
    for m in matches:
        pred = get_prediction(participant["id"], m["id"])
        if pred:
            lines.append(f"  {m['team_home']} {pred['pred_home']}:{pred['pred_away']} {m['team_away']}")
        else:
            lines.append(f"  {m['team_home']} — нет прогноза — {m['team_away']}")
    await query.edit_message_text("\n".join(lines))
