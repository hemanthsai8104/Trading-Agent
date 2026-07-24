# Trading Agent

A Python-based automated trading agent that connects to a broker API, executes strategies, tracks a watchlist, and backtests performance — with a simple web dashboard for monitoring.

## Features

- **Automated Strategy Execution:** Runs configurable trading strategies against live market data.
- **Broker Integration:** Connects to a broker API for order placement and account data.
- **Backtesting:** Evaluate strategy performance against historical data before going live.
- **Watchlist Management:** Track a configurable list of symbols for monitoring and trading.
- **Data Persistence:** Stores trade/status data using Supabase.
- **Web Dashboard:** Flask-based interface for monitoring agent status.

## Tech Stack

- **Backend:** Python, Flask
- **Data Storage:** Supabase
- **Frontend:** HTML/CSS (Flask templates)

## Project Structure

Trading-Agent/
├── static/ # CSS/JS assets for the web dashboard
├── templates/ # HTML templates for the Flask app
├── agent.py # Core trading agent logic
├── app.py # Flask application entry point
├── backtester.py # Strategy backtesting engine
├── broker.py # Broker API integration
├── config.py # Configuration settings
├── data_source.py # Market data fetching
├── database.py # Database connection/operations
├── strategy.py # Trading strategy logic
├── strategy_config.json # Strategy parameters
├── trading_agent.py # Main trading agent runner
├── upload_to_supabase.py # Syncs data to Supabase
├── watchlist.json # List of tracked symbols
├── status.json # Agent status/state tracking
└── requirements.txt


## Getting Started

### Prerequisites

- Python 3.8+
- A broker API account (for live trading)
- A Supabase project (for data storage)

### Installation

1. **Clone the repository:**
```bash
   git clone https://github.com/hemanthsai8104/Trading-Agent.git
   cd Trading-Agent
```

2. **Create a virtual environment and install dependencies:**
```bash
   python -m venv venv

   # Windows
   .\venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate

   pip install -r requirements.txt
```

3. **Configure environment variables:**
   Create a `.env` file in the root directory with your broker API credentials and Supabase connection details. This file should never be committed to version control.

### Running the App

**Start the Flask dashboard:**
```bash
python app.py
```

**Run the trading agent:**
```bash
python trading_agent.py
```

**Run a backtest:**
```bash
python backtester.py
```

## Disclaimer

This software is for educational purposes only. Algorithmic trading involves significant financial risk. The developer of this repository is not responsible for any financial losses incurred while using this code. Always test strategies thoroughly in a controlled environment before using real funds.
