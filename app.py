# app.py (FINAL, WITH TOTAL P&L CALCULATION)

import time, json, atexit, traceback, os
from threading import Thread
from flask import Flask, render_template, jsonify, request
import yfinance as yf
import pandas as pd
import config, database, data_source, strategy, backtester
from broker import AlpacaBroker
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from alpaca.trading.enums import ActivityType

broker = None; agent_thread = None; stop_agent = False
app = Flask(__name__)

# ... (The first part of your app.py is unchanged and correct) ...
def read_strategy_config():
    if not os.path.exists('strategy_config.json'):
        default_config = { "SHORT_WINDOW": 20, "LONG_WINDOW": 50, "TAKE_PROFIT_THRESHOLD": 3.0, "STOP_LOSS_THRESHOLD": 1.5 }
        with open('strategy_config.json', 'w') as f: json.dump(default_config, f, indent=4)
        return default_config
    try:
        with open('strategy_config.json', 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return { "SHORT_WINDOW": 20, "LONG_WINDOW": 50, "TAKE_PROFIT_THRESHOLD": 3.0, "STOP_LOSS_THRESHOLD": 1.5 }

def run_trading_cycle(shared_broker):
    print(f"\n{'='*50}\nAGENT: Running trading cycle at {time.ctime()}...")
    strategy_params = read_strategy_config()
    write_status({"message": "Agent is analyzing market data..."})
    watchlist = read_watchlist(); live_statuses = {}
    if not watchlist: write_status({"message": "Watchlist is empty. Add a stock to begin."}); return
    for symbol in watchlist:
        try:
            position = shared_broker.get_position(symbol)
            open_order = shared_broker.get_open_order(symbol)
            daily_data = data_source.get_daily_data(symbol, config.DAYS_OF_DATA, strategy_params['LONG_WINDOW'])
            decision, analysis = strategy.analyze_market_and_decide(daily_data, position, strategy_params)
            analysis['action'] = decision
            live_statuses[symbol] = analysis
            if decision == 'BUY' and not position and not open_order:
                shared_broker.place_buy_order(symbol, config.TRADE_QUANTITY)
            elif decision == 'SELL' and position:
                shared_broker.place_sell_order(symbol, position.qty)
            elif position and not open_order:
                entry_price = float(position.avg_entry_price)
                quantity = float(position.qty)
                take_profit_price = entry_price * (1 + strategy_params['TAKE_PROFIT_THRESHOLD'] / 100)
                stop_loss_price = entry_price * (1 - strategy_params['STOP_LOSS_THRESHOLD'] / 100)
                shared_broker.place_oco_order(symbol, quantity, take_profit_price, stop_loss_price)
        except Exception as e:
            print(f" -> ERROR analyzing {symbol}: {e}")
            live_statuses[symbol] = {"reason": f"An error occurred: {e}", "action": "HOLD"}
    sleep_minutes = config.SLEEP_INTERVAL // 60
    summary_message = f"Analysis done. Agent is sleeping for {sleep_minutes} minutes..."
    live_statuses['_summary'] = {"message": summary_message}
    write_status(live_statuses); print("="*50)

def agent_loop(shared_broker):
    print("BACKGROUND AGENT: Starting...")
    while not stop_agent:
        run_trading_cycle(shared_broker)
        print(f"AGENT: Cycle complete. Sleeping for {config.SLEEP_INTERVAL} seconds...")
        for _ in range(config.SLEEP_INTERVAL):
            if stop_agent: break
            time.sleep(1)
    print("BACKGROUND AGENT: Stopped.")

def start_background_agent(shared_broker):
    global agent_thread
    if agent_thread is None or not agent_thread.is_alive():
        with open('status.json', 'w') as f: json.dump({"message": "Agent is starting..."}, f)
        agent_thread = Thread(target=agent_loop, args=(shared_broker,)); agent_thread.daemon = True; agent_thread.start()
        print("Flask App: Background agent thread started.")

def stop_background_agent():
    global stop_agent; stop_agent = True
    if agent_thread and agent_thread.is_alive(): agent_thread.join()

def read_watchlist():
    try:
        with open('watchlist.json', 'r') as f: content = f.read(); return json.loads(content) if content else []
    except (FileNotFoundError, json.JSONDecodeError):
        with open('watchlist.json', 'w') as f: json.dump([], f); return []

def write_status(status_data):
    with open('status.json', 'w') as f: json.dump(status_data, f, indent=4)

@app.route('/')
def index(): return render_template('index.html', symbols=config.SYMBOLS)


# ====================================================================
# == THIS IS THE CORRECTED API ENDPOINT WITH TOTAL P&L ==
# ====================================================================
@app.route('/api/agent_status')
def get_agent_status():
    if not broker or not broker.client: return jsonify({"success": False, "error": "Broker not connected."}), 500
    try:
        account = broker.get_account()
        if not account: raise Exception("Failed to get account.")
        
        watchlist = read_watchlist()
        positions = broker.get_all_positions()
        open_orders = broker.get_all_open_orders()
        all_activities = broker.get_activities()

        position_data = [{"symbol": p.symbol, "qty": p.qty, "avg_entry_price": float(p.avg_entry_price)} for p in positions]
        order_data = [{"symbol": o.symbol, "qty": o.qty, "side": o.side.value, "status": o.status.value} for o in open_orders]
        
        closed_position_data = []
        if all_activities:
            fills = [act for act in all_activities if act.get('activity_type') == 'FILL']
            fills.sort(key=lambda x: x['transaction_time'])

            buy_fills = {}
            sell_fills = {}
            for fill in fills:
                symbol = fill['symbol']
                if fill['side'] == 'buy':
                    if symbol not in buy_fills: buy_fills[symbol] = []
                    buy_fills[symbol].append(fill)
                else: # sell
                    if symbol not in sell_fills: sell_fills[symbol] = []
                    sell_fills[symbol].append(fill)
            
            for symbol, sells in sell_fills.items():
                if symbol in buy_fills:
                    buys = buy_fills[symbol]
                    for sell in sells:
                        if len(buys) > 0:
                            buy = buys.pop(0) 
                            
                            sell_qty = float(sell['qty'])
                            sell_price = float(sell['price'])
                            buy_qty = float(buy['qty'])
                            buy_price = float(buy['price'])
                            
                            if sell_qty == buy_qty:
                                pnl = (sell_price - buy_price) * sell_qty
                                closed_position_data.append({
                                    "symbol": symbol,
                                    "qty": sell_qty,
                                    "realized_pl": round(pnl, 2)
                                })
        
        # THE NEW ADDITION: Calculate the sum of all realized P/L
        total_realized_pl = sum(trade['realized_pl'] for trade in closed_position_data)
        
        return jsonify({
            "success": True, 
            "account_balance": float(account.cash), 
            "watchlist": watchlist, 
            "positions": position_data, 
            "open_orders": order_data,
            "closed_positions": closed_position_data,
            "total_realized_pl": total_realized_pl  # Send the total to the frontend
        })
    except Exception as e: 
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500
# ====================================================================


# ... (The rest of your app.py is correct and unchanged) ...
@app.route('/api/live_log')
def get_live_log():
    try:
        with open('status.json', 'r') as f: return jsonify({"success": True, "data": json.load(f)})
    except: return jsonify({"success": False, "error": "Status file not found."})

@app.route('/api/update_watchlist', methods=['POST'])
def update_watchlist():
    data = request.get_json()
    try:
        watchlist = read_watchlist()
        if data['action'] == 'add' and data['symbol'] not in watchlist: watchlist.append(data['symbol'])
        elif data['action'] == 'remove' and data['symbol'] in watchlist: watchlist.remove(data['symbol'])
        with open('watchlist.json', 'w') as f: json.dump(watchlist, f, indent=4)
        return jsonify({"success": True, "watchlist": watchlist})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/settings', methods=['GET'])
def get_settings():
    return jsonify({"success": True, "settings": read_strategy_config()})

@app.route('/api/settings', methods=['POST'])
def save_settings():
    try:
        data = request.get_json()
        updated_config = { "SHORT_WINDOW": int(data.get('SHORT_WINDOW')), "LONG_WINDOW": int(data.get('LONG_WINDOW')), "TAKE_PROFIT_THRESHOLD": float(data.get('TAKE_PROFIT_THRESHOLD')), "STOP_LOSS_THRESHOLD": float(data.get('STOP_LOSS_THRESHOLD')) }
        with open('strategy_config.json', 'w') as f: json.dump(updated_config, f, indent=4)
        return jsonify({"success": True, "message": "Settings saved successfully."})
    except (TypeError, ValueError) as e: return jsonify({"success": False, "error": f"Invalid data format: {e}"}), 400
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/analyze_data')
def analyze_data():
    try:
        symbol = request.args.get('symbol'); interval = request.args.get('interval'); start_date_str = request.args.get('start_date'); end_date_str = request.args.get('end_date')
        if not all([symbol, interval, start_date_str, end_date_str]): return jsonify({"success": False, "error": "Missing required parameters."}), 400
        interval_map = {'1T': '1min', '5T': '5min', '15T': '15min', '1H': '1H', '1D': '1D'}; pandas_interval = interval_map.get(interval)
        table_name = symbol.lower(); df_raw = database.fetch_data_by_range(table_name, start_date_str, end_date_str)
        if df_raw.empty: return jsonify({"success": False, "error": "No historical data found for the selected date range."}), 404
        ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}; df_resampled = df_raw.resample(pandas_interval).apply(ohlc_dict).dropna()
        if df_resampled.empty: return jsonify({"success": False, "error": "No data available for this interval and date range combination."}), 404
        df_chart = df_resampled.reset_index()
        chart_data = [{'x': row['timestamp'].isoformat(), 'y': [row['open'], row['high'], row['low'], row['close']]} for _, row in df_chart.iterrows()]
        table_data = df_resampled.reset_index(); table_data['timestamp'] = table_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S'); table_data_records = table_data.to_dict(orient='records')
        return jsonify({"success": True, "data": {"chart_data": chart_data, "table_data": table_data_records}})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": f"A server error occurred: {str(e)}"}), 500

