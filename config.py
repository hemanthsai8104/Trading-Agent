# config.py

import os
from dotenv import load_dotenv

load_dotenv()

# --- API Credentials ---
API_KEY = os.getenv('APCA_API_KEY_ID')
API_SECRET = os.getenv('APCA_API_SECRET_KEY')
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# --- List of symbols for the Insights Dashboard Dropdown ---
SYMBOLS = [
    'TSLA', 'NVDA', 'AAPL', 'GOOGL', 'MSFT',
    'AMZN', 'META', 'JPM', 'V', 'UNH'
]

# --- Trading Strategy Parameters (these apply to all stocks in the watchlist) ---
TRADE_QUANTITY = 1
DAYS_OF_DATA = 100
SHORT_WINDOW = 20
LONG_WINDOW = 50
TAKE_PROFIT_THRESHOLD = 3.0
STOP_LOSS_THRESHOLD = 1.5

# --- Agent Timing ---
SLEEP_INTERVAL = 300 # Check every 5 minutes