import asyncio
import os
import io
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from bot import *


load_dotenv()


# 1 . Inicia o bot com um /start
# 2 . Passa para o bot uma lista de cartas para busca
# 3 . Bot passa a lista de cartas para o scrapper
# 4 . Scrapper retorna as variáveis para o bot
# 5 . Bot formata a mensagem e manda de volta

# =================================================
#       Função que pega a entrada e ja ajusta
#  independente de ser texto, linha ou arquivo txt
# =================================================
async def processar_entrada(update:Update, context:ContextTypes.DEFAULT_TYPE):
    # Tratamento para arquivo
    if update.message.document:
        
        arquivo = await context.bot.get_file(update.message.document.file_id)
        out = io.BytesIO()

        await arquivo.download_to_memory(out)
        texto_bruto = out.read().decode('utf-8', errors='ignore')
    
    # Tratamento para qualquer texto
    else:
        texto_bruto = update.message.text.replace('/buscar', '').strip()
        
    
    if not texto_bruto:
        await update.message.reply_text('Ainda não recebi nenhum nome ou arquivo com as cartas')
        return
    
    try:
        texto_formatado = formatar_nomes_cartas(texto_bruto)
        print(texto_formatado)
        await update.message.reply_text('Buscando por cartas ...')
    except Exception as e:
        print("ERRO COM O TEXTO: {e}")
        await update.message.reply_text('Houve um erro. Tente novamente.')
        return
    
    if texto_formatado:
        resultados = await raspar_lista_cartas(texto_formatado)
        print(resultados)
        await update.message.reply_text(f'RESULTADOS:\n {resultados}')