@app.route('/api/get_expiration_dates')
def get_expiration_dates():
    symbol = request.args.get('symbol')
    if not symbol: return jsonify({"success": False, "error": "Symbol parameter is missing."}), 400
    try:
        ticker = yf.Ticker(symbol); expirations = ticker.options
        return jsonify({"success": True, "dates": expirations})
    except Exception as e: return jsonify({"success": False, "error": f"Could not fetch expiration dates for {symbol}: {e}"}), 500

@app.route('/api/options_chain')
def get_options_chain():
    symbol = request.args.get('symbol'); date = request.args.get('date')
    if not symbol or not date: return jsonify({"success": False, "error": "Missing symbol or date parameters."}), 400
    try:
        ticker = yf.Ticker(symbol); chain = ticker.option_chain(date)
        calls_df = chain.calls.fillna(0); puts_df = chain.puts.fillna(0)
        return jsonify({"success": True, "calls": calls_df.to_dict(orient='records'), "puts": puts_df.to_dict(orient='records')})
    except Exception as e: return jsonify({"success": False, "error": f"Could not fetch options chain for {symbol} on {date}: {e}"}), 500

@app.route('/api/get_live_bars')
def get_live_bars():
    symbol = request.args.get('symbol'); interval = request.args.get('interval')
    if not symbol or not interval: return jsonify({"success": False, "error": "Missing symbol or interval."}), 400
    try:
        bars_df = data_source.get_live_bars(symbol, interval)
        if bars_df is None: return jsonify({"success": False, "error": "No live data available from Alpaca."}), 404
        df_chart = bars_df.reset_index().rename(columns={"index": "timestamp"})
        chart_data = [{'x': row['timestamp'].isoformat(), 'y': [row['open'], row['high'], row['low'], row['close']]} for _, row in df_chart.iterrows()]
        return jsonify({"success": True, "data": chart_data})
    except Exception as e: return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/backtest')
