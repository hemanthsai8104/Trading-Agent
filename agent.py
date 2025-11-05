# agent.py (Final Corrected Version with Complete Syntax)

import time
import json
import config
import data_source
import strategy
from broker import AlpacaBroker

def read_watchlist():
    """Reads the list of stock symbols from watchlist.json."""
    try:
        with open('watchlist.json', 'r') as f:
            content = f.read()
            if not content: return []
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        with open('watchlist.json', 'w') as f:
            json.dump([], f)
        return []

def write_status(status_data):
    """Writes the current analysis status to status.json."""
    try:
        with open('status.json', 'w') as f:
            json.dump(status_data, f, indent=4)
    except Exception as e:
        print(f"AGENT ERROR: Could not write to status.json: {e}")

def run_trading_cycle(broker):
    """Runs a single analysis and trading cycle for all stocks in the watchlist."""
    print("\n" + "="*50)
    print(f"AGENT: Running trading cycle at {time.ctime()}...")

    watchlist = read_watchlist()
    live_statuses = {} 

    if not watchlist:
        print("AGENT: Watchlist is empty. Nothing to trade.")
        write_status({"message": "Watchlist is empty. Add a stock from the dashboard to begin."})
        return

    print(f"AGENT: Analyzing symbols in watchlist: {watchlist}")

    for symbol in watchlist:
        print(f"\n--- Analyzing {symbol} ---")
        try:
            position = broker.get_position(symbol)
            open_order = broker.get_open_order(symbol)
            daily_data = data_source.get_daily_data(symbol, config.DAYS_OF_DATA, config.LONG_WINDOW)

            # This single call to the strategy brain is the correct logic
            decision, analysis = strategy.analyze_market_and_decide(daily_data, position, config)
            live_statuses[symbol] = analysis

            if decision == 'BUY' and not position and not open_order:
                broker.place_buy_order(symbol, config.TRADE_QUANTITY)
            elif decision == 'SELL' and position:
                broker.place_sell_order(symbol, position.qty)
            else:
                print(f"ACTION for {symbol}: No trade executed.")
        
        except Exception as e:
            print(f" -> ERROR analyzing {symbol}: {e}")
            live_statuses[symbol] = {"reason": f"An error occurred: {e}"}
            continue
    
    write_status(live_statuses)
    print("="*50)


if __name__ == '__main__':
    if not config.API_KEY or not config.API_SECRET:
        print("FATAL ERROR: API keys not found in config.")
    else:
        broker = AlpacaBroker(config.API_KEY, config.API_SECRET)
        if not broker.client:
            print("AGENT: Could not connect to broker. Agent will not start.")
        else:
            # --- THIS IS THE CORRECTED AND COMPLETE try-except BLOCK ---
            while True:
                try:
                    run_trading_cycle(broker)
                    print(f"AGENT: Cycle complete. Sleeping for {config.SLEEP_INTERVAL} seconds...")
                    time.sleep(config.SLEEP_INTERVAL)
                except KeyboardInterrupt:
                    print("\nAGENT: Agent stopped manually.")
                    break
                except Exception as e:
                    print(f"AGENT: A critical, unhandled error occurred in the main loop: {e}")
                    print(f"AGENT: Restarting cycle after a short break...")
                    time.sleep(30) # Wait 30 seconds after a major crash before retrying