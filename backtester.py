# backtester.py (FINAL - No pandas-ta)

import pandas as pd
import numpy as np

# --- ADD THIS HELPER FUNCTION AT THE TOP ---
def calculate_rsi(data, window=14):
    """A manual implementation of RSI calculation using pandas."""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    # Avoid division by zero
    rs = gain / loss
    rs = rs.replace([np.inf, -np.inf], np.nan).fillna(0)
    
    rsi = 100 - (100 / (1 + rs))
    return rsi

def run_backtest(df_historical, strategy_params):
    if df_historical.empty:
        return {"success": False, "error": "Historical data is empty."}

    short_window = strategy_params.get('short_window')
    long_window = strategy_params.get('long_window')
    
    # --- THIS BLOCK IS REPLACED ---
    df_historical['RSI_14'] = calculate_rsi(df_historical['close'])
    df_historical['short_ma'] = df_historical['close'].rolling(window=short_window).mean()
    df_historical['long_ma'] = df_historical['close'].rolling(window=long_window).mean()
    
    df_historical.dropna(inplace=True)

    trades = []
    position = None
    entry_price = 0
    equity = 100000

    for i in range(1, len(df_historical)):
        prev_row = df_historical.iloc[i-1]
        curr_row = df_historical.iloc[i]
        
        is_golden_cross = prev_row['short_ma'] < prev_row['long_ma'] and curr_row['short_ma'] > curr_row['long_ma']
        is_not_overbought = curr_row['RSI_14'] < 70
        
        if position is None and is_golden_cross and is_not_overbought:
            position = 'LONG'
            entry_price = curr_row['close']
            entry_date = curr_row.name
            trades.append({
                "entry_date": entry_date.strftime('%Y-%m-%d'), 
                "entry_price": entry_price, 
                "exit_date": None, "exit_price": None, "pnl_pct": None
            })

        elif position == 'LONG':
            is_death_cross = prev_row['short_ma'] > prev_row['long_ma'] and curr_row['short_ma'] < curr_row['long_ma']
            take_profit_price = entry_price * (1 + strategy_params.get('take_profit') / 100)
            stop_loss_price = entry_price * (1 - strategy_params.get('stop_loss') / 100)

            exit_reason = None
            if curr_row['high'] >= take_profit_price:
                exit_price = take_profit_price; exit_reason = "Take Profit"
            elif curr_row['low'] <= stop_loss_price:
                exit_price = stop_loss_price; exit_reason = "Stop Loss"
            elif is_death_cross:
                exit_price = curr_row['close']; exit_reason = "Death Cross"

            if exit_reason:
                position = None
                exit_date = curr_row.name
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                
                trades[-1].update({ "exit_date": exit_date.strftime('%Y-%m-%d'), "exit_price": exit_price, "pnl_pct": pnl_pct, "reason": exit_reason })
                equity *= (1 + pnl_pct / 100)

    completed_trades = [t for t in trades if t['exit_date'] is not None]
    total_trades = len(completed_trades)
    winning_trades = len([t for t in completed_trades if t['pnl_pct'] is not None and t['pnl_pct'] > 0])
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    total_pnl = ((equity - 100000) / 100000) * 100

    metrics = {
        "total_pnl_pct": total_pnl, "win_rate_pct": win_rate, "total_trades": total_trades,
        "winning_trades": winning_trades, "losing_trades": (total_trades - winning_trades)
    }

    df_chart = df_historical.reset_index()
    chart_data = {
        "candlesticks": [{'x': row['timestamp'].isoformat(), 'y': [row['open'], row['high'], row['low'], row['close']]} for _, row in df_chart.iterrows()],
        "short_ma": [{'x': row['timestamp'].isoformat(), 'y': row['short_ma']} for _, row in df_chart.iterrows()],
        "long_ma": [{'x': row['timestamp'].isoformat(), 'y': row['long_ma']} for _, row in df_chart.iterrows()]
    }

    return {"success": True, "metrics": metrics, "trades": trades, "chart_data": chart_data}