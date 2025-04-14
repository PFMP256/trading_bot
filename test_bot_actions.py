#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Archivo de prueba para verificar la funcionalidad del bot de trading
Este script comprueba si todas las acciones del bot pueden concretarse correctamente,
incluyendo inicialización, obtención de datos, cálculo de indicadores y ejecución de órdenes reales.
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

def setup_credentials():
    """Configurar credenciales desde las variables de entorno."""
    # Cargar variables de entorno si no se han cargado ya
    load_dotenv()
    
    # Verificar que las credenciales estén establecidas
    credentials = {
        'API_KEY': os.getenv('API_KEY'),
        'API_SECRET': os.getenv('API_SECRET'),
        'API_PASSWORD': os.getenv('API_PASSWORD'),
        'EXCHANGE_ID': os.getenv('EXCHANGE_ID', 'bitget')
    }
    
    # Ocultar los valores reales al imprimir
    logger.info(f"Credenciales configuradas: {', '.join([f'{k}={"*" * 5 if v else "NO CONFIGURADO"}' for k, v in credentials.items()])}")
    
    # Verificar si todas las credenciales necesarias están disponibles
    if not all([credentials['API_KEY'], credentials['API_SECRET'], credentials['API_PASSWORD']]):
        logger.error("❌ Faltan credenciales obligatorias. Asegúrate de que API_KEY, API_SECRET y API_PASSWORD estén configuradas.")
        return False
    
    return True

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

def test_balances(bot):
    """Verificar que se pueden consultar los balances correctamente."""
    logger.info("Consultando balances del exchange...")
    
    try:
        balance = bot.exchange.fetch_balance()
        
        if 'total' in balance:
            # Listar monedas principales (BTC, USDT y algunas más si existen)
            currencies = ['BTC', 'USDT', 'ETH', 'USDC']
            balances_info = {}
            
            for curr in currencies:
                if curr in balance['total'] and balance['total'][curr] > 0:
                    balances_info[curr] = {
                        'free': balance['free'][curr] if curr in balance['free'] else 0,
                        'used': balance['used'][curr] if curr in balance['used'] else 0,
                        'total': balance['total'][curr]
                    }
            
            if balances_info:
                logger.info("Balances disponibles:")
                for curr, info in balances_info.items():
                    logger.info(f"  {curr}: Libre: {info['free']}, En uso: {info['used']}, Total: {info['total']}")
            else:
                logger.warning("No se encontraron balances positivos para las principales monedas")
            
            logger.info("✅ Consulta de balances exitosa")
            return True
        else:
            logger.error("❌ La estructura del balance recibido no es la esperada")
            return False
    except Exception as e:
        logger.error(f"❌ Error al consultar balances: {str(e)}")
        return False

