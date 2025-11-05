import os
import pandas as pd
from dotenv import load_dotenv
import yfinance as yf
import time

# --- Alpaca Trading Imports ---
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce

# --- Load Environment Variables ---
load_dotenv()

# --- Alpaca API Credentials ---
API_KEY = os.getenv('APCA_API_KEY_ID')
API_SECRET = os.getenv('APCA_API_SECRET_KEY')

# --- Trading Parameters ---
STOCK_SYMBOL = 'TSLA'
TRADE_QUANTITY = 5

# --- STRATEGY PARAMETERS ---
# Data & Moving Averages
DAYS_OF_DATA = 100  # "Train" with the last 100 days of data
SHORT_WINDOW = 20
LONG_WINDOW = 50
# Profit/Loss Management
TAKE_PROFIT_THRESHOLD = 3.0 # Sell if profit reaches 3%
STOP_LOSS_THRESHOLD = 1.5  # Sell if loss reaches 1.5%

# --- Agent Timing ---
SLEEP_INTERVAL = 900 # Check every 15 minutes (900 seconds)

def get_daily_data(symbol, days):
    """Fetches historical daily data from Yahoo Finance."""
    print(f"Fetching last {days} days of daily data for {symbol}...")
    try:
        # Fetch an extra buffer of data for MA calculation
        data = yf.download(symbol, period=f"{days + LONG_WINDOW}d", interval="1d", progress=False, auto_adjust=True)
        if data.empty:
            print("No daily data found.")
            return None
        return data.tail(days)
    except Exception as e:
        print(f"Error fetching daily data: {e}")
        return None

def analyze_market_and_decide(daily_data, current_position):
    """Analyzes data and decides whether to Buy, Sell, or Hold."""
    if daily_data is None or len(daily_data) < LONG_WINDOW:
        print("  -> DECISION: Not enough daily data to analyze.")
        return 'HOLD', None, None, None

    # --- Calculate Moving Averages ---
    short_mavg = daily_data['Close'].rolling(window=SHORT_WINDOW).mean()
    long_mavg = daily_data['Long'].rolling(window=LONG_WINDOW).mean()
    
    # Get the latest values for display
    latest_short_mavg = short_mavg.iloc[-1]
    latest_long_mavg = long_mavg.iloc[-1]
    current_price = daily_data['Close'].iloc[-1]

    # --- DECISION LOGIC ---
    if current_position is None: # We are looking to BUY
        print("  -> STATUS: Looking for a buy opportunity.")
        # Golden Cross Signal: The 20-day just crossed above the 50-day
        if short_mavg.iloc[-2] < long_mavg.iloc[-2] and short_mavg.iloc[-1] > long_mavg.iloc[-1]:
            print("  -> DECISION: Golden Cross detected! Favorable uptrend predicted.")
            return 'BUY', latest_short_mavg, latest_long_mavg, current_price
        else:
            print("  -> DECISION: No Golden Cross signal. Waiting for a clear uptrend.")
            return 'HOLD', latest_short_mavg, latest_long_mavg, current_price
            
    else: # We own the stock and are looking to SELL
        buy_price = float(current_position.avg_entry_price)
        profit_percentage = ((current_price - buy_price) / buy_price) * 100
        
        print(f"  -> STATUS: Position held. Bought at ${buy_price:.2f}. Current Profit: {profit_percentage:.2f}%")
        
        if profit_percentage >= TAKE_PROFIT_THRESHOLD:
            print(f"  -> DECISION: Take-profit target of {TAKE_PROFIT_THRESHOLD}% reached.")
            return 'SELL', latest_short_mavg, latest_long_mavg, current_price
        elif profit_percentage <= -STOP_LOSS_THRESHOLD:
            print(f"  -> DECISION: Stop-loss of -{STOP_LOSS_THRESHOLD}% triggered.")
            return 'SELL', latest_short_mavg, latest_long_mavg, current_price
        else:
            print("  -> DECISION: Profit/loss is within thresholds. Holding.")
            return 'HOLD', latest_short_mavg, latest_long_mavg, current_price

def run_trading_logic():
    """Contains the main logic for a single trading check."""
    print("\n" + "="*50)
    print(f"Running trading check at {time.ctime()}...")
    
    trading_client = TradingClient(API_KEY, API_SECRET, paper=True)
    
    # --- 1. Display Account Balance ---
    account = trading_client.get_account()
    print(f"ACCOUNT: Paper trading balance: ${float(account.cash):,.2f}")

    # --- 2. Check Current Position ---
    try:
        current_position = trading_client.get_open_position(STOCK_SYMBOL)
    except Exception:
        current_position = None
    
    status_message = f"POSITION: Holding {current_position.qty} shares." if current_position else "POSITION: No shares held."
    print(status_message)

    # --- 3. "Train" with 100 days of data and make a decision ---
    daily_data = get_daily_data(STOCK_SYMBOL, DAYS_OF_DATA)
    if daily_data is None:
        print("Could not retrieve data. Skipping check.")
        return

    decision, short_ma, long_ma, price = analyze_market_and_decide(daily_data, current_position)
    
    # --- 4. Display Analysis ---
    if short_ma and long_ma and price:
        print(f"ANALYSIS: Current Price: ${price:.2f} | 20-Day MA: ${short_ma:.2f} | 50-Day MA: ${long_ma:.2f}")

    # --- 5. Execute Trade ---
    if decision == 'BUY' and current_position is None:
        print(f"ACTION: Placing BUY order for {TRADE_QUANTITY} shares.")
        try:
            trading_client.submit_order(
                order_data=MarketOrderRequest(symbol=STOCK_SYMBOL, qty=TRADE_QUANTITY, side=OrderSide.BUY, time_in_force=TimeInForce.GTC)
            )
            print("Buy order submitted successfully.")
        except Exception as e:
            print(f"Error submitting buy order: {e}")

    elif decision == 'SELL' and current_position is not None:
        print(f"ACTION: Placing SELL order for all {current_position.qty} shares.")
        try:
            trading_client.close_position(STOCK_SYMBOL)
            print("Sell order submitted successfully.")
        except Exception as e:
            print(f"Error submitting sell order: {e}")
    else:
        print("ACTION: No trade executed.")
    
    print("="*50)

if __name__ == '__main__':
    if not API_KEY or not API_SECRET:
        print("FATAL ERROR: API keys not found. Please create and populate the .env file.")
    else:
        while True:
            try:
                run_trading_logic()
                print(f"Sleeping for {SLEEP_INTERVAL / 60} minutes...")
                time.sleep(SLEEP_INTERVAL)
            except KeyboardInterrupt:
                print("\nAgent stopped manually.")
                break
            except Exception as e:
                print(f"A critical error occurred: {e}")
                print("Restarting logic loop after a short break...")
                time.sleep(SLEEP_INTERVAL)