#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para visualizar la estrategia de day trading con datos históricos
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import ccxt
from dotenv import load_dotenv
from ta.trend import EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

# Cargar variables de entorno
load_dotenv()

def fetch_historical_data(symbol='BTC/USDT', timeframe='15m', limit=500):
    """Obtener datos históricos de OHLCV para análisis."""
    exchange_id = os.getenv('EXCHANGE_ID', 'binance')
    
    try:
        # Inicializar el exchange sin API keys para datos públicos
        exchange_class = getattr(ccxt, exchange_id)
        exchange = exchange_class({
            'enableRateLimit': True
        })
        
        # Obtener datos OHLCV
        ohlcv = exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit
        )
        
        # Crear DataFrame
        df = pd.DataFrame(
            ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        return df
    
    except Exception as e:
        print(f"Error al obtener datos históricos: {str(e)}")
        return None

def add_indicators(df):
    """Añadir indicadores técnicos al DataFrame."""
    if df is None or df.empty:
        return None
    
    # EMA de 20 y 50 periodos
    df['ema20'] = EMAIndicator(close=df['close'], window=20).ema_indicator()
    df['ema50'] = EMAIndicator(close=df['close'], window=50).ema_indicator()
    
    # RSI
    df['rsi'] = RSIIndicator(close=df['close'], window=14).rsi()
    
    # MACD
    macd = MACD(
        close=df['close'],
        window_slow=26,
        window_fast=12,
        window_sign=9
    )
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()
    
    # Bandas de Bollinger
    bollinger = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_high'] = bollinger.bollinger_hband()
    df['bb_mid'] = bollinger.bollinger_mavg()
    df['bb_low'] = bollinger.bollinger_lband()
    
    return df

def identify_signals(df):
    """Identificar señales de compra y venta según la estrategia."""
    # Inicializar columnas de señales
    df['buy_signal'] = False
    df['sell_signal'] = False
    
    # Recorrer el DataFrame saltando las primeras 50 filas que necesitamos para calcular los indicadores
    for i in range(50, len(df)-1):
        # Verificar señal de compra
        current_row = df.iloc[i]
        prev_row = df.iloc[i-1]
        
        # Condiciones para compra
        ema_crossover = (prev_row['ema20'] <= prev_row['ema50']) and (current_row['ema20'] > current_row['ema50'])
        rsi_condition = (prev_row['rsi'] <= 30) and (current_row['rsi'] > 30)
        macd_crossover = (prev_row['macd'] <= prev_row['macd_signal']) and (current_row['macd'] > current_row['macd_signal'])
        bollinger_support = (current_row['close'] <= current_row['bb_low'] * 1.01)
        
        # Combinación de señales (al menos 2 de 4 condiciones)
        buy_signal_count = sum([ema_crossover, rsi_condition, macd_crossover, bollinger_support])
        if buy_signal_count >= 2:
            df.at[df.index[i], 'buy_signal'] = True
        
        # Condiciones para venta
        ema_crossover_sell = (prev_row['ema20'] >= prev_row['ema50']) and (current_row['ema20'] < current_row['ema50'])
        rsi_condition_sell = (prev_row['rsi'] <= 70) and (current_row['rsi'] > 70)
        macd_crossover_sell = (prev_row['macd'] >= prev_row['macd_signal']) and (current_row['macd'] < current_row['macd_signal'])
        bollinger_resistance = (current_row['close'] >= current_row['bb_high'] * 0.99)
        
        # Combinación de señales (al menos 2 de 4 condiciones)
        sell_signal_count = sum([ema_crossover_sell, rsi_condition_sell, macd_crossover_sell, bollinger_resistance])
        if sell_signal_count >= 2:
            df.at[df.index[i], 'sell_signal'] = True
    
    return df

def backtest_strategy(df, initial_capital=100, risk_per_trade=0.02, leverage=1.0, take_profit=0.03, stop_loss=0.01):
    """Realizar un backtesting simple de la estrategia."""
    if df is None or df.empty:
        return None, None
    
    # Crear DataFrame para resultados
    results = pd.DataFrame(index=df.index)
    results['capital'] = initial_capital  # Capital inicial
    
    # Variables para tracking
    in_position = False
    entry_price = 0
    position_size = 0
    trades = []
    
    # Recorrer el DataFrame
    for i in range(1, len(df)):
        current_date = df.index[i]
        prev_date = df.index[i-1]
        current_price = df.loc[current_date, 'close']
        
        # Actualizar el capital con el mismo valor que el período anterior
        results.loc[current_date, 'capital'] = results.loc[prev_date, 'capital']
        
        # Si estamos en posición, verificar si es momento de vender
        if in_position:
            # Verificar take profit
            if current_price >= entry_price * (1 + take_profit):
                # Calcular ganancia
                pnl = position_size * (current_price - entry_price)
                # Actualizar capital
                results.loc[current_date, 'capital'] += pnl
                # Registrar trade
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': current_date,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'position_size': position_size,
                    'pnl': pnl,
                    'pnl_pct': (current_price - entry_price) / entry_price * 100,
                    'exit_reason': 'take_profit'
                })
                # Resetear posición
                in_position = False
                
            # Verificar stop loss
            elif current_price <= entry_price * (1 - stop_loss):
                # Calcular pérdida
                pnl = position_size * (current_price - entry_price)
                # Actualizar capital
                results.loc[current_date, 'capital'] += pnl
                # Registrar trade
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': current_date,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'position_size': position_size,
                    'pnl': pnl,
                    'pnl_pct': (current_price - entry_price) / entry_price * 100,
                    'exit_reason': 'stop_loss'
                })
                # Resetear posición
                in_position = False
                
            # Verificar señal de venta
            elif df.loc[current_date, 'sell_signal']:
                # Calcular P&L
                pnl = position_size * (current_price - entry_price)
                # Actualizar capital
                results.loc[current_date, 'capital'] += pnl
                # Registrar trade
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': current_date,
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'position_size': position_size,
                    'pnl': pnl,
                    'pnl_pct': (current_price - entry_price) / entry_price * 100,
                    'exit_reason': 'sell_signal'
                })
                # Resetear posición
                in_position = False
            
        # Si no estamos en posición, verificar si es momento de comprar
        elif df.loc[current_date, 'buy_signal']:
            # Calcular el tamaño de la posición basado en el riesgo
            capital = results.loc[prev_date, 'capital']
            risk_amount = capital * risk_per_trade
            position_size_usd = risk_amount * leverage
            position_size = position_size_usd / current_price
            
            # Actualizar estado
            in_position = True
            entry_price = current_price
            entry_date = current_date
    
    # Si aún estamos en posición al final del período, cerrar la posición
    if in_position:
        last_date = df.index[-1]
        last_price = df.loc[last_date, 'close']
        
        # Calcular P&L
        pnl = position_size * (last_price - entry_price)
        # Actualizar capital
        results.loc[last_date, 'capital'] += pnl
        # Registrar trade
        trades.append({
            'entry_date': entry_date,
            'exit_date': last_date,
            'entry_price': entry_price,
            'exit_price': last_price,
            'position_size': position_size,
            'pnl': pnl,
            'pnl_pct': (last_price - entry_price) / entry_price * 100,
            'exit_reason': 'end_of_period'
        })
    
    # Crear DataFrame de trades
    trades_df = pd.DataFrame(trades)
    
    # Calcular rendimiento
    if not results.empty:
        initial_capital = results.iloc[0]['capital']
        final_capital = results.iloc[-1]['capital']
        total_return = (final_capital - initial_capital) / initial_capital * 100
        print(f"Capital inicial: ${initial_capital:.2f}")
        print(f"Capital final: ${final_capital:.2f}")
        print(f"Rendimiento total: {total_return:.2f}%")
        
        if not trades_df.empty:
            print(f"Número de operaciones: {len(trades_df)}")
            print(f"Ganancia promedio: {trades_df['pnl'].mean():.2f}")
            print(f"% de operaciones ganadoras: {(trades_df['pnl'] > 0).mean() * 100:.2f}%")
    
    return results, trades_df

