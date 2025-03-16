# Bot de Day Trading para BTC/USDT

Este bot implementa una estrategia de day trading para el par BTC/USDT, basada en indicadores técnicos y con gestión de riesgo incorporada. El bot está diseñado para realizar entre 1-3 operaciones por día, buscando aprovechar movimientos significativos en el precio de Bitcoin.

## Características Principales

- **Estrategia de Day Trading:** Todas las posiciones se abren y cierran dentro del mismo día, evitando riesgos durante la noche.
- **Análisis Técnico:** Utiliza múltiples indicadores (EMA, RSI, MACD, Bandas de Bollinger) para identificar oportunidades de trading.
- **Gestión de Riesgo:** Implementa stop-loss y take-profit automáticos, con límites de riesgo por operación configurables.
- **Visualización:** Incluye herramienta para visualizar y backtest de la estrategia con datos históricos.

## Requisitos

- Python 3.8+
- Cuenta en un exchange compatible con la API de CCXT (Binance por defecto)
- Credenciales de API con permisos de lectura y trading

## Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/tuusuario/btc_day_trading_bot.git
cd btc_day_trading_bot
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Configura tus credenciales:
```bash
cp .env.example .env
```
Edita el archivo `.env` con tus credenciales de API y configuración deseada.

## Configuración

El bot se configura a través del archivo `.env`. Los parámetros principales son:

- **API_KEY:** Tu clave de API del exchange
- **API_SECRET:** Tu secreto de API del exchange
- **EXCHANGE_ID:** ID del exchange (por defecto: "binance")
- **RISK_PER_TRADE:** Porcentaje de riesgo por operación (por defecto: 0.02 = 2%)
- **MAX_DAILY_TRADES:** Número máximo de operaciones diarias (por defecto: 3)
- **LEVERAGE:** Apalancamiento (por defecto: 1.0 = sin apalancamiento)
- **TAKE_PROFIT_PCT:** Porcentaje para take profit (por defecto: 0.03 = 3%)
- **STOP_LOSS_PCT:** Porcentaje para stop loss (por defecto: 0.01 = 1%)

## Uso

### Iniciar el Bot

Para iniciar el bot en modo de trading real:
```bash
python main.py
```

El bot operará durante el horario de trading configurado (9:00-20:00 UTC por defecto) y cerrará todas las posiciones al final del día.

### Visualizar la Estrategia

Para visualizar y probar la estrategia con datos históricos:
```bash
python visualize_strategy.py
```

Esto generará un gráfico con las señales de trading, indicadores técnicos y resultados del backtest.

## Lógica de Trading

El bot utiliza la siguiente lógica para identificar oportunidades:

### Señales de Compra
Busca la coincidencia de al menos 2 de las siguientes 4 condiciones:
1. Cruce alcista de EMA (EMA20 cruza por encima de EMA50)
2. RSI saliendo de la zona de sobreventa (cruza por encima de 30)
3. MACD cruzando por encima de su línea de señal
4. Precio cerca del soporte (banda inferior de Bollinger)

### Señales de Venta
Vende cuando ocurre cualquiera de estas situaciones:
- Se alcanza el nivel de take profit (3% por defecto)
- Se alcanza el stop loss (1% por defecto)
- Se identifican al menos 2 de las siguientes condiciones técnicas:
  1. Cruce bajista de EMA (EMA20 cruza por debajo de EMA50)
  2. RSI entrando en la zona de sobrecompra (cruza por encima de 70)
  3. MACD cruzando por debajo de su línea de señal
  4. Precio cerca de la resistencia (banda superior de Bollinger)

Todas las posiciones se cierran automáticamente antes del final del día de trading.

## Advertencia de Riesgo

Este bot es una herramienta de trading experimental. El trading de criptomonedas conlleva un alto riesgo y es posible perder su inversión. Use este software bajo su propio riesgo y nunca opere con fondos que no pueda permitirse perder.

## Contribuciones

Las contribuciones son bienvenidas. Por favor, abre un issue para discutir cambios importantes antes de enviar un pull request.

## Licencia

[MIT License](LICENSE) 