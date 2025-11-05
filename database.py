# database.py (Final Corrected and Complete Version)

import pandas as pd
from supabase import create_client, Client
import config
from datetime import datetime, timedelta

# --- Initialize Supabase Connection ---
try:
    supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    print("DATABASE: Successfully connected to Supabase.")
except Exception as e:
    print(f"DATABASE: FATAL ERROR - Could not connect to Supabase. Error: {e}")
    supabase = None

# --- Function to UPLOAD Data (No changes needed here) ---
def upload_data(table_name: str, df: pd.DataFrame):
    if supabase is None: return False
    try:
        records = df.to_dict(orient='records')
        supabase.table(table_name).upsert(records).execute()
        print(f"DATABASE: Successfully uploaded {len(records)} records to '{table_name}'.")
        return True
    except Exception as e:
        print(f"DATABASE: Error uploading data to '{table_name}'. Error: {e}")
        return False

# --- Original Fetch Function (Used by old agent scripts, kept for compatibility) ---
def fetch_data(table_name: str, symbol: str):
    """Fetches ALL data from a symbol-specific table."""
    if supabase is None: return pd.DataFrame()
    try:
        response = supabase.table(table_name).select("*").execute()
        df = pd.DataFrame(response.data)
        if df.empty: return pd.DataFrame()
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"DATABASE: Error fetching data from '{table_name}'. Error: {e}")
        return pd.DataFrame()

# --- New Function for the Dashboard to fetch by a period (e.g., '7d') ---
def fetch_data_for_period(table_name: str, period: str):
    """Fetches data from a table for a specific lookback period."""
    if supabase is None: return pd.DataFrame()
    
    if "d" in period:
        days = int(period.replace('d', ''))
        start_date = datetime.now() - timedelta(days=days)
    elif "y" in period:
        years = int(period.replace('y', ''))
        start_date = datetime.now() - timedelta(days=years * 365)
    else:
        start_date = datetime.now() - timedelta(days=365)
        
    try:
        response = supabase.table(table_name).select("*").gte('timestamp', start_date.isoformat()).execute()
        df = pd.DataFrame(response.data)
        if df.empty: return pd.DataFrame()
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df
    except Exception as e:
        print(f"DATABASE: Error fetching period data from '{table_name}'. Error: {e}")
        return pd.DataFrame()

# --- New Function for the Dashboard to fetch by a specific date range ---
def fetch_data_by_range(table_name: str, start_date: str, end_date: str):
    """Fetches data from a table between a specific start and end date."""
    if supabase is None:
        return pd.DataFrame()
    try:
        # Add a day to the end_date to make the query inclusive of the selected end day
        end_date_inclusive = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        
        response = supabase.table(table_name).select("*") \
            .gte('timestamp', start_date) \
            .lt('timestamp', end_date_inclusive) \
            .execute()
        
        df = pd.DataFrame(response.data)
        if df.empty:
            print(f"DATABASE: No data found for range in table '{table_name}'.")
            return pd.DataFrame()
            
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        print(f"DATABASE: Successfully fetched {len(df)} records for range from '{table_name}'.")
        return df
    except Exception as e:
        print(f"DATABASE: Error fetching data by range from '{table_name}'. Error: {e}")
        return pd.DataFrame()