#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot de Day Trading para BTC/USDT
Este bot implementa una estrategia de day trading para el par BTC/USDT,
buscando realizar entre 1-3 operaciones por día con gestión de riesgo.
"""

import os
import time
import datetime
import logging
import schedule
import pandas as pd
import numpy as np
import ccxt
from dotenv import load_dotenv
import ta
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("btc_day_trading_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BTCDayTrader")

# Cargar variables de entorno
load_dotenv()

class BTCDayTrader:
    def __init__(self):
        """Inicializar el bot de day trading."""
        # Configuración de la API del exchange
        self.api_key = os.getenv('API_KEY')
        self.api_secret = os.getenv('API_SECRET')
        self.exchange_id = os.getenv('EXCHANGE_ID', 'bitget')  # Binance por defecto
        
        # Configuración de trading
        self.symbol = 'BTC/USDT'
        self.timeframe = '15m'  # Marco de tiempo para el análisis
        self.risk_per_trade = float(os.getenv('RISK_PER_TRADE', 0.02))  # 2% por defecto
        self.max_daily_trades = int(os.getenv('MAX_DAILY_TRADES', 3))
        self.leverage = float(os.getenv('LEVERAGE', 1.0))  # Sin apalancamiento por defecto
        
        # Límites de ganancia y pérdida
        self.take_profit_pct = float(os.getenv('TAKE_PROFIT_PCT', 0.03))  # 3% por defecto
        self.stop_loss_pct = float(os.getenv('STOP_LOSS_PCT', 0.01))  # 1% por defecto
        
        # Estado del bot
        self.in_position = False
        self.entry_price = None
        self.position_size = None
        self.daily_trades = 0
        self.last_trade_date = None
        
        # Inicializar el exchange
        self._init_exchange()
        
        logger.info(f"Bot de day trading para {self.symbol} inicializado correctamente.")
    
    def _init_exchange(self):
        """Inicializar la conexión con el exchange."""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',  # Tipo de mercado: spot
                }
            })
            logger.info(f"Conexión con {self.exchange_id} establecida.")
        except Exception as e:
            logger.error(f"Error al inicializar exchange: {str(e)}")
            raise
    
    def fetch_ohlcv_data(self, limit=100):
        """Obtener datos OHLCV históricos."""
        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=self.symbol,
                timeframe=self.timeframe,
                limit=limit
            )
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            logger.error(f"Error al obtener datos OHLCV: {str(e)}")
            return None
    
    def add_indicators(self, df):
        """Añadir indicadores técnicos al DataFrame."""
        if df is None or df.empty:
            return None
        
        # Añadir EMA de 20 y 50 periodos
        df['ema20'] = EMAIndicator(close=df['close'], window=20).ema_indicator()
        df['ema50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
        
        # Añadir RSI
        df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
        
        # Añadir MACD
        macd = MACD(
            close=df['close'],
            window_slow=26,
            window_fast=12,
            window_sign=9
        )
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_diff'] = macd.macd_diff()
        
        # Añadir Bandas de Bollinger
        bollinger = BollingerBands(close=df['close'], window=20, window_dev=2)
        df['bb_high'] = bollinger.bollinger_hband()
        df['bb_mid'] = bollinger.bollinger_mavg()
        df['bb_low'] = bollinger.bollinger_lband()
        
        return df
    
    def check_buy_signals(self, df):
        """Verificar señales de compra según la estrategia."""
        if df is None or df.empty or len(df) < 50:
            logger.warning("Datos insuficientes para analizar señales de compra.")
            return False
        
        # Obtener la última fila (datos más recientes)
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Condiciones para una señal de compra:
        
        # 1. Cruce de EMA (EMA20 cruza por encima de EMA50)
        ema_crossover = (prev_row['ema20'] <= prev_row['ema50']) and (last_row['ema20'] > last_row['ema50'])
        
        # 2. RSI saliendo de zona de sobreventa (RSI cruza por encima de 30)
        rsi_condition = (prev_row['rsi'] <= 30) and (last_row['rsi'] > 30)
        
        # 3. MACD cruzando por encima de la línea de señal
        macd_crossover = (prev_row['macd'] <= prev_row['macd_signal']) and (last_row['macd'] > last_row['macd_signal'])
        
        # 4. Precio cerca del soporte (banda inferior de Bollinger)
        bollinger_support = (last_row['close'] <= last_row['bb_low'] * 1.01)  # Precio dentro del 1% de la banda inferior
        
        # Combinación de señales (necesitamos al menos 2 de 4 condiciones)
        signal_count = sum([ema_crossover, rsi_condition, macd_crossover, bollinger_support])
        
        if signal_count >= 2:
            logger.info(f"Señal de compra detectada: EMA={ema_crossover}, RSI={rsi_condition}, MACD={macd_crossover}, BB={bollinger_support}")
            return True
        
        return False
    
    def check_sell_signals(self, df):
        """Verificar señales de venta según la estrategia."""
        if df is None or df.empty or len(df) < 50 or not self.in_position:
            return False
        
        # Obtener la última fila (datos más recientes)
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        # Condiciones para una señal de venta:
        
        # 1. Cruce de EMA (EMA20 cruza por debajo de EMA50)
        ema_crossover = (prev_row['ema20'] >= prev_row['ema50']) and (last_row['ema20'] < last_row['ema50'])
        
        # 2. RSI entrando en zona de sobrecompra (RSI cruza por encima de 70)
        rsi_condition = (prev_row['rsi'] <= 70) and (last_row['rsi'] > 70)
        
        # 3. MACD cruzando por debajo de la línea de señal
        macd_crossover = (prev_row['macd'] >= prev_row['macd_signal']) and (last_row['macd'] < last_row['macd_signal'])
        
        # 4. Precio cerca de la resistencia (banda superior de Bollinger)
        bollinger_resistance = (last_row['close'] >= last_row['bb_high'] * 0.99)  # Precio dentro del 1% de la banda superior
        
        # Take profit: precio actual es un % específico mayor que el precio de entrada
        take_profit = self.entry_price and (last_row['close'] >= self.entry_price * (1 + self.take_profit_pct))
        
        # Stop loss: precio actual es un % específico menor que el precio de entrada
        stop_loss = self.entry_price and (last_row['close'] <= self.entry_price * (1 - self.stop_loss_pct))
        
        # Combinación de señales (take profit, stop loss, o al menos 2 de 4 condiciones técnicas)
        signal_count = sum([ema_crossover, rsi_condition, macd_crossover, bollinger_resistance])
        
        if take_profit:
            logger.info(f"Señal de venta: Take Profit alcanzado. Entrada: {self.entry_price}, Actual: {last_row['close']}")
            return True
        elif stop_loss:
            logger.info(f"Señal de venta: Stop Loss alcanzado. Entrada: {self.entry_price}, Actual: {last_row['close']}")
            return True
        elif signal_count >= 2:
            logger.info(f"Señal de venta técnica detectada: EMA={ema_crossover}, RSI={rsi_condition}, MACD={macd_crossover}, BB={bollinger_resistance}")
            return True
        
        return False
    
    def execute_buy(self):
        """Ejecutar una orden de compra."""
        if self.in_position:
            logger.info("Ya hay una posición abierta. No se puede comprar.")
            return
        
        if self.daily_trades >= self.max_daily_trades:
            logger.info(f"Se alcanzó el máximo de operaciones diarias ({self.max_daily_trades}).")
            return
        
        try:
            # Obtener el balance disponible
            balance = self.exchange.fetch_balance()
            usdt_balance = balance['USDT']['free'] if 'USDT' in balance else 0
            
            # Obtener el precio actual
            ticker = self.exchange.fetch_ticker(self.symbol)
            current_price = ticker['last']
            
            # Calcular el tamaño de la posición basado en el riesgo por operación
            risk_amount = usdt_balance * self.risk_per_trade
            # Ajustar por apalancamiento si se está usando
            position_size_usd = risk_amount * self.leverage
            position_size_btc = position_size_usd / current_price
            
            # Redondear a 6 decimales (ajustar según los requisitos del exchange)
            position_size_btc = round(position_size_btc, 6)
            
            if position_size_btc * current_price < 10:  # Verificar mínimo (por ejemplo, 10 USDT)
                logger.warning(f"Tamaño de posición demasiado pequeño: {position_size_btc * current_price} USDT")
                return
            
            # Ejecutar la orden de mercado
            order = self.exchange.create_market_buy_order(
                symbol=self.symbol,
                amount=position_size_btc
            )
            
            # Actualizar el estado
            self.in_position = True
            self.entry_price = current_price
            self.position_size = position_size_btc
            self.daily_trades += 1
            self.last_trade_date = datetime.date.today()
            
            logger.info(f"Compra ejecutada: {position_size_btc} BTC a {current_price} USDT")
            logger.info(f"Detalles de la orden: {order}")
            
        except Exception as e:
            logger.error(f"Error al ejecutar compra: {str(e)}")
    
    def execute_sell(self):
        """Ejecutar una orden de venta."""
        if not self.in_position:
            logger.info("No hay posición abierta. No se puede vender.")
            return
        
        try:
            # Verificar si tenemos la cantidad de BTC necesaria
            balance = self.exchange.fetch_balance()
            btc_balance = balance['BTC']['free'] if 'BTC' in balance else 0
            
            # Usar el mínimo entre la posición registrada y el balance actual
            sell_amount = min(self.position_size, btc_balance)
            
            if sell_amount <= 0:
                logger.warning("No hay BTC disponible para vender.")
                return
            
            # Ejecutar la orden de mercado
            order = self.exchange.create_market_sell_order(
                symbol=self.symbol,
                amount=sell_amount
            )
            
            # Obtener el precio actual para calcular P&L
            ticker = self.exchange.fetch_ticker(self.symbol)
            exit_price = ticker['last']
            
            # Calcular P&L
            if self.entry_price:
                pnl_pct = (exit_price - self.entry_price) / self.entry_price * 100
                pnl_usd = sell_amount * (exit_price - self.entry_price)
                logger.info(f"P&L: {pnl_pct:.2f}% / {pnl_usd:.2f} USDT")
            
            # Actualizar el estado
            self.in_position = False
            self.entry_price = None
            self.position_size = None
            
            logger.info(f"Venta ejecutada: {sell_amount} BTC a {exit_price} USDT")
            logger.info(f"Detalles de la orden: {order}")
            
        except Exception as e:
            logger.error(f"Error al ejecutar venta: {str(e)}")
    
    def close_all_positions(self):
        """Cerrar todas las posiciones al final del día."""
        if self.in_position:
            logger.info("Cerrando posiciones al final del día...")
            self.execute_sell()
    
    def reset_daily_counters(self):
        """Resetear contadores diarios."""
        today = datetime.date.today()
        if self.last_trade_date != today:
            self.daily_trades = 0
            self.last_trade_date = today
            logger.info("Contadores diarios reseteados.")
    
    def run_trading_cycle(self):
        """Ejecutar un ciclo de trading."""
        logger.info("Iniciando ciclo de trading...")
        
        # Resetear contadores si es un nuevo día
        self.reset_daily_counters()
        
        # Verificar si estamos en horario de trading (9:00-20:00 UTC)
        current_hour = datetime.datetime.utcnow().hour
        if not (9 <= current_hour < 20):
            if self.in_position:
                logger.info("Fuera de horario de trading. Cerrando posiciones...")
                self.close_all_positions()
            else:
                logger.info("Fuera de horario de trading. Esperando...")
            return
        
        # Obtener datos y añadir indicadores
        df = self.fetch_ohlcv_data(limit=100)
        df = self.add_indicators(df)
        
        if df is None or df.empty:
            logger.warning("No se pudieron obtener datos válidos.")
            return
        
        # Si estamos en posición, verificar señales de venta
        if self.in_position:
            if self.check_sell_signals(df):
                self.execute_sell()
        # Si no estamos en posición y no hemos alcanzado el máximo de operaciones diarias,
        # verificar señales de compra
        elif self.daily_trades < self.max_daily_trades:
            if self.check_buy_signals(df):
                self.execute_buy()
        
        logger.info(f"Ciclo de trading completado. Operaciones hoy: {self.daily_trades}/{self.max_daily_trades}")
    
    def run(self):
        """Iniciar el bot de trading."""
        logger.info("Iniciando bot de trading...")
        
        # Programar cierre de posiciones al final del día (19:55 UTC)
        schedule.every().day.at("19:55").do(self.close_all_positions)
        
        # Programar reseteo de contadores a medianoche UTC
        schedule.every().day.at("00:01").do(self.reset_daily_counters)
        
        # Ciclo principal
        while True:
            try:
                # Ejecutar tareas programadas
                schedule.run_pending()
                
                # Ejecutar ciclo de trading
                self.run_trading_cycle()
                
                # Esperar antes del siguiente ciclo (5 minutos)
                logger.info("Esperando 5 minutos hasta el próximo ciclo...")
                time.sleep(300)
                
            except KeyboardInterrupt:
                logger.info("Bot detenido manualmente.")
                if self.in_position:
                    logger.warning("¡ATENCIÓN! Hay posiciones abiertas. Considera cerrarlas manualmente.")
                break
            except Exception as e:
                logger.error(f"Error en el ciclo principal: {str(e)}")
                # Esperar 1 minuto antes de reintentar
                time.sleep(60)

if __name__ == "__main__":
    try:
        bot = BTCDayTrader()
        bot.run()
    except Exception as e:
        logger.critical(f"Error fatal al iniciar el bot: {str(e)}") 