def test_balances_detailed(bot):
    """Verificar balances en todas las cuentas de Bitget con detalle."""
    logger.info("Consultando balances detallados en todas las cuentas de Bitget...")
    
    found_usdt = False
    
    try:
        # 1. Verificar el balance estándar primero (account type: spot)
        try:
            standard_balance = bot.exchange.fetch_balance()
            
            # Verificar si hay USDT en la cuenta principal de spot
            if 'USDT' in standard_balance and standard_balance['USDT']['total'] > 0:
                logger.info(f"✓ Balance USDT en cuenta SPOT: {standard_balance['USDT']['total']} USDT")
                found_usdt = True
            else:
                logger.info("✗ No hay USDT en la cuenta principal de SPOT según CCXT standard")
        except Exception as e:
            logger.error(f"Error al consultar balance principal: {str(e)}")
        
        # 2. Intentar consultar balances para diferentes tipos de cuentas
        account_types = [
            {'type': 'spot', 'name': 'SPOT'},
            {'type': 'swap', 'name': 'SWAP/FUTUROS'},
            {'type': 'future', 'name': 'FUTUROS'},
            {'type': 'margin', 'name': 'MARGEN'},
            {'type': 'funding', 'name': 'FINANCIACIÓN'},
            {'type': 'unified', 'name': 'UNIFICADA'}
        ]
        
        for acc in account_types:
            try:
                balance = bot.exchange.fetch_balance({'type': acc['type']})
                if 'USDT' in balance and balance['USDT']['total'] > 0:
                    logger.info(f"✓ Balance USDT en cuenta {acc['name']}: {balance['USDT']['total']} USDT")
                    found_usdt = True
            except Exception:
                # No mostramos errores si el tipo de cuenta no está disponible
                pass
        
        # 3. Consultar balances para cuentas específicas de contratos (futures/swap)
        try:
            # Caso específico para cuentas de contratos
            if hasattr(bot.exchange, 'fetch_balance_unified'):
                unified_balance = bot.exchange.fetch_balance_unified()
                if 'USDT' in unified_balance and unified_balance['USDT']['total'] > 0:
                    logger.info(f"✓ Balance USDT en cuenta UNIFICADA: {unified_balance['USDT']['total']} USDT")
                    found_usdt = True
        except Exception:
            pass
            
        # 4. Usar llamadas API directas si están disponibles
        try:
            # Usando el endpoint directo para Bitget V2
            if hasattr(bot.exchange, 'private_get_api_wallet_v1_account_assets'):
                assets = bot.exchange.private_get_api_wallet_v1_account_assets({'coin': 'USDT'})
                logger.info(f"Respuesta directa API de assets: {assets}")
                if 'data' in assets and assets['data']:
                    for asset in assets['data']:
                        if 'coinName' in asset and asset['coinName'].upper() == 'USDT':
                            available = float(asset.get('available', '0'))
                            frozen = float(asset.get('frozen', '0'))
                            total = available + frozen
                            logger.info(f"✓ USDT en Bitget (API directa): Disponible={available}, Congelado={frozen}, Total={total}")
                            found_usdt = True
        except Exception as e:
            logger.info(f"No se pudo usar el método API directo: {str(e)}")
        
        # 5. Llamada específica para Bitget para obtener todos los activos
        try:
            # Intentar una consulta específica si está disponible
            if hasattr(bot.exchange, 'fetch_accounts'):
                accounts = bot.exchange.fetch_accounts()
                logger.info(f"Cuentas disponibles: {accounts}")
            elif hasattr(bot.exchange, 'fetch_positions'):
                positions = bot.exchange.fetch_positions()
                logger.info(f"Posiciones disponibles: {positions}")
        except Exception:
            pass
        
        # 6. Intentar llamadas específicas con parámetros extras para cuentas mix (futures)
        futures_markets = ['BTCUSDT_UMCBL', 'BTCUSDT']
        for market in futures_markets:
            try:
                positions = bot.exchange.fetch_positions([market])
                for position in positions:
                    if position['info'].get('marginCoin') == 'USDT' and float(position['info'].get('available', '0')) > 0:
                        logger.info(f"✓ USDT en posición de futuros para {market}: {position['info'].get('available')} USDT")
                        found_usdt = True
            except Exception:
                pass
        
        # 7. Verificar balance de sub-cuentas si existe
        try:
            if hasattr(bot.exchange, 'fetch_subaccounts'):
                subaccounts = bot.exchange.fetch_subaccounts()
                logger.info(f"Subcuentas disponibles: {subaccounts}")
        except Exception:
            pass
        
        # Resultado final
        if found_usdt:
            logger.info("✅ Se encontraron balances de USDT en al menos una cuenta")
            return True
        else:
            logger.warning("⚠️ No se encontró ningún balance de USDT en las cuentas consultadas")
            
            # Verificar si estamos en modo testnet/sandbox
            if bot.exchange.urls.get('api') and 'testnet' in bot.exchange.urls['api']:
                logger.warning("⚠️ NOTA: Estás conectado a un entorno de TESTNET/SANDBOX, que podría tener balances diferentes")
            logger.info("Sugerencia: Verifica manualmente en tu cuenta de Bitget dónde están tus USDT")
            return False
    except Exception as e:
        logger.error(f"❌ Error al consultar balances detallados: {str(e)}")
        return False

