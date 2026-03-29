FROM python:3.12-slim

# Variáveis de ambiente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Instala dependências do sistema + Cron
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 \
    libpangocairo-1.0-0 libx11-xcb1 cron procps \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Cache das dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install --with-deps

# Copia o restante do código
COPY . .

# Configura o Cron (Certifique-se que o arquivo se chama 'crontab' na sua pasta)
COPY crontab /etc/cron.d/mtg-cron
RUN chmod 0644 /etc/cron.d/mtg-cron && crontab /etc/cron.d/mtg-cron

# Cria o log
RUN touch /var/log/cron.log

# O SEGREDO: printenv garante que o bot veja o seu .env
CMD ["sh", "-c", "printenv > /etc/environment && cron && tail -f /var/log/cron.log"]