from telegram.ext import ApplicationBuilder

def formatar_relatorio_telegram(resultados_scrapping: dict):
    if not resultados_scrapping:
        return "⚠️ Nenhuma carta encontrada em estoque nas lojas monitoradas."

    mensagem = "<b>🚀 Relatório de Disponibilidade MTG</b>\n\n"
    encontrou_alguma = False

    for loja, lista_de_cartas in resultados_scrapping.items():
        # Criamos um bloco para a loja, mas só adicionamos se houver estoque
        bloco_loja = f"<b>🏪 LOJA: {loja.upper()}</b>\n"
        tem_estoque_nesta_loja = False

        for sublista in lista_de_cartas:
            for info in sublista:
                # O seu formato parece ser: [Nome, Status, Coleção, Qtd, Preço, Link]
                # Index: 0=Nome, 1=Status, 2=Coleção, 3=Qtd, 4=Preço, 5=Link
                
                if len(info) > 2 and info[1] == 'DISPONÍVEL':
                    nome_carta = info[0]
                    colecao    = info[2]
                    qtd        = info[3]
                    preco      = info[4]
                    link       = info[5]

                    bloco_loja += f"• <a href='{link}'>{nome_carta}</a>\n"
                    bloco_loja += f"  └ 💰 R$ {preco} | 📦 Est: {qtd} | 📔 {colecao}\n"
                    
                    tem_estoque_nesta_loja = True
                    encontrou_alguma = True

        if tem_estoque_nesta_loja:
            mensagem += bloco_loja + "\n"

    if not encontrou_alguma:
        return "⚠️ Nenhuma das cartas buscadas está disponível no momento."
        
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