def plot_strategy(df, results=None, trades_df=None):
    """Visualizar la estrategia en gráficos."""
    if df is None or df.empty:
        print("No hay datos para visualizar.")
        return
    
    # Crear figura y subplots
    fig, axs = plt.subplots(3, 1, figsize=(14, 12), gridspec_kw={'height_ratios': [3, 1, 1]})
    
    # Configurar gráfico de precios y señales
    ax1 = axs[0]
    ax1.set_title('Estrategia de Day Trading BTC/USDT')
    ax1.plot(df.index, df['close'], label='Precio', color='black', alpha=0.7)
    ax1.plot(df.index, df['ema20'], label='EMA 20', color='blue', alpha=0.6)
    ax1.plot(df.index, df['ema50'], label='EMA 50', color='red', alpha=0.6)
    ax1.plot(df.index, df['bb_high'], label='BB Superior', color='gray', linestyle='--', alpha=0.4)
    ax1.plot(df.index, df['bb_mid'], label='BB Media', color='gray', linestyle='-', alpha=0.4)
    ax1.plot(df.index, df['bb_low'], label='BB Inferior', color='gray', linestyle='--', alpha=0.4)
    
    # Marcar señales de compra y venta
    buy_signals = df[df['buy_signal'] == True].index
    sell_signals = df[df['sell_signal'] == True].index
    
    ax1.scatter(buy_signals, df.loc[buy_signals, 'close'], marker='^', color='green', s=100, label='Compra')
    ax1.scatter(sell_signals, df.loc[sell_signals, 'close'], marker='v', color='red', s=100, label='Venta')
    
    # Si hay trades realizados, marcarlos también
    if trades_df is not None and not trades_df.empty:
        for _, trade in trades_df.iterrows():
            # Marcar entradas
            ax1.scatter(trade['entry_date'], trade['entry_price'], marker='>', color='blue', s=80)
            # Marcar salidas con color según razón
            if trade['exit_reason'] == 'take_profit':
                ax1.scatter(trade['exit_date'], trade['exit_price'], marker='<', color='green', s=80)
            elif trade['exit_reason'] == 'stop_loss':
                ax1.scatter(trade['exit_date'], trade['exit_price'], marker='<', color='red', s=80)
            else:
                ax1.scatter(trade['exit_date'], trade['exit_price'], marker='<', color='orange', s=80)
    
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Configurar gráfico de RSI
    ax2 = axs[1]
    ax2.set_title('RSI (14)')
    ax2.plot(df.index, df['rsi'], color='purple', alpha=0.7)
    ax2.axhline(30, color='green', linestyle='--', alpha=0.5)
    ax2.axhline(70, color='red', linestyle='--', alpha=0.5)
    ax2.fill_between(df.index, 30, df['rsi'], where=(df['rsi'] < 30), color='green', alpha=0.3)
    ax2.fill_between(df.index, 70, df['rsi'], where=(df['rsi'] > 70), color='red', alpha=0.3)
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)
    
    # Configurar gráfico de MACD
    ax3 = axs[2]
    ax3.set_title('MACD')
    ax3.plot(df.index, df['macd'], label='MACD', color='blue', alpha=0.7)
    ax3.plot(df.index, df['macd_signal'], label='Señal', color='red', alpha=0.7)
    ax3.bar(df.index, df['macd_diff'], label='Histograma', color='gray', alpha=0.5)
    ax3.axhline(0, color='black', linestyle='-', alpha=0.3)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Si hay resultados de capital, mostrar rendimiento
    if results is not None and not results.empty:
        ax4 = ax1.twinx()
        ax4.plot(results.index, results['capital'], label='Capital', color='green', linestyle='-.')
        ax4.set_ylabel('Capital ($)')
        ax4.legend(loc='upper left')
    
    # Formato de fechas
    for ax in axs:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M'))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
    
    # Ajustar espaciado
    plt.tight_layout()
    plt.savefig('btc_day_trading_strategy.png')
    plt.show()

