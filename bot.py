import logging

from collections import defaultdict
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ApplicationBuilder, ConversationHandler, ContextTypes
from io import BytesIO
from converter import PDFConverter
from email_sender import MailMessageData

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

OUTPUT_FILE_NAME, UPLOAD_PHOTO, PHOTO_ADDED, MAIL = range(4)


class TelegramBot:
    def __init__(self, msg_sender, bot_token=None):
        if bot_token is None:
            raise ValueError('Bot token is missing!')

        self.msg_sender = msg_sender
        self.app = ApplicationBuilder().token(bot_token).build()
        self.user_ids_to_file_ids = defaultdict(list)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text(
            "Hi! I'm PHOTOS to PDF converter bot.\n"
            "Send /exit to stop talking to me.\n\n"
            "Please, enter result PDF filename:"
        )

        return OUTPUT_FILE_NAME

    async def store_output_file_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        text = update.message.text
        context.user_data["output_file_name"] = text
        await update.message.reply_text("Please, upload photos one by one for merging and converting to pdf:")

        return UPLOAD_PHOTO

    async def upload_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        u_id = update.message.from_user.id
        photo = update.message.photo[-1]

        self.user_ids_to_file_ids[u_id].append(photo.file_id)

        await update.message.reply_text("Photo successfully added.\n\nAdd more or use /f to finish uploading.")

        return PHOTO_ADDED

    async def process_on_finish_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        await update.message.reply_text("Processing...")

        u_id = update.message.from_user.id
        file_id_list = self.user_ids_to_file_ids.get(u_id)
        image_byte_list = []
        for fid in file_id_list:
            file = await context.bot.get_file(fid)
            as_bytearray = await file.download_as_bytearray()
            image_byte_list.append(as_bytearray)

        bytes_obj_result = self.__class__.convert(image_byte_list, update)

        context.user_data['pdf_result'] = bytes_obj_result

        await self.send_converted_to_user(update, context, bytes_obj_result)

        await update.message.reply_text("Please, enter your email:")

        return MAIL

    async def send_converted_to_user(self, update: Update, context, bytes_obj: BytesIO):
        output_file_name = context.user_data["output_file_name"]
        await context.bot.send_document(
            update.message.chat_id, document=bytes_obj.getvalue(), filename=output_file_name + '.pdf'
        )
        await update.message.reply_text("Photos successfully converted.\n")

    async def send_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        to_email = update.message.text
        await update.message.reply_text(f"Sending result to {to_email} ...")
        try:
            pdf_bytes_obj = context.user_data['pdf_result']
            result_file_name = context.user_data["output_file_name"] + '.pdf'
            await self.send_email_internal(to_email, pdf_bytes_obj, result_file_name)
        except Exception as ex:
            logger.error(f"Error while sending email to {to_email}", exc_info=ex)
            await update.message.reply_text(f"Error while sending email to {to_email}")
        else:
            await update.message.reply_text(f"Result file is successfully sent to {to_email} \n\nBye!")

        self.cleanup(update, context)

        return ConversationHandler.END

    @staticmethod
    def convert(img_bytes: list, update: Update):
        res = None
        try:
            conv = PDFConverter()
            res = conv.convert_images(img_bytes)
        except Exception as ex:
            logger.error("Error while converting images to pdf", exc_info=ex)
            update.message.reply_text("Error while converting images to pdf.")

        return res

    async def send_email_internal(self, to_addr: str, data_to_send: BytesIO, result_name: str):
        md = MailMessageData(to_addr,
                             data_to_send,
                             main_text='Look for pdf result file it attachment.',
                             subject='Merged pdf',
                             result_file_name=result_name)
        await self.msg_sender.try_send(md)

    async def exit(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s canceled the conversation.", user.first_name)
        await update.message.reply_text(
            "Bye! Hope to see you soon!", reply_markup=ReplyKeyboardRemove()
        )
        self.cleanup(update, context)

        return ConversationHandler.END

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text("Sorry, I didn't understand that command.")

    def cleanup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        context.user_data.clear()
        self.user_ids_to_file_ids.pop(update.message.from_user.id, None)

    def run(self):
        self.app.run_polling()
