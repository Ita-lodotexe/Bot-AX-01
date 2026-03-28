from telegram.ext import ApplicationBuilder

def formatar_relatorio_telegram(resultados_scrapping:dict):
    if not resultados_scrapping:
        return "⚠️ Nenhuma carta encontrada em estoque nas lojas monitoradas."

    mensagem = "<b>🚀 Relatório de Disponibilidade MTG</b>\n\n"
    
    for loja, cartas in resultados_scrapping.items():
        mensagem += f"<b>🏪 LOJA: {loja.upper()}</b>\n"
        
        for nome_carta, info in cartas.items():
            if len(info) > 1:
                colecao = info[1]
                qtd = info[2]
                preco = info[3]
                link = info[4]

                mensagem += f"• <a href='{link}'>{nome_carta}</a>\n"
                mensagem += f"  └ 💰 R$ {preco} | 📦 Est: {qtd} | 📔 {colecao}\n"
        
        mensagem += "\n" # Espaço entre lojas
        
    return mensagem




async def enviar_notificacao_telegram(dicionario_lojas, token, chat_id):
    app = ApplicationBuilder().token(token).build()

    texto_final = formatar_relatorio_telegram(dicionario_lojas)
    
    async with app:
        await app.bot.send_message(
            chat_id=chat_id, 
            text=texto_final, 
            parse_mode='HTML',
            disable_web_page_preview=True # Evita que o Telegram tente carregar o preview de todos os links
        )
    print("✅ Notificação enviada para o Telegram!")
