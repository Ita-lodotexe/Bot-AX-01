from playwright.async_api import async_playwright
import requests
import asyncio
import re
from dotenv import load_dotenv

# IMPORTS DE MODULO
from planilhas_bot import *
from telegram_bot import *

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

BASIC_LANDS = {"ISLAND", "SWAMP", "MOUNTAIN", "FOREST", "PLAINS", "WASTES"}

LOJAS = {'mercadia':'https://www.mercadiastore.com.br/',
        'calabouco':'https://www.lojacalabouco.com.br/#'}

SELECTOR_IMAGEM_CARD_UNICO = 'html body section.bg-clean div.container div.bloco_cards div.imagem_cards div#imagemScroll figure#imagemOriginal.text-center img#img_0.load-capty-0.pProdItem'

# 1. Pega nome da carta
# 1.1. Busca o nome em portugues da carta com a API do scryfall 
# 2. Abre mercadia.com.br
# 3. Pesquisa o nome da carta
# 4. Pega o preço da carta se existir
# 4.5. Se não existir, avisa que a carta não foi encontradak
# 5. Imprime o preço da carta


# =================================================
#  Busca pelo id da carta e usa o id para achar
#             o nome em ptbr da carta
# =================================================
def traduzir_carta_mtg(nome_ingles):
    # Endpoint de nome exato
    url_base = "https://api.scryfall.com/cards/named"
    params = {
        "exact": nome_ingles,
        "format": "json"
    }

    try:
        response = requests.get(url_base, params=params)
        if response.status_code == 200:
            dados_ingles = response.json()
            
            # Pegamos o ID da carta e buscamos especificamente a versão 'pt' dela
            oracle_id = dados_ingles.get('oracle_id')
            
            # Buscamos no Scryfall a versão em português desta carta específica
            url_busca_pt = "https://api.scryfall.com/cards/search"
            params_pt = {
                "q": f"oracle_id:{oracle_id} lang:pt",
                "order": "released" # Pega a versão mais recente ou comum
            }
            
            res_pt = requests.get(url_busca_pt, params=params_pt)
            
            if res_pt.status_code == 200:
                dados_pt = res_pt.json()['data'][0]
                
                # Tratamento para cartas de duas faces
                if 'printed_name' in dados_pt:
                    return dados_pt['printed_name']
                elif 'card_faces' in dados_pt:
                    return dados_pt['card_faces'][0]['printed_name']
            
            # Se não houver versão PT, retorna o nome em inglês
            return dados_ingles.get('name')
            
        return f"Não encontrada: {nome_ingles}"
    except Exception as e:
        return f"Erro: {e}"


# =================================================
#      Função que serve para encontrar a carta 
#     procurada quando houverem varios resultados 
#                   para a pesquisa
# =================================================
async def raspar_de_varios_resultados(page, nome_carta:str=' ' , nome_ptbr:str=' '):
    todas_as_opcoes = await page.locator('div.card-item').all() #Pega todos os itens da pagina
    print(f'Localizamos {len(todas_as_opcoes)} itens, buscando o certo ...')

    for item in todas_as_opcoes:
        try:
            fonte_imagem_item = await item.locator('div.card-img a img').get_attribute('src') #Pega o link da imagem do item
            nome_item = await item.locator('div.card-desc div.title a').inner_text() #Procura o nome do item na descrição

            nome_ptbr = nome_ptbr.strip().upper()
            nome_carta = nome_carta.strip().upper()
            nome_item = nome_item.strip().upper()

            # Se no link houver a palavra "magic" e no nome do item for o mesmo da carta buscada, clica 
            if 'magic' in fonte_imagem_item and ((nome_item == nome_carta or nome_item == nome_ptbr)):
                await item.click()
                await page.wait_for_load_state('networkidle')

        except Exception as e:
            # Para qualquer erro que ocorrer no processo, sai da função
            print("Erro ao coletar dados, dando continuidade ...")
            print(f'ERROR:\n{e}')




