from playwright.async_api import async_playwright
import requests
import time
import asyncio
import re

BASIC_LANDS = {"ISLAND", "SWAMP", "MOUNTAIN", "FOREST", "PLAINS", "WASTES"}

LOJAS = {'mercadia':'https://www.mercadiastore.com.br/',
        'calabouco':'https://www.lojacalabouco.com.br/#'}

SELECTOR_IMAGEM_CARD_UNICO = 'html body section.bg-clean div.container div.bloco_cards div.imagem_cards div#imagemScroll figure#imagemOriginal.text-center img#img_0.load-capty-0.pProdItem'

# 1. Pega nome da carta
# 1.1. Busca o nome em portugues da carta com a API do scryfall 
# 2. Abre mercadia.com.br
# 3. Pesquisa o nome da carta
# 4. Pega o preço da carta se existir
# 4.5. Se não existir, avisa que a carta não foi encontrada
# 5. Imprime o preço da carta

def traduzir_carta_mtg(nome_ingles):
    # Endpoint de nome exato é muito mais rápido e preciso que o /search
    url_base = "https://api.scryfall.com/cards/named"
    params = {
        "exact": nome_ingles,
        "format": "json"
    }

    try:
        response = requests.get(url_base, params=params)
        if response.status_code == 200:
            dados_ingles = response.json()
            
            # Aqui está o segredo: Pegamos o ID da carta (Oracle ID) 
            # e buscamos especificamente a versão 'pt' dela
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
                
                # Tratamento para cartas de duas faces (Double Faced)
                if 'printed_name' in dados_pt:
                    return dados_pt['printed_name']
                elif 'card_faces' in dados_pt:
                    return dados_pt['card_faces'][0]['printed_name']
            
            # Se não houver versão PT, retorna o nome em inglês (comum em cartas antigas)
            return dados_ingles.get('name')
            
        return f"Não encontrada: {nome_ingles}"
    except Exception as e:
        return f"Erro: {e}"




async def raspar_de_varios_resultados(page, nome_carta:str=' ' , nome_ptbr:str=' '):
    todas_as_opcoes = await page.locator('div.card-item').all()
    print(f'Localizamos {len(todas_as_opcoes)} itens, buscando o certo ...')

    for item in todas_as_opcoes:
        try:
            fonte_imagem_item = await item.locator('div.card-img a img').get_attribute('src')
            nome_item = await item.locator('div.card-desc div.title a').inner_text()

            nome_ptbr = nome_ptbr.strip().upper()
            nome_carta = nome_carta.strip().upper()
            nome_item = nome_item.strip().upper()

            if 'magic' in fonte_imagem_item and ((nome_item == nome_carta or nome_item == nome_ptbr)):
                await item.click()
                await page.wait_for_load_state('networkidle')
                await raspar_de_resultado_unico(page)
        except Exception as e:
            print("Erro ao coletar dados, dando continuidade ...")
            print(f'ERROR:\n{e}')




async def raspar_de_resultado_unico(page):
    todas_as_colecoes = await page.locator('div.table-cards-row').all()
    print(f'Encontrados {len(todas_as_colecoes)} coleções')

    for i in todas_as_colecoes:
        quantidade = await i.locator('div:nth-child(5)').inner_text(timeout=3000)
        quantidade = int(quantidade[0])
        try:
            colecao = await i.locator('img.icon.icon-edicao').get_attribute('title')
        except:
            colecao = ''

        if quantidade > 0:
            preco = await i.locator('div.card-preco').inner_text(timeout=3000)
            print(f'COLEÇÃO: {colecao} | QTD:{quantidade} | PRECO:{preco}')
        else:
            pass




async def raspar_preco_carta(url, nome_carta):
    if nome_carta.upper() in BASIC_LANDS:
        return 0
    
    nome_busca = traduzir_carta_mtg(nome_carta).upper()

    print(f'\nNOME ENCONTRADO NA API: {nome_busca}')

    
    async with async_playwright() as ap:
        browser = await ap.firefox.launch(headless=False)
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
                print("ERRO AO BUSCAR PELOS NOMES")

        # Espera a pagina carregar 
        await page.wait_for_load_state('networkidle')

        card_unico = None
        try:
            print('ENTROU NO 1') 
            card_unico = await page.locator(SELECTOR_IMAGEM_CARD_UNICO).click(timeout=2000)
            await raspar_de_resultado_unico(page)   
        except Exception as e:
            print('ENTROU NO 2') 
            print(f"ERRO AO BUSCAR CARD ÚNICO: {e}")
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

    print(len(decklist_limpa))

    for nome, link in LOJAS.items():
        print(f"====================================\nESCAVANDO EM {nome.upper()}\n====================================")
        for carta in decklist_limpa:
            await raspar_preco_carta(link,carta)




asyncio.run(raspar_lista_cartas())