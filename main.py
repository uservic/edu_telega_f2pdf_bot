import os
import logging

from bot import TelegramBot, OUTPUT_FILE_NAME, MAIL, UPLOAD_PHOTO, PHOTO_ADDED
from dotenv import load_dotenv
from email_sender import EmailSender, MailServerConnectionConfig

from telegram.ext import CommandHandler, ConversationHandler, MessageHandler, filters

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def create_and_configure_bot():
    load_dotenv()
    bot_token = os.getenv('BOT_TOKEN')
    em_sender = EmailSender(create_yandex_mail_server_connection_config())

    tb = TelegramBot(em_sender, bot_token=bot_token)
    tb.app.add_handlers(get_handlers(tb))

    return tb


def get_handlers(tb: TelegramBot):
    h = [
        ConversationHandler(
            entry_points=[CommandHandler("start", tb.start)],
            states={
                OUTPUT_FILE_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, tb.store_output_file_name)
                ],
                UPLOAD_PHOTO: [
                    MessageHandler(filters.ALL, tb.upload_photo),
                    CommandHandler("exit", tb.exit)
                ],
                PHOTO_ADDED: [
                    CommandHandler("f", tb.process_on_finish_upload),
                    MessageHandler(filters.ALL, tb.upload_photo),
                    CommandHandler("exit", tb.exit)
                ],
                MAIL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, tb.send_email),
                    CommandHandler("exit", tb.exit)
                ]
            },
            fallbacks=[CommandHandler("exit", tb.exit)],
        ),
        MessageHandler(filters.TEXT, tb.unknown_command),
        CommandHandler("exit", tb.exit)
    ]

    return h


def create_yandex_mail_server_connection_config():
    return MailServerConnectionConfig(
        smtp_socket=os.getenv('YANDEX_SMTP_SSL'),
        from_addr=os.getenv('YANDEX_MAIL_ADDRESS'),
        login=os.getenv('YANDEX_MAIL_LOGIN'),
        passw=os.getenv('YANDEX_MAIL_PASSWORD')
    )


if __name__ == "__main__":
    bot = create_and_configure_bot()
    bot.run()