# =================================================
#     Função que serve para encontrar os dados 
#         que buscamos na pagina da carta
#              que queremos raspar
# =================================================
async def raspar_de_resultado_unico(page, nome_carta):
    url_carta = page.url
    todas_as_colecoes = await page.locator('div.table-cards-row').all() #Busca as linhas de cada coleção
    print(f'Encontrados {len(todas_as_colecoes)} coleções')

    disponiveis = []

    for i in todas_as_colecoes:
        quantidade = await i.locator('div:nth-child(5)').inner_text(timeout=3000)
        quantidade = int(quantidade[0])

        try:
            colecao = await i.locator('img.icon.icon-edicao').get_attribute('title')
        except:
            colecao = ''

        # Se a quantidade da carta daquela edição for maior que 0, retorna o nome da coleção, quantidade e preço.
        if quantidade > 0:
            preco = str(await i.locator('div.card-preco').inner_text(timeout=3000))
            preco = preco.splitlines()
            try:
                preco_float = float(preco[1].strip().replace(',','.').replace('R$',''))
            except:
                preco_float = float(preco[0].strip().replace(',','.').replace('R$',''))


            print(f'COLEÇÃO: {colecao} | QTD:{quantidade} | PRECO: R${preco_float} ')
            disponiveis.append([nome_carta, 'DISPONÍVEL', colecao, quantidade, preco_float, str(url_carta)])
        else:
            disponiveis.append([nome_carta,'NÃO DISPONÍVEL'])
    return disponiveis




async def raspar_preco_carta(url, nome_carta):
    if nome_carta.upper() in BASIC_LANDS:
        return 0
    
    resultado = []
    
    nome_busca = traduzir_carta_mtg(nome_carta).upper()

    print(f'\nNOME ENCONTRADO NA API: {nome_busca}')

    
    async with async_playwright() as ap:
        browser = await ap.firefox.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='pt-BR',
            timezone_id='America/Manaus',
        )
        page = await context.new_page()
        await page.goto(url, wait_until='domcontentloaded')

        # Procura o campo de busca, e escreve o nome da carta traduzido nele
        await page.locator('#fSearch.form-control.inp_busca').type(nome_busca)
        print(f'PESQUISANDO POR {nome_carta.upper()} -> {nome_busca.upper()}')

        # Procura o auto complete e clica
        selector_primeiro_autocomplete = 'section.item > div.card-title'
        try:
            await page.locator(selector_primeiro_autocomplete).first.click(timeout=5000)# encontra a primeira ocorrencia do autocomplete e clica
        except:
            # Caso ele não ache com o nome da API, busca com o nome original da busca
            print(f'ERRO AO ENCONTRAR {nome_busca}, BUSCANDO POR {nome_carta.upper()}')
            try:
                await page.locator('#fSearch.form-control.inp_busca').clear()
                await page.locator('#fSearch.form-control.inp_busca').type(nome_carta)
                await page.locator(selector_primeiro_autocomplete).first.click(timeout=5000)
            except:
                await page.locator('div.bg_btn').click(timeout=2000)

        # Espera a pagina carregar 
        await page.wait_for_load_state('networkidle')

        # Verifica se está na pagina da carta. Caso não esteja, busca dentre vários resultados
        try:
            await page.locator(SELECTOR_IMAGEM_CARD_UNICO).click(timeout=2000)
            resultados_scrapping = await raspar_de_resultado_unico(page, nome_carta=nome_carta)
        except Exception as e:
            print(f"Mais de uma opção encontrada")

            await raspar_de_varios_resultados(page, nome_carta=nome_carta, nome_ptbr=nome_busca)
            resultados_scrapping = await raspar_de_resultado_unico(page, nome_carta=nome_carta)

        
        if resultados_scrapping == None:
            print('Não achou nada')
            return
        else:
            return resultados_scrapping



# def formatar_nomes_cartas(texto_bruto):
#     linhas = re.split(r'[\n,]', texto_bruto)
    
#     decklist_limpa = []
    
#     for linha in linhas:
#         # Limpa espaços em branco nas pontas
#         linha = linha.strip()
#         if not linha:
#             continue
            
#         # Aplica um regex para buscar só pelo nome da carta e pronto
#         match = re.search(r'^\d*\s*x?\s*(.+)', linha, re.IGNORECASE)
        
