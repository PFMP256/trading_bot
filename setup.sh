#!/bin/bash

# Exit on error
set -e

echo "========================================"
echo "Trading Bot Setup Script"
echo "========================================"

# Verificar si Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 no está instalado. Por favor instálalo antes de continuar."
    exit 1
fi

echo "Para instalar las dependencias necesarias, es posible que necesites permisos de superusuario"
echo "Las siguientes dependencias pueden ser necesarias: python3-venv python3-distutils python3-full build-essential"
echo "Por favor, instálalas manualmente si este script falla:"
echo "sudo apt install python3-venv python3-distutils python3-full build-essential"

# Asegurarse de tener python3-venv instalado
echo "Verificando que python3-venv esté instalado..."
python3 -c "import venv" 2>/dev/null || { 
    echo "El módulo venv no está disponible, intenta instalarlo con: sudo apt install python3-venv python3-full"
    echo "Luego ejecuta este script nuevamente."
    exit 1
}

# Crear y activar entorno virtual
echo "Creando entorno virtual..."
python3 -m venv venv
source venv/bin/activate

# Actualizar pip dentro del entorno virtual
echo "Actualizando pip..."
pip install --upgrade pip setuptools wheel

# Instalar dependencias
echo "Instalando dependencias..."
pip install -r requirements.txt

# Crear directorio de logs si no existe
mkdir -p logs

# Hacer ejecutables los scripts
chmod +x start.sh stop.sh

echo "========================================"
echo "Configuración completada!"
echo ""
echo "Próximos pasos:"
echo "1. Edita el archivo .env con tus claves API y preferencias: nano .env"
echo "2. Inicia el bot de trading: ./start.sh"
echo "3. Para ver los logs: tail -f btc_day_trading_bot.log"
echo "4. Para detener el bot: ./stop.sh"
echo "========================================"