def main():
    """Función principal."""
    print("Visualizador de Estrategia de Day Trading para BTC/USDT")
    print("------------------------------------------------------")
    
    # Obtener datos históricos
    print("Obteniendo datos históricos...")
    df = fetch_historical_data(limit=500)  # Aproximadamente 5 días en timeframe de 15m
    
    if df is None or df.empty:
        print("Error: No se pudieron obtener datos históricos.")
        return
    
    print(f"Se obtuvieron {len(df)} registros desde {df.index[0]} hasta {df.index[-1]}")
    
    # Añadir indicadores
    print("Calculando indicadores técnicos...")
    df = add_indicators(df)
    
    # Identificar señales
    print("Identificando señales de trading...")
    df = identify_signals(df)
    
    # Backtest
    print("Realizando backtesting de la estrategia...")
    results, trades_df = backtest_strategy(
        df, 
        initial_capital=100,
        risk_per_trade=0.02,
        leverage=3.0,  # Apalancamiento moderado
        take_profit=0.03,
        stop_loss=0.01
    )
    
    # Visualizar
    print("Generando visualización...")
    plot_strategy(df, results, trades_df)
    
    print("Análisis completado. Resultados guardados en 'btc_day_trading_strategy.png'")

if __name__ == "__main__":
    main() 