#         if match:
#             nome_carta = match.group(1).strip()
#             if nome_carta.upper() not in BASIC_LANDS:
#                 decklist_limpa.append(nome_carta)
#         else:
#             # Se não bateu no regex adiciona direto
#             if linha.upper() not in BASIC_LANDS:
#                 decklist_limpa.append(linha)
    
#     # LISTA > SET > LISTA para limpar duplicatas
#     decklist_limpa = set(decklist_limpa)
#     decklist_limpa = list(decklist_limpa).sort()
#     return decklist_limpa




async def raspar_lista_cartas(lista_de_cartas:list=[], cartas_para_busca=''):
    cartas_disponiveis_por_loja = {}

    if cartas_para_busca:
        cartas_para_busca = set(re.findall(r'^\s*\d+\s+(.+)', cartas_para_busca, re.MULTILINE))
        for nome_loja, link_loja in LOJAS.items():
            print(f"====================================\nESCAVANDO EM {nome_loja.upper()}\n====================================")
            lista_resultados_loja = []
            cartas_disponiveis_por_loja[nome_loja] = []

            for carta in cartas_para_busca:
                scrap = await raspar_preco_carta(link_loja,carta)
                lista_resultados_loja.append(scrap)
            cartas_disponiveis_por_loja[nome_loja] = lista_resultados_loja

    
    if lista_de_cartas:
        for nome_loja, link_loja in LOJAS.items():
            print(f"====================================\nESCAVANDO EM {nome_loja.upper()}\n====================================")
            lista_resultados_loja = []
            cartas_disponiveis_por_loja[nome_loja] = {}

            for carta in lista_de_cartas:
                carta = re.findall(r'^\s*\d*\s*(.+)', carta)[0]
                scrap = await raspar_preco_carta(link_loja,carta)
                lista_resultados_loja.append(scrap)
            cartas_disponiveis_por_loja[nome_loja] = lista_resultados_loja

    linhas_planilha = limpa_scrapping_para_planilha(cartas_disponiveis_por_loja)

    return linhas_planilha, cartas_disponiveis_por_loja




def limpa_scrapping_para_planilha(dados_por_loja:dict):
    # LOJA : 
    # Todas as cartas da loja =>[
    #   Todas as ocorrencias de coleções da carta =>[
    #        Os dados buscados da determinada coleção =>[  ]]]
    linhas_finais_planilha = []

    # Percorrendo o dicionário
    for nome_loja, lista_de_listas in dados_por_loja.items():

        # lista_de_listas contém as listas de cada carta
        for resultados_carta in lista_de_listas:

            # Filtro para remover identicos, como vários itens com "NÃO DISPONÍVEL"
            disponiveis_unicos = {tuple(resultado) for resultado in resultados_carta if resultado[1] == 'DISPONÍVEL'}

            if disponiveis_unicos:

                # Se existem disponíveis, adicionamos todos eles à planilha
                for item in disponiveis_unicos:

                    # Adicionamos o nome da loja no início da linha para a planilha
                    linhas_finais_planilha.append([nome_loja] + list(item))
            else:
                # Se a lista de disponíveis está vazia, pegamos o nome da carta do primeiro item da lista original e marcamos como esgotado
                nome_carta = resultados_carta[0][0]
                linhas_finais_planilha.append([nome_loja, nome_carta, "NÃO DISPONÍVEL", "---", 0, 0, "---"])

    return linhas_finais_planilha




async def main():
    # Conecta a planilha do google sheets
    aba_resultados, aba_busca  = conectar_planilha()

    # Busca as cartas para scrapping direto da planilha de busca
    decklist = ler_da_planilha(aba_busca)

    # Chama o scrapping passando a lista de cartas lida da planilha
    linhas_planilha, disponibilidade = await raspar_lista_cartas(decklist)

    # Salva os resultados na planilha de resultados
    salvar_planilha(aba_resultados, linhas_planilha)

    # Envia a mensagem com as cartas para o telegram
    await enviar_notificacao_telegram(disponibilidade, TELEGRAM_TOKEN, CHAT_ID)




if __name__ == "__main__":
    asyncio.run(main())