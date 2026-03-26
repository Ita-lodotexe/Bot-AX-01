from playwright.async_api import async_playwright
import asyncio
import re

# 1. Pega nome da carta
# 2. Abre mercadia.com.br
# 3. Pesquisa o nome da carta
# 4. Pega o preço da carta se existir
# 4.5. Se não existir, avisa que a carta não foi encontrada
# 5. Imprime o preço da carta

async def raspar_preco_carta(nome_carta='Wild Growth'):
    url = f'https://www.mercadiastore.com.br/'
    resultados = []

    async with async_playwright() as ap:
        browser = await ap.firefox.launch(headless=False)
        page = await browser.new_page()
        await page.goto(url, wait_until='domcontentloaded')

        # Procura o campo de busca, e escreve o nome da carta nele 
        await page.locator('#fSearch.form-control.inp_busca').type(nome_carta)
        print(f'PESQUISANDO POR {nome_carta.upper()}')

        # encontra a primeira ocorrencia do autocomplete e clica
        selector_primeiro_autocomplete = 'section.item > div.card-title'
        # await page.wait_for_selector(locator_primeiro_autocomplete)
        await page.locator(selector_primeiro_autocomplete).first.click()
        await page.wait_for_load_state('networkidle')

        todas_as_colecoes = await page.locator('div.table-cards-row').all()
        print(f'Encontrados {len(todas_as_colecoes)} coleções')

        for i in todas_as_colecoes:
            quantidade = await i.locator('div:nth-child(5)').inner_text(timeout=3000)
            quantidade = int(quantidade[0])

            colecao = await i.locator('img.icon.icon-edicao').get_attribute('title')
            # sigla_edicao = await i.locator('')

            if quantidade > 0:
                preco = await i.locator('div.card-preco').inner_text(timeout=3000)
                print(f'COLEÇÃO: {colecao} | QTD:{quantidade} | PRECO:{preco}')
            else:
                pass


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
    decklist_limpa = re.findall(r'^\s*\d+\s+(.+)', decklist, re.MULTILINE)

    for carta in decklist_limpa:
        await raspar_preco_carta(carta)



asyncio.run(raspar_lista_cartas())