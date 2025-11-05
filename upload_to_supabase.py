# upload_to_supabase.py

import os
import pandas as pd
from datetime import datetime, timedelta

# --- Import Alpaca Clients ---
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# --- Import Supabase Client ---
from supabase import create_client, Client

# --- Import your configuration ---
import config

# --- 1. Define the List of Stock Symbols ---
SYMBOLS = [
    'TSLA', 'NVDA', 'AAPL', 'GOOGL', 'MSFT',
    'AMZN', 'META', 'JPM', 'V', 'UNH'
]

# --- 2. Define the Timeframe and Date Range ---
DATA_INTERVAL = TimeFrame(5, TimeFrameUnit.Minute)
end_date = datetime.now() - timedelta(days=1)
start_date = end_date - timedelta(days=365)

# ====================================================================
# == THIS FUNCTION HAS BEEN EDITED FOR DEBUGGING ==
# ====================================================================
def create_supabase_client():
    """Initializes and returns a Supabase client."""
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        print("FATAL ERROR: Supabase URL or Key not found in .env file.")
        return None
        
    # --- DEBUGGING STEP ---
    # This will print the first 20 characters of the key your script is actually using.
    # We will compare this to the service_role key on your Supabase dashboard.
    print("\n" + "="*20 + " DEBUGGING INFO " + "="*20)
    print(f"Key being used starts with: {config.SUPABASE_KEY[:20]}")
    print("Compare the line above with the start of the 'service_role' key in Supabase.")
    print("="*56 + "\n")
    # --- END DEBUGGING STEP ---
    
    return create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
# ====================================================================


def create_stock_table_if_not_exists(supabase: Client, table_name: str):
    """Creates a new table in Supabase for a stock symbol if it doesn't already exist."""
    try:
        supabase.table(table_name).select("timestamp", head=True).limit(1).execute()
        print(f"DATABASE: Table '{table_name}' already exists. Skipping creation.")
        return
    except Exception:
        print(f"DATABASE: Table '{table_name}' not found. Creating it now...")
        sql_command = f"""
            CREATE TABLE public."{table_name}" (
                "timestamp" timestamp with time zone NOT NULL,
                "open" double precision,
                "high" double precision,
                "low" double precision,
                "close" double precision,
                "volume" bigint,
                "trade_count" bigint,
                "vwap" double precision,
                CONSTRAINT "{table_name}_pkey" PRIMARY KEY ("timestamp")
            );
        """
        try:
            supabase.rpc('exec', {'sql': sql_command}).execute()
            print(f"DATABASE: Table '{table_name}' created successfully.")
        except Exception as e:
            print(f" -> DATABASE ERROR: Failed to create table '{table_name}'. Details: {e}")

def main():
    """Main function to fetch data and upload it to Supabase."""
    print("\n" + "="*50)
    print("Starting data upload process to Supabase...")
    print("="*50)

    supabase = create_supabase_client()
    if not supabase: return

    data_client = StockHistoricalDataClient(config.API_KEY, config.API_SECRET)

    for symbol in SYMBOLS:
        table_name = symbol.lower()
        print(f"\n--- Processing symbol: {symbol} ---")

        create_stock_table_if_not_exists(supabase, table_name)

        print(f"ALPACA: Fetching 1 year of 5-min data for {symbol}...")
        try:
            request_params = StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=DATA_INTERVAL,
                start=start_date,
                end=end_date
            )
            bars = data_client.get_stock_bars(request_params)
            data_df = bars.df
        except Exception as e:
            print(f" -> ERROR: Failed to fetch data from Alpaca for {symbol}: {e}")
            continue

        if data_df.empty:
            print(f" -> WARNING: No data returned from Alpaca for {symbol}.")
            continue

        # --- THIS IS THE DEFINITIVE FIX BLOCK ---
        # 1. Reset the index to turn 'timestamp' and 'symbol' into columns.
        data_df.reset_index(inplace=True)
        
        # 2. Drop the redundant 'symbol' column.
        if 'symbol' in data_df.columns:
            data_df.drop('symbol', axis=1, inplace=True)
        
        # 3. **CRITICAL FIX:** Convert float columns that should be integers.
        #    The .astype(int) method will safely convert "2339.0" to the integer 2339.
        if 'volume' in data_df.columns:
            data_df['volume'] = data_df['volume'].astype(int)
        if 'trade_count' in data_df.columns:
            data_df['trade_count'] = data_df['trade_count'].astype(int)

        # 4. Format the timestamp column to a string for JSON compatibility.
        data_df['timestamp'] = data_df['timestamp'].dt.strftime('%Y-m-%dT%H:%M:%S%z')
        
        # 5. Now, aconvert the perfectly cleaned DataFrame to the upload format.
        data_to_upload = data_df.to_dict(orient='records')
        # --- END OF FIX BLOCK ---

        chunk_size = 1000
        total_rows = len(data_to_upload)
        print(f"SUPABASE: Preparing to upload {total_rows} rows in chunks of {chunk_size}...")

        for i in range(0, total_rows, chunk_size):
            chunk = data_to_upload[i:i + chunk_size]
            print(f" -> Uploading chunk {i//chunk_size + 1}/{(total_rows//chunk_size) + 1}...")
            try:
                supabase.table(table_name).upsert(chunk).execute()
            except Exception as e:
                print(f"    -> ERROR: Failed to upload chunk: {e}")
        
        print(f" -> SUCCESS: Finished uploading data for {symbol}.")

    print("\n" + "="*50)
    print("All data has been uploaded to Supabase.")
    print("="*50)

if __name__ == "__main__":
    main()