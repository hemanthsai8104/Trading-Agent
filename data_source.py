# data_source.py (With Definitive Live Chart Fix)

from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from datetime import datetime, timedelta, timezone
import config

try:
    data_client = StockHistoricalDataClient(config.API_KEY, config.API_SECRET)
    print("DATA SOURCE: Successfully connected to Alpaca Market Data API.")
except Exception as e:
    data_client = None
    print(f"DATA SOURCE: FATAL ERROR - Could not connect to Alpaca Market Data API. Error: {e}")

# This function is for the AGENT and is unchanged
def get_daily_data(symbol, days, long_window):
    if not data_client: return None
    print(f"DATA SOURCE: Fetching last {days} days of daily data for {symbol} from Alpaca...")
    try:
        total_days_to_fetch = days + long_window
        start_date = datetime.now() - timedelta(days=total_days_to_fetch)
        request_params = StockBarsRequest(symbol_or_symbols=[symbol], timeframe=TimeFrame.Day, start=start_date)
        bars = data_client.get_stock_bars(request_params)
        if bars.df.empty: return None
        data = bars.df.droplevel('symbol')
        data.rename(columns={'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'volume': 'Volume'}, inplace=True)
        return data.tail(days)
    except Exception as e:
        print(f"DATA SOURCE: Error fetching daily data from Alpaca for {symbol}: {e}")
        return None

# ====================================================================
# == THIS IS THE DEFINITIVELY CORRECTED FUNCTION ==
# ====================================================================
def get_live_bars(symbol, timeframe_str, limit=80):
    """
    Fetches intraday bars from the last few hours to ensure a "zoomed-in" live view.
    """
    if not data_client: return None
    print(f"DATA SOURCE: Fetching recent live '{timeframe_str}' bars for {symbol}...")
    try:
        timeframe_map = {
            "1T": TimeFrame(1, TimeFrameUnit.Minute),
            "5T": TimeFrame(5, TimeFrameUnit.Minute),
            "15T": TimeFrame(15, TimeFrameUnit.Minute),
            "1H": TimeFrame(1, TimeFrameUnit.Hour),
        }
        alpaca_timeframe = timeframe_map.get(timeframe_str, TimeFrame(1, TimeFrameUnit.Day))

        # THE FIX: Instead of just a limit, we specify a START TIME.
        # This forces the API to only give us data from the last 8 hours,
        # ensuring the chart is always focused on recent activity.
        # We use timezone-aware datetime for robustness.
        start_time = datetime.now(timezone.utc) - timedelta(hours=8)

        request_params = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=alpaca_timeframe,
            start=start_time 
            # We no longer need limit, as the start time is more precise.
        )
        bars = data_client.get_stock_bars(request_params)
        if bars.df.empty: return None
        return bars.df.droplevel('symbol')
    except Exception as e:
        print(f"DATA SOURCE: Error fetching live bars from Alpaca for {symbol}: {e}")
        return None