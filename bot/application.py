from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from bot.config import BOT_TOKEN
from bot.handlers.menu import start, show_main_menu
from bot.handlers.predict import handle_predict_entry, handle_picker_callback
from bot.handlers.results import handle_results
from bot.handlers.admin import (
    handle_admin_result_entry, add_player_command, add_match_command,
    standings_command,
)


def build_application() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_player", add_player_command))
    app.add_handler(CommandHandler("add_match", add_match_command))
    app.add_handler(CommandHandler("standings", standings_command))
    app.add_handler(CallbackQueryHandler(handle_predict_entry, pattern=r"^menu\|predict$"))
    app.add_handler(CallbackQueryHandler(handle_results, pattern=r"^menu\|results$"))
    app.add_handler(CallbackQueryHandler(handle_admin_result_entry, pattern=r"^menu\|admin_result$"))
    app.add_handler(CallbackQueryHandler(handle_picker_callback, pattern=r"^(p|r)\|"))
    app.add_handler(CallbackQueryHandler(handle_picker_callback, pattern=r"^nav\|"))
    app.add_handler(CallbackQueryHandler(handle_picker_callback, pattern=r"^done\|"))
    return app
