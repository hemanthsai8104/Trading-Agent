# strategy.py (FINAL - No pandas-ta)

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

def analyze_market_and_decide(daily_data, current_position, config):
    analysis = {}
    
    long_window = config.get('LONG_WINDOW', 50)
    short_window = config.get('SHORT_WINDOW', 20)

    if daily_data is None or len(daily_data) < long_window:
        analysis['reason'] = "Not enough daily data to analyze."
        return 'HOLD', analysis
        
    try:
        # --- THIS BLOCK IS REPLACED ---
        rsi_series = calculate_rsi(daily_data['Close'])
        analysis['rsi'] = rsi_series.iloc[-1].item()
        
        short_mavg = daily_data['Close'].rolling(window=short_window).mean()
        long_mavg = daily_data['Close'].rolling(window=long_window).mean()
        
        analysis['current_price'] = daily_data['Close'].iloc[-1].item()
        analysis['short_ma'] = short_mavg.iloc[-1].item()
        analysis['long_ma'] = long_mavg.iloc[-1].item()
        
    except (ValueError, IndexError, AttributeError) as e:
        analysis['reason'] = f"Could not calculate indicators: {e}"
        return 'HOLD', analysis

    if current_position is None:
        analysis['status'] = "Looking for a buy opportunity."
        try:
            prev_short = short_mavg.iloc[-2].item()
            prev_long = long_mavg.iloc[-2].item()
            curr_short = analysis['short_ma']
            curr_long = analysis['long_ma']

            is_golden_cross = prev_short < prev_long and curr_short > curr_long
            is_not_overbought = analysis.get('rsi', 0) < 70

            if is_golden_cross:
                if is_not_overbought:
                    analysis['reason'] = f"Golden Cross detected and RSI ({analysis.get('rsi', 0):.2f}) is not overbought. Favorable entry."
                    return 'BUY', analysis
                else:
                    analysis['reason'] = f"Golden Cross detected, but RSI ({analysis.get('rsi', 0):.2f}) is overbought. Waiting for a pullback."
                    return 'HOLD', analysis
            else:
                if curr_short < curr_long:
                    analysis['reason'] = "Bearish Trend (MA Cross). Waiting for reversal."
                else:
                    analysis['reason'] = "Bullish Trend, but no Golden Cross signal."
                return 'HOLD', analysis

        except (ValueError, IndexError):
            analysis['reason'] = "Moving average data is still calculating."
            return 'HOLD', analysis
    else:
        try:
            prev_short = short_mavg.iloc[-2].item()
            prev_long = long_mavg.iloc[-2].item()
            curr_short = analysis['short_ma']
            curr_long = analysis['long_ma']
            
            is_death_cross = prev_short > prev_long and curr_short < curr_long

            if is_death_cross:
                analysis['reason'] = "Death Cross detected! Trend has reversed, forcing liquidation."
                return 'SELL', analysis
            else:
                buy_price = float(current_position.avg_entry_price)
                current_price = float(analysis['current_price'])
                profit_percentage = ((current_price - buy_price) / buy_price) * 100
                analysis['status'] = f"Position held. Profit: {profit_percentage:.2f}%. Protected by OCO order."
                analysis['reason'] = "Trend is still favorable. Letting OCO order manage profit/loss targets."
                return 'HOLD', analysis
        except (ValueError, IndexError, TypeError):
            analysis['reason'] = "Price data is invalid. Holding position and OCO order."
            return 'HOLD', analysis