#!/bin/bash

echo "======================================================"
echo "Ejecutando pruebas del bot antes de iniciar..."
echo "======================================================"

# Activar entorno virtual
source venv/bin/activate

# Ejecutar script de pruebas
python test_bot_actions.py

# Verificar si las pruebas terminaron correctamente
TESTS_RESULT=$?

# Verificar si hay errores de credenciales en el log del bot
if grep -q "requires \"password\" credential" btc_day_trading_bot.log; then
    echo "======================================================"
    echo "ERROR CRÍTICO: Se detectaron problemas con las credenciales."
    echo "El bot requiere credenciales válidas para operar."
    echo "Por favor, configure las credenciales correctamente en el archivo .env"
    echo "======================================================"
    exit 1
fi

if [ $TESTS_RESULT -eq 0 ]; then
    echo "======================================================"
    echo "Todas las pruebas pasaron correctamente. Iniciando bot..."
    echo "======================================================"
    # Iniciar el bot solo si las pruebas fueron exitosas
    # Usar nohup para que el proceso continúe incluso si se cierra la terminal
    nohup python main.py > nohup.out 2>&1 &
    
    # Guardar el PID para facilitar la detención
    echo $! > bot.pid
    
    echo "Trading bot iniciado con PID: $!"
    echo "Los logs se guardan en btc_day_trading_bot.log"
    echo "La salida estándar y errores se guarda en nohup.out"
else
    echo "======================================================"
    echo "ERROR: Las pruebas fallaron. El bot no se iniciará."
    echo "Revise los logs para más detalles."
    echo "======================================================"
    exit 1
fi