def backtest_strategy():
    try:
        symbol = request.args.get('symbol'); start_date = request.args.get('start_date'); end_date = request.args.get('end_date')
        strategy_params = { "short_window": int(request.args.get('short_window')), "long_window": int(request.args.get('long_window')), "take_profit": float(request.args.get('take_profit')), "stop_loss": float(request.args.get('stop_loss')) }
        table_name = symbol.lower(); df_daily_raw = database.fetch_data_by_range(table_name, start_date, end_date)
        if df_daily_raw.empty: return jsonify({"success": False, "error": "No historical data found for this date range."}), 404
        if 'timestamp' in df_daily_raw.columns:
            df_daily_raw['timestamp'] = pd.to_datetime(df_daily_raw['timestamp']); df_daily_raw.set_index('timestamp', inplace=True)
        ohlc_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}; df_daily = df_daily_raw.resample('1D').apply(ohlc_dict).dropna()
        if df_daily.empty or len(df_daily.index) < strategy_params['long_window']:
            error_message = (f"Not enough daily data to run the backtest. " f"The selected range produced only {len(df_daily.index)} days of data, " f"but the strategy requires at least {strategy_params['long_window']} days to calculate the Long MA. " f"Please select a longer date range.")
            return jsonify({"success": False, "error": error_message}), 400
        results = backtester.run_backtest(df_daily, strategy_params); return jsonify(results)
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "error": f"A server error occurred during backtest: {e}"}), 500

@app.route('/api/market_status')
def get_market_status():
    try:
        eastern_time = ZoneInfo("America/New_York")
    except ZoneInfoNotFoundError:
        return jsonify({"success": False, "error": "Timezone data not found on server."}), 500
    now_et = datetime.now(eastern_time)
    market_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now_et.replace(hour=16, minute=0, second=0, microsecond=0)
    is_weekday = now_et.weekday() < 5 
    is_market_hours = market_open <= now_et <= market_close
    is_open = is_weekday and is_market_hours
    return jsonify({"success": True, "is_open": is_open})

if __name__ == '__main__':
    broker = AlpacaBroker(config.API_KEY, config.API_SECRET)
    if broker.client:
        start_background_agent(broker)
        atexit.register(stop_background_agent)
    app.run(debug=True, port=5001, use_reloader=True)