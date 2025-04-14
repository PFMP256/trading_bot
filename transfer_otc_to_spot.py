#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para transferir fondos entre cuentas de Bitget.
Este script facilita la transferencia de fondos desde la cuenta OTC a la cuenta Spot.
"""

import os
import sys
import logging
import time
from dotenv import load_dotenv
import ccxt

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("transfer_funds.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("BitgetTransfer")

def setup_exchange():
    """Configurar la conexión con el exchange Bitget."""
    # Cargar variables de entorno
    load_dotenv()
    
    # Obtener las credenciales
    api_key = os.getenv('API_KEY')
    api_secret = os.getenv('API_SECRET')
    api_password = os.getenv('API_PASSWORD')
    
    if not all([api_key, api_secret, api_password]):
        logger.error("❌ Faltan credenciales. Verifica tu archivo .env")
        return None
    
    try:
        # Inicializar el exchange con credenciales
        exchange = ccxt.bitget({
            'apiKey': api_key,
            'secret': api_secret,
            'password': api_password,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',  # Tipo de mercado por defecto
            }
        })
        
        logger.info("Conexión con Bitget establecida correctamente")
        return exchange
    except Exception as e:
        logger.error(f"❌ Error al inicializar exchange: {str(e)}")
        return None

def check_all_balances(exchange):
    """Verificar balances en todas las cuentas disponibles."""
    account_types = ['spot', 'swap', 'future', 'margin', 'funding', 'otc']
    
    all_balances = {}
    
    for acc_type in account_types:
        try:
            params = {'type': acc_type}
            balance = exchange.fetch_balance(params)
            
            # Filtrar solo monedas con balance positivo
            coins_with_balance = {
                coin: balance[coin]
                for coin in balance
                if isinstance(balance[coin], dict) and 
                   'total' in balance[coin] and 
                   balance[coin]['total'] > 0
            }
            
            if coins_with_balance:
                logger.info(f"Cuenta {acc_type.upper()}: Encontrados balances positivos")
                all_balances[acc_type] = coins_with_balance
                
                for coin, details in coins_with_balance.items():
                    if coin in ['USDT', 'BTC', 'ETH']:  # Solo mostrar monedas principales
                        logger.info(f"  {coin}: {details['free']} libre, {details['used']} en uso, {details['total']} total")
            else:
                logger.info(f"Cuenta {acc_type.upper()}: No se encontraron balances positivos")
        except Exception as e:
            logger.info(f"No se pudo consultar cuenta {acc_type}: {str(e)}")
    
    return all_balances

def transfer_funds(exchange, from_account="otc", to_account="spot", currency="USDT", amount=None):
    """
    Transferir fondos entre cuentas de Bitget.
    
    Args:
        exchange: Instancia del exchange
        from_account: Cuenta origen ('spot', 'swap', 'otc', etc.)
        to_account: Cuenta destino ('spot', 'swap', 'otc', etc.)
        currency: Moneda a transferir (ej. 'USDT')
        amount: Cantidad a transferir. Si es None, se transferirá todo el saldo disponible.
    """
    try:
        # Verificar el balance en la cuenta de origen
        try:
            params = {'type': from_account}
            from_balance = exchange.fetch_balance(params)
            
            if currency not in from_balance or from_balance[currency]['free'] <= 0:
                logger.error(f"❌ No hay balance de {currency} disponible en la cuenta {from_account}")
                return False
            
            available_amount = from_balance[currency]['free']
            logger.info(f"Balance disponible en cuenta {from_account}: {available_amount} {currency}")
            
            # Si no se especifica la cantidad, transferir todo el saldo disponible
            if amount is None:
                amount = available_amount
            elif amount > available_amount:
                logger.warning(f"⚠️ Cantidad solicitada ({amount}) es mayor que el saldo disponible ({available_amount}). Se transferirá el máximo disponible.")
                amount = available_amount
        except Exception as e:
            logger.error(f"❌ Error al verificar balance en cuenta {from_account}: {str(e)}")
            return False
        
        # Realizar la transferencia utilizando la API de Bitget directamente
        try:
            # En Bitget la transferencia entre cuentas internas se realiza con el método transfer
            # Las cuentas internas en Bitget pueden tener diferentes nombres: 
            # - spot: Cuenta spot
            # - mix_usdt: Cuenta USDT-M Futures
            # - mix_usd: Cuenta USD-S Futures
            # - margin: Cuenta de margen
            # - otc: Cuenta OTC
            
            # Mapear nombres de cuentas al formato que espera Bitget
            account_map = {
                'spot': 'spot',
                'swap': 'mix_usdt',
                'future': 'mix_usd',
                'margin': 'margin',
                'otc': 'otc',
                'funding': 'funding'
            }
            
            from_account_type = account_map.get(from_account, from_account)
            to_account_type = account_map.get(to_account, to_account)
            
            # Llamar al método de transferencia
            # Parámetros: moneda, cantidad, cuenta origen, cuenta destino
            transfer_params = {
                'coin': currency,
                'amount': str(amount),  # Bitget espera la cantidad como string
                'from': from_account_type,
                'to': to_account_type
            }
            
            # Uso directo de la API
            result = exchange.private_post_spot_v1_wallet_transfer(transfer_params)
            logger.info(f"Respuesta de transferencia: {result}")
            
            if 'code' in result and result['code'] == '00000':
                logger.info(f"✅ Transferencia exitosa: {amount} {currency} desde {from_account} a {to_account}")
                return True
            else:
                error_msg = result.get('msg', 'Error desconocido')
                logger.error(f"❌ Error en la transferencia: {error_msg}")
                return False
        except Exception as e:
            logger.error(f"❌ Error en la transferencia: {str(e)}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Error general en la transferencia: {str(e)}")
        return False

def main():
    """Función principal."""
    print("\n" + "="*70)
    print("    TRANSFERENCIA DE FONDOS ENTRE CUENTAS DE BITGET")
    print("="*70 + "\n")
    
    # Configurar el exchange
    exchange = setup_exchange()
    if not exchange:
        print("❌ No se pudo establecer conexión con Bitget. Verifica tus credenciales.")
        return
    
    # Comprobar balances en todas las cuentas
    print("\nVerificando balances en todas las cuentas disponibles...\n")
    all_balances = check_all_balances(exchange)
    
    # Mostrar opciones al usuario
    print("\n" + "-"*70)
    print("TRANSFERENCIA DE FONDOS")
    print("-"*70)
    
    # Determinar cuentas con fondos
    accounts_with_funds = []
    for acc_type, balances in all_balances.items():
        if balances:
            accounts_with_funds.append(acc_type)
    
    if not accounts_with_funds:
        print("❌ No se encontraron fondos en ninguna cuenta.")
        return
    
    # Solicitar datos para la transferencia
    from_account = input(f"Cuenta de origen (opciones: {', '.join(accounts_with_funds)}): ") or "otc"
    if from_account not in accounts_with_funds:
        print(f"❌ No hay fondos en la cuenta {from_account} o no existe.")
        return
    
    # Mostrar monedas disponibles en la cuenta seleccionada
    available_coins = list(all_balances[from_account].keys())
    print(f"Monedas disponibles en {from_account}: {', '.join(available_coins)}")
    
    currency = input("Moneda a transferir (ej. USDT): ") or "USDT"
    if currency not in all_balances[from_account]:
        print(f"❌ No hay balance de {currency} en la cuenta {from_account}.")
        return
    
    # Mostrar balance disponible
    available_amount = all_balances[from_account][currency]['free']
    print(f"Balance disponible: {available_amount} {currency}")
    
    amount_input = input(f"Cantidad a transferir (dejar en blanco para transferir todo el saldo): ")
    amount = float(amount_input) if amount_input else None
    
    to_account = input("Cuenta de destino (ej. spot): ") or "spot"
    
    # Confirmar la transferencia
    if amount is not None:
        confirm_msg = f"¿Confirmar transferencia de {amount} {currency} desde {from_account} a {to_account}? (s/n): "
    else:
        confirm_msg = f"¿Confirmar transferencia de TODO el saldo disponible ({available_amount} {currency}) desde {from_account} a {to_account}? (s/n): "
    
    confirm = input(confirm_msg).lower()
    if confirm != "s":
        print("Transferencia cancelada.")
        return
    
    # Realizar la transferencia
    print("\nRealizando transferencia...\n")
    success = transfer_funds(exchange, from_account, to_account, currency, amount)
    
    if success:
        print(f"\n✅ Transferencia completada con éxito.")
        
        # Verificar el nuevo balance
        print("\nVerificando nuevos balances...\n")
        time.sleep(2)  # Esperar un momento para que la transferencia se procese
        check_all_balances(exchange)
    else:
        print("\n❌ La transferencia no pudo completarse.")

if __name__ == "__main__":
    main()