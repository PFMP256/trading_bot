FROM python:3.8-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de requisitos primero para aprovechar la caché de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código fuente
COPY . .

# Crear un usuario no root para ejecutar la aplicación
RUN useradd -m botuser

# Crear directorio de logs y dar permisos al usuario botuser
RUN mkdir -p /app/logs && \
    touch /app/btc_day_trading_bot.log && \
    chown -R botuser:botuser /app/logs /app/btc_day_trading_bot.log

USER botuser

# Comando para ejecutar el bot
CMD ["python", "main.py"]