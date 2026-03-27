from playwright.async_api import async_playwright
import requests
import time
import asyncio
import re

BASIC_LANDS = {"ISLAND", "SWAMP", "MOUNTAIN", "FOREST", "PLAINS", "WASTES"}

LOJAS = {'calabouco':'https://www.lojacalabouco.com.br/#',
        'mercadia':'https://www.mercadiastore.com.br/',}

SELECTOR_IMAGEM_CARD_UNICO = 'html body section.bg-clean div.container div.bloco_cards div.imagem_cards div#imagemScroll figure#imagemOriginal.text-center img#img_0.load-capty-0.pProdItem'

# 1. Pega nome da carta
# 1.1. Busca o nome em portugues da carta com a API do scryfall 
# 2. Abre mercadia.com.br
# 3. Pesquisa o nome da carta
# 4. Pega o preço da carta se existir
# 4.5. Se não existir, avisa que a carta não foi encontrada
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
                await raspar_de_resultado_unico(page)
        except Exception as e:
            # Para qualquer erro que ocorrer no processo, sai da função
            print("Erro ao coletar dados, dando continuidade ...")
            print(f'ERROR:\n{e}')
            return 


# =================================================
#     Função que serve para encontrar os dados 
#         que buscamos na pagina da carta
#              que queremos raspar
# =================================================
async def raspar_de_resultado_unico(page):
    todas_as_colecoes = await page.locator('div.table-cards-row').all() #Busca as linhas de cada coleção
    print(f'Encontrados {len(todas_as_colecoes)} coleções')

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
            preco_float = float(preco[1].strip().replace(',','.').replace('R$',''))


            print(f'COLEÇÃO: {colecao} | QTD:{quantidade} | PRECO: R${preco_float}')
        else:
            pass




async def raspar_preco_carta(url, nome_carta):
    if nome_carta.upper() in BASIC_LANDS:
        return 0
    
    nome_busca = traduzir_carta_mtg(nome_carta).upper()

    print(f'\nNOME ENCONTRADO NA API: {nome_busca}')

    
    async with async_playwright() as ap:
        browser = await ap.firefox.launch()
        page = await browser.new_page()
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

        try:
            await page.locator(SELECTOR_IMAGEM_CARD_UNICO).click(timeout=2000)
            await raspar_de_resultado_unico(page)   
        except Exception as e:
            print(f"Mais de uma opção encontrada")
            await raspar_de_varios_resultados(page, nome_carta=nome_carta, nome_ptbr=nome_busca)




async def raspar_lista_cartas():
    decklist = """
        11 Island
        1 Swamp
        2 Bojuka Bog
        4 Ice Tunnel
        1 Dispel
        2 Spell Pierce
        4 Ponder
        4 Brainstorm
        4 Augur of Bolas
        4 Counterspell
        3 Cast Down
        1 Extract a Confession
        1 Unexpected Fangs
        1 Suffocating Fumes
        1 Behold the Multiverse
        2 Thorn of the Black Rose
        4 Snuff Out
        2 Murmuring Mystic
        4 Lorien Revealed
        4 Tolarian Terror

        1 Blue Elemental Blast
        4 Hydroblast
        2 Nihil Spellbomb
        1 Rotten Reunion
        3 Steel Sabotage
        1 Extract a Confession
        1 Unexpected Fangs
        1 Arms of Hadar
        1 Thorn of the Black Rose
        """
    
    # cartas_velhas = ['Blue Elemental Blast','Red Elemental Blast']
    decklist_limpa = set(re.findall(r'^\s*\d+\s+(.+)', decklist, re.MULTILINE))

    lista_para_testes = ['Ponder']
    cartas_disp_calab = ['Augur of bolas','Counterspell','Bojuka bog']
    
    print(len(decklist_limpa))

    for nome, link in LOJAS.items():
        print(f"====================================\nESCAVANDO EM {nome.upper()}\n====================================")
        for carta in cartas_disp_calab:
            await raspar_preco_carta(link,carta)




asyncio.run(raspar_lista_cartas())