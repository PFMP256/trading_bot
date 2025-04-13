#!/bin/bash

echo "Deteniendo el trading bot..."

if [ -f bot.pid ]; then
    # Obtener PID del archivo
    PID=$(cat bot.pid)
    
    # Verificar si el proceso sigue ejecutándose
    if ps -p $PID > /dev/null; then
        kill $PID
        echo "Trading bot con PID $PID detenido."
    else
        echo "El proceso con PID $PID ya no está en ejecución."
    fi
    
    # Eliminar el archivo PID
    rm bot.pid
else
    echo "No se encontró archivo bot.pid. Intentando detener por nombre de proceso..."
    pkill -f "python main.py" && echo "Trading bot detenido." || echo "El bot no estaba en ejecución."
fi