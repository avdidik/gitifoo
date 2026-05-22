from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.db import get_participant, add_participant
from bot.config import ADMIN_ID

MAIN_MENU_TEXT = "⚽ FWC 2026 — выбери действие:"


def main_menu_keyboard(is_admin: bool) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("📝 Мой прогноз", callback_data="menu|predict")],
        [InlineKeyboardButton("📊 Результаты дня", callback_data="menu|results")],
    ]
    if is_admin:
        buttons.append(
            [InlineKeyboardButton("✏️ Внести результат", callback_data="menu|admin_result")]
        )
    return InlineKeyboardMarkup(buttons)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    participant = get_participant(user.id)
    if participant is None:
        is_admin = user.id == ADMIN_ID
        participant = add_participant(user.id, user.full_name, is_admin=is_admin)
    await update.message.reply_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(participant["is_admin"]),
    )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    participant = get_participant(user.id)
    is_admin = participant["is_admin"] if participant else False
    await query.edit_message_text(
        MAIN_MENU_TEXT,
        reply_markup=main_menu_keyboard(is_admin),
    )
