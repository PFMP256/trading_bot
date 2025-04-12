#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Archivo de prueba para verificar la funcionalidad del bot de trading
Este script comprueba si todas las acciones del bot pueden concretarse correctamente,
incluyendo inicialización, obtención de datos, cálculo de indicadores y ejecución de órdenes.
"""

import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import ccxt

# Importar la clase principal del bot
from main import BTCDayTrader

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("test_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TestBTCDayTrader")

def test_bot_initialization():
    """Probar la inicialización del bot."""
    logger.info("Probando inicialización del bot...")
    try:
        bot = BTCDayTrader()
        logger.info("✅ Inicialización exitosa")
        return bot
    except Exception as e:
        logger.error(f"❌ Error al inicializar el bot: {str(e)}")
        return None

def test_market_data_fetch(bot):
    """Probar la obtención de datos del mercado."""
    logger.info("Probando obtención de datos OHLCV...")
    try:
        df = bot.fetch_ohlcv_data(limit=100)
        if df is not None and not df.empty:
            logger.info(f"✅ Datos obtenidos correctamente: {len(df)} registros")
            logger.info(f"Muestra de datos:\n{df.head(3)}")
            return df
        else:
            logger.error("❌ No se pudieron obtener datos válidos")
            return None
    except Exception as e:
        logger.error(f"❌ Error al obtener datos: {str(e)}")
        return None

def test_indicators_calculation(bot, df):
    """Probar el cálculo de indicadores técnicos."""
    logger.info("Probando cálculo de indicadores técnicos...")
    try:
        if df is None or df.empty:
            logger.error("❌ No hay datos para calcular indicadores")
            return None
        
        df_with_indicators = bot.add_indicators(df)
        if df_with_indicators is not None:
            indicators = ['ema20', 'ema50', 'rsi', 'macd', 'macd_signal', 'bb_high', 'bb_mid', 'bb_low']
            missing_indicators = [ind for ind in indicators if ind not in df_with_indicators.columns]
            
            if missing_indicators:
                logger.error(f"❌ Faltan indicadores: {missing_indicators}")
                return None
            else:
                logger.info("✅ Indicadores calculados correctamente")
                logger.info(f"Muestra de indicadores:\n{df_with_indicators[indicators].tail(3)}")
                return df_with_indicators
        else:
            logger.error("❌ Error al calcular indicadores")
            return None
    except Exception as e:
        logger.error(f"❌ Error en cálculo de indicadores: {str(e)}")
        return None

def test_buy_sell_signals(bot, df):
    """Probar la detección de señales de compra y venta."""
    logger.info("Probando detección de señales de compra y venta...")
    try:
        if df is None or df.empty:
            logger.error("❌ No hay datos para detectar señales")
            return False
        
        # Probar señales de compra
        buy_signal = bot.check_buy_signals(df)
        logger.info(f"Señal de compra detectada: {buy_signal}")
        
        # Forzar estado "en posición" para probar señales de venta
        original_position_state = bot.in_position
        original_entry_price = bot.entry_price
        
        bot.in_position = True
        bot.entry_price = df['close'].iloc[-1]  # Usar el último precio de cierre como precio de entrada
        
        # Probar señales de venta
        sell_signal = bot.check_sell_signals(df)
        logger.info(f"Señal de venta detectada: {sell_signal}")
        
        # Restaurar estado original
        bot.in_position = original_position_state
        bot.entry_price = original_entry_price
        
        logger.info("✅ Prueba de señales completada")
        return True
    except Exception as e:
        logger.error(f"❌ Error al detectar señales: {str(e)}")
        return False

def test_order_execution_simulation(bot):
    """Simular la ejecución de órdenes sin realizar operaciones reales."""
    logger.info("Simulando ejecución de órdenes (sin operaciones reales)...")
    try:
        # Guardar el método original de creación de órdenes
        original_create_market_buy = bot.exchange.create_market_buy_order
        original_create_market_sell = bot.exchange.create_market_sell_order
        
        # Reemplazar con funciones simuladas
        def mock_buy_order(symbol, amount):
            logger.info(f"SIMULACIÓN: Orden de compra para {amount} {symbol}")
            return {"id": "sim-buy-001", "status": "closed", "amount": amount, "symbol": symbol}
        
        def mock_sell_order(symbol, amount):
            logger.info(f"SIMULACIÓN: Orden de venta para {amount} {symbol}")
            return {"id": "sim-sell-001", "status": "closed", "amount": amount, "symbol": symbol}
        
        # Aplicar mocks
        bot.exchange.create_market_buy_order = mock_buy_order
        bot.exchange.create_market_sell_order = mock_sell_order
        
        # Guardar estado original
        original_position_state = bot.in_position
        original_entry_price = bot.entry_price
        original_position_size = bot.position_size
        original_daily_trades = bot.daily_trades
        
        # Prueba de compra
        logger.info("Simulando compra...")
        bot.in_position = False
        bot.execute_buy()
        
        # Prueba de venta
        logger.info("Simulando venta...")
        bot.in_position = True
        bot.position_size = 0.001  # Simular una pequeña cantidad
        bot.execute_sell()
        
        # Restaurar métodos originales
        bot.exchange.create_market_buy_order = original_create_market_buy
        bot.exchange.create_market_sell_order = original_create_market_sell
        
        # Restaurar estado original
        bot.in_position = original_position_state
        bot.entry_price = original_entry_price
        bot.position_size = original_position_size
        bot.daily_trades = original_daily_trades
        
        logger.info("✅ Simulación de órdenes completada")
        return True
    except Exception as e:
        logger.error(f"❌ Error en simulación de órdenes: {str(e)}")
        return False

def test_trading_cycle(bot):
    """Probar un ciclo de trading completo."""
    logger.info("Probando ciclo de trading completo...")
    try:
        # Guardar estado original
        original_position_state = bot.in_position
        original_entry_price = bot.entry_price
        original_position_size = bot.position_size
        original_daily_trades = bot.daily_trades
        
        # Reemplazar temporalmente métodos de ejecución de órdenes
        original_execute_buy = bot.execute_buy
        original_execute_sell = bot.execute_sell
        
        def mock_execute_buy():
            logger.info("SIMULACIÓN: Ejecutando compra en ciclo de trading")
            bot.in_position = True
            bot.entry_price = 50000  # Precio ficticio
            bot.position_size = 0.001
            bot.daily_trades += 1
            
        def mock_execute_sell():
            logger.info("SIMULACIÓN: Ejecutando venta en ciclo de trading")
            bot.in_position = False
            bot.entry_price = None
            bot.position_size = None
        
        # Aplicar mocks
        bot.execute_buy = mock_execute_buy
        bot.execute_sell = mock_execute_sell
        
        # Ejecutar ciclo de trading
        bot.run_trading_cycle()
        
        # Restaurar métodos originales
        bot.execute_buy = original_execute_buy
        bot.execute_sell = original_execute_sell
        
        # Restaurar estado original
        bot.in_position = original_position_state
        bot.entry_price = original_entry_price
        bot.position_size = original_position_size
        bot.daily_trades = original_daily_trades
        
        logger.info("✅ Prueba de ciclo de trading completada")
        return True
    except Exception as e:
        logger.error(f"❌ Error en ciclo de trading: {str(e)}")
        return False

def run_all_tests():
    """Ejecutar todas las pruebas secuencialmente."""
    logger.info("="*50)
    logger.info("INICIANDO PRUEBAS DEL BOT DE TRADING")
    logger.info(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*50)
    
    # Inicializar bot
    bot = test_bot_initialization()
    if bot is None:
        logger.error("No se puede continuar sin un bot inicializado")
        return False
    
    # Obtener datos
    df = test_market_data_fetch(bot)
    if df is None:
        logger.error("No se puede continuar sin datos de mercado")
        return False
    
    # Calcular indicadores
    df_with_indicators = test_indicators_calculation(bot, df)
    if df_with_indicators is None:
        logger.error("No se puede continuar sin indicadores calculados")
        return False
    
    # Probar señales
    signal_test_result = test_buy_sell_signals(bot, df_with_indicators)
    
    # Simular órdenes
    order_simulation_result = test_order_execution_simulation(bot)
    
    # Probar ciclo de trading
    cycle_test_result = test_trading_cycle(bot)
    
    # Resumen final
    logger.info("="*50)
    logger.info("RESUMEN DE PRUEBAS")
    logger.info("="*50)
    logger.info(f"✅ Inicialización del bot: OK")
    logger.info(f"✅ Obtención de datos: {df is not None}")
    logger.info(f"✅ Cálculo de indicadores: {df_with_indicators is not None}")
    logger.info(f"✅ Detección de señales: {signal_test_result}")
    logger.info(f"✅ Simulación de órdenes: {order_simulation_result}")
    logger.info(f"✅ Ciclo de trading: {cycle_test_result}")
    
    all_passed = (df is not None and 
                  df_with_indicators is not None and 
                  signal_test_result and 
                  order_simulation_result and 
                  cycle_test_result)
    
    if all_passed:
        logger.info("✅ TODAS LAS PRUEBAS COMPLETADAS EXITOSAMENTE")
    else:
        logger.warning("⚠️ ALGUNAS PRUEBAS FALLARON")
    
    logger.info("="*50)
    return all_passed

if __name__ == "__main__":
    # Cargar variables de entorno si existen
    load_dotenv()
    
    # En caso de estar en entorno de prueba y no tener credenciales reales,
    # se pueden establecer credenciales ficticias para pruebas
    if not os.getenv('API_KEY') or not os.getenv('API_SECRET'):
        logger.warning("No se encontraron credenciales API. Usando valores de prueba.")
        os.environ['API_KEY'] = 'test_api_key'
        os.environ['API_SECRET'] = 'test_api_secret'
    
    # Ejecutar todas las pruebas
    run_all_tests()