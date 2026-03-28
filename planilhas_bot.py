import os
import asyncio
from datetime import datetime

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

CREDENTIALS_FILE= os.getenv('GOOGLE_CREDENTIALS')
SHEET_NAME = os.getenv('SHEET_NAME')

def conectar_planilha():
    scope = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
    ]

    cred = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
    client = gspread.authorize(cred)

    planilha = client.open(SHEET_NAME)
    aba_busca = planilha.worksheet("BUSCA")
    aba_resultados = planilha.worksheet("RESULTADOS")   

    # cria um cabeçalho se a planilha estiver vazia.
    if not aba_resultados.row_values(1):
        aba_resultados.append_row(
            ['NOME DA LOJA','CARTA','DISPONÍVEL?','COLEÇÃO','QUANTIDADE','PREÇO','LINK'],
            value_input_option='USER_ENTERED'
        )
        print('Cabeçalho criado na planilha.')
    return aba_resultados, aba_busca



def salvar_planilha(aba, resultados:dict):
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')
    linhas = []

    for nome_loja, inventario in resultados.items():
        print(f"\n🏪 Loja: {nome_loja}")

        for nome_carta, detalhes in inventario.items():
            mensagem_saída = detalhes[0]
            if len(detalhes) > 1:
                colecao = detalhes[1]
                qtd = detalhes[2]
                preco = detalhes[3]
                link_carta = detalhes[4]

                print(f'{nome_carta}: {mensagem_saída}|{colecao}|{qtd}|r${preco}')
                linha = [str(nome_loja).capitalize(), nome_carta, mensagem_saída, colecao, qtd, preco,link_carta]
                linhas.append(linha)
            else:    
                print(f'{nome_carta}: {mensagem_saída}')
                linha = [str(nome_loja).capitalize(), nome_carta, mensagem_saída]
                linhas.append(linha)
    aba.append_rows(linhas, value_input_option='USER_ENTERED')
    print(f'{len(linhas)} linhas adicionadas na planilha.')




def ler_da_planilha(aba_busca):
    valores_coluna = aba_busca.col_values(1)

    print(f'Valores coluna: {valores_coluna}')

    if len(valores_coluna) <= 1:
        print("Planilha de busca está vazia ou só tem o cabeçalho.")
        return []

    decklist = valores_coluna[1:]
    print(f'Decklist da planilha:{decklist}')

    return decklist