def test_order_execution_real(bot, amount=0.0001):
    """
    Probar la ejecución de órdenes reales con un monto mínimo.
    
    ADVERTENCIA: Esta función ejecutará órdenes reales en el exchange y 
    utilizará fondos reales. Solo debe utilizarse con un monto mínimo y
    con pleno conocimiento de las consecuencias.
    
    Args:
        bot: Instancia del bot de trading
        amount: Cantidad de BTC para la transacción (debe ser un valor muy pequeño)
                Por defecto es 0.0001 BTC (aproximadamente 5-10 USD dependiendo del precio)
    """
    logger.info(f"ADVERTENCIA: Se ejecutarán órdenes reales con {amount} BTC")
    logger.info("Ejecutando pruebas de órdenes reales...")
    
    # Variables para rastrear estado
    test_status = {
        'buy_executed': False,
        'sell_executed': False,
        'entry_price': None,
        'exit_price': None
    }
    
    try:
        # Verificar balances antes
        balance_before = bot.exchange.fetch_balance()
        if 'USDT' in balance_before['free']:
            usdt_balance = balance_before['free']['USDT']
            logger.info(f"Balance USDT antes de la prueba: {usdt_balance}")
            
            # Verificar si hay fondos suficientes
            if usdt_balance <= 0:
                logger.error("❌ No hay fondos USDT disponibles para realizar pruebas de compra")
                return False
        else:
            logger.error("❌ No se puede determinar el balance de USDT")
            return False
        
        # Obtener precio actual
        ticker = bot.exchange.fetch_ticker(bot.symbol)
        current_price = ticker['last']
        logger.info(f"Precio actual de BTC: {current_price} USDT")
        
        # Calcular el costo total y verificar que sea lo suficientemente pequeño
        cost = amount * current_price
        if cost > 20:  # Limitar a $20 USD como máximo
            new_cost = 20
            new_amount = new_cost / current_price
            logger.warning(f"Monto ajustado a {new_amount:.8f} BTC (~20 USDT) por seguridad")
            amount = new_amount
            cost = new_cost
        
        # Verificar que haya fondos suficientes
        if usdt_balance < cost:
            logger.error(f"❌ Balance insuficiente: {usdt_balance} USDT (se necesita al menos {cost:.2f} USDT)")
            return False
        
        # Configurar opciones específicas para Bitget
        original_options = bot.exchange.options
        
        # Para Bitget, configurar createMarketBuyOrderRequiresPrice = False
        if 'bitget' in bot.exchange.id.lower():
            logger.info("Configurando opciones específicas para Bitget...")
            
            # Hacer una copia de las opciones existentes para restaurarlas después
            if bot.exchange.options is None:
                bot.exchange.options = {}
            else:
                bot.exchange.options = dict(bot.exchange.options)
                
            # Configurar la opción específica para órdenes de mercado
            bot.exchange.options['createMarketBuyOrderRequiresPrice'] = False
            
            logger.info("Opción configurada: createMarketBuyOrderRequiresPrice = False")
        
        # Ejecutar una compra real - Para Bitget pasamos el costo total en lugar de la cantidad
        logger.info(f"⚠️ Ejecutando compra real por valor de {cost:.2f} USDT a ~{current_price} USDT/BTC")
        try:
            if 'bitget' in bot.exchange.id.lower():
                # Para Bitget, pasar el costo en el parámetro amount
                buy_order = bot.exchange.create_market_buy_order(
                    symbol=bot.symbol,
                    amount=cost  # Esto es el costo total en USDT, no la cantidad en BTC
                )
            else:
                # Para otros exchanges, usar el método estándar
                buy_order = bot.exchange.create_market_buy_order(
                    symbol=bot.symbol,
                    amount=amount
                )
                
            test_status['buy_executed'] = True
            test_status['entry_price'] = current_price
            logger.info(f"✅ Compra ejecutada correctamente")
            logger.info(f"Detalles de la orden: {buy_order}")
            
            # Obtener la cantidad real comprada del resultado de la orden
            if 'amount' in buy_order:
                amount = buy_order['amount']
                logger.info(f"Cantidad real comprada: {amount} BTC")
            
        except Exception as e:
            logger.error(f"❌ Error al ejecutar compra real: {str(e)}")
            # Restaurar opciones originales
            bot.exchange.options = original_options
            return False
        
        # Esperar un momento antes de vender para asegurarse de que la orden se procesó
        import time
        logger.info("Esperando 3 segundos...")
        time.sleep(3)
        
        # Verificar balance después de la compra
        balance_after_buy = bot.exchange.fetch_balance()
        if 'BTC' in balance_after_buy['free']:
            btc_balance = balance_after_buy['free']['BTC']
            logger.info(f"Balance BTC después de la compra: {btc_balance}")
            
            # Si no hay BTC suficiente, usar lo que tengamos
            if btc_balance < amount:
                logger.warning(f"Cantidad ajustada para venta: {btc_balance} BTC (menor que la compra original)")
                amount = btc_balance
        
        # Ejecutar una venta real para cerrar la posición
        logger.info(f"⚠️ Ejecutando venta real de {amount:.8f} BTC")
        try:
            sell_order = bot.exchange.create_market_sell_order(
                symbol=bot.symbol,
                amount=amount
            )
            test_status['sell_executed'] = True
            
            # Obtener el precio actual de nuevo para calcular P&L
            ticker = bot.exchange.fetch_ticker(bot.symbol)
            exit_price = ticker['last']
            test_status['exit_price'] = exit_price
            
            # Calcular P&L
            if test_status['entry_price']:
                pnl_pct = (exit_price - test_status['entry_price']) / test_status['entry_price'] * 100
                pnl_usd = amount * (exit_price - test_status['entry_price'])
                logger.info(f"P&L: {pnl_pct:.4f}% / {pnl_usd:.4f} USDT")
            
            logger.info(f"✅ Venta ejecutada correctamente")
            logger.info(f"Detalles de la orden: {sell_order}")
        except Exception as e:
            logger.error(f"❌ Error al ejecutar venta real: {str(e)}")
            if test_status['buy_executed']:
                logger.critical(f"⚠️ ATENCIÓN: La compra se ejecutó pero no la venta. Tienes {amount} BTC en posición.")
            # Restaurar opciones originales
            bot.exchange.options = original_options
            return False
        
        # Restaurar opciones originales
        bot.exchange.options = original_options
        
        # Verificar balance final
        balance_after = bot.exchange.fetch_balance()
        if 'USDT' in balance_after['free']:
            logger.info(f"Balance USDT después de las pruebas: {balance_after['free']['USDT']}")
        
        return test_status['buy_executed'] and test_status['sell_executed']
    except Exception as e:
        logger.error(f"❌ Error en prueba de órdenes reales: {str(e)}")
        # Asegurarse de restaurar las opciones originales
        try:
            bot.exchange.options = original_options
        except:
            pass
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
        
        # Ejecutar ciclo de trading (sin modificar las funciones originales)
        # Esto no ejecutará órdenes si no hay señales válidas
        bot.run_trading_cycle()
        
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

