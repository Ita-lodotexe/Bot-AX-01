import asyncio
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler

from bot import *
from telegram_bot import *

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')



def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('buscar', processar_entrada))

    print("Bot rodando... Pressione Ctrl+C para parar.")
    app.run_polling()

    



if __name__ == "__main__":
    main()