def run_real_tests():
    """Ejecutar pruebas con operaciones reales (usar con precaución)."""
    logger.info("="*50)
    logger.info("⚠️ INICIANDO PRUEBAS CON OPERACIONES REALES ⚠️")
    logger.info(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*50)
    
    # Verificar credenciales
    credentials_ok = setup_credentials()
    if not credentials_ok:
        logger.error("No se puede continuar sin credenciales válidas")
        return False
    
    # Solicitar confirmación en consola
    print("\n" + "!"*80)
    print("!! ADVERTENCIA: Estás a punto de ejecutar pruebas que realizarán operaciones REALES !!")
    print("!! Estas operaciones utilizarán fondos reales de tu cuenta de Bitget           !!")
    print("!"*80 + "\n")
    
    confirmation = input("¿Estás seguro de querer continuar con operaciones reales? (escribe 'SI' para confirmar): ")
    if confirmation.strip().upper() != "SI":
        logger.info("Pruebas canceladas por el usuario")
        return False
    
    # Inicializar bot
    bot = test_bot_initialization()
    if bot is None:
        logger.error("No se puede continuar sin un bot inicializado")
        return False
    
    # Verificar balances
    balance_test_result = test_balances(bot)
    if not balance_test_result:
        logger.warning("Advertencia: Problemas al verificar balances")
    
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
    
    # Ejecutar operaciones reales de prueba
    # Se usa un monto muy pequeño (0.0001 BTC, equivalente a unos 5-10 USD)
    trade_result = test_order_execution_real(bot, amount=0.0001)
    
    # Probar ciclo de trading
    cycle_test_result = test_trading_cycle(bot)
    
    # Resumen final
    logger.info("="*50)
    logger.info("RESUMEN DE PRUEBAS REALES")
    logger.info("="*50)
    logger.info(f"✅ Configuración de credenciales: {credentials_ok}")
    logger.info(f"✅ Inicialización del bot: {bot is not None}")
    logger.info(f"✅ Verificación de balances: {balance_test_result}")
    logger.info(f"✅ Obtención de datos: {df is not None}")
    logger.info(f"✅ Cálculo de indicadores: {df_with_indicators is not None}")
    logger.info(f"✅ Detección de señales: {signal_test_result}")
    logger.info(f"✅ Ejecución de órdenes reales: {trade_result}")
    logger.info(f"✅ Ciclo de trading: {cycle_test_result}")
    
    all_passed = (credentials_ok and
                 bot is not None and
                 df is not None and 
                 df_with_indicators is not None and 
                 signal_test_result and 
                 trade_result and 
                 cycle_test_result)
    
    if all_passed:
        logger.info("✅ TODAS LAS PRUEBAS REALES COMPLETADAS EXITOSAMENTE")
    else:
        logger.warning("⚠️ ALGUNAS PRUEBAS REALES FALLARON")
    
    logger.info("="*50)
    return all_passed

def run_balance_check():
    """Ejecutar solo la verificación de balances detallados."""
    logger.info("="*50)
    logger.info("VERIFICACIÓN DETALLADA DE BALANCES")
    logger.info(f"Fecha y hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*50)
    
    # Verificar credenciales
    credentials_ok = setup_credentials()
    if not credentials_ok:
        logger.error("No se puede continuar sin credenciales válidas")
        return False
    
    # Inicializar bot
    bot = test_bot_initialization()
    if bot is None:
        logger.error("No se puede continuar sin un bot inicializado")
        return False
    
    # Verificar balances detallados
    logger.info("\n---- RESULTADO DE LA VERIFICACIÓN DETALLADA DE BALANCES ----\n")
    balance_detailed_result = test_balances_detailed(bot)
    logger.info("\n---------------------------------------------------------\n")
    
    return balance_detailed_result

if __name__ == "__main__":
    # Cargar variables de entorno
    load_dotenv()
    
    # Ejecutar pruebas reales en lugar de solo verificar balances
    run_real_tests()