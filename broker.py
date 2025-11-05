# broker.py (FINAL, CLEAN VERSION)

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, GetOrdersRequest, TakeProfitRequest, StopLossRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce, QueryOrderStatus, OrderClass, ActivityType
import traceback

class AlpacaBroker:
    def __init__(self, api_key, api_secret):
        self.client = None
        try:
            client = TradingClient(api_key, api_secret, paper=True)
            self.client = client
            print("BROKER: Successfully connected and verified with Alpaca.")
        except Exception as e:
            print(f"BROKER: FATAL ERROR - Could not connect to Alpaca. Check API keys. Error: {e}")

    def get_account(self):
        if not self.client: return None
        try: return self.client.get_account()
        except Exception as e: print(f"BROKER: Error getting account details: {e}"); return None

    def get_position(self, symbol):
        if not self.client: return None
        try: return self.client.get_open_position(symbol)
        except Exception: return None
    
    def get_all_positions(self):
        if not self.client: return []
        try: return self.client.get_all_positions()
        except Exception as e: print(f"BROKER: Error getting all positions: {e}"); return []

    def get_activities(self, page_size=100):
        if not self.client: return []
        try:
            url = "/account/activities"
            params = { "page_size": page_size }
            raw_activities = self.client.get(path=url, data=params)
            return raw_activities
        except Exception as e:
            print(f"BROKER: Error getting activities:")
            traceback.print_exc()
            return []

    def get_all_open_orders(self):
        if not self.client: return []
        try:
            request_params = GetOrdersRequest(status='open')
            return self.client.get_orders(filter=request_params)
        except Exception as e: print(f"BROKER: Error getting all open orders: {e}"); return []
            
    def get_open_order(self, symbol):
        if not self.client: return None
        try:
            request_params = GetOrdersRequest(status='all', symbols=[symbol], limit=10)
            orders = self.client.get_orders(filter=request_params)
            active_statuses = ['new', 'held', 'partially_filled', 'accepted']
            for order in orders:
                if order.status in active_statuses:
                    return order 
            return None
        except Exception as e: 
            print(f"BROKER: Error checking for open orders for {symbol}:")
            traceback.print_exc()
            return None

    def cancel_open_orders_for_symbol(self, symbol):
        if not self.client: return False
        try:
            self.client.cancel_orders(symbol=symbol)
            return True
        except Exception as e:
            print(f"BROKER: Error canceling orders for {symbol}: {e}")
            return False

    def place_buy_order(self, symbol, quantity):
        if not self.client: return False
        try:
            market_order_data = MarketOrderRequest(
                symbol=symbol, qty=quantity, side=OrderSide.BUY, time_in_force=TimeInForce.GTC
            )
            self.client.submit_order(order_data=market_order_data)
            return True
        except Exception as e:
            print(f"\n!!! BROKER: FAILED to submit buy order for {symbol}. Error: {e}\n")
            return False

    def place_sell_order(self, symbol, quantity):
        if not self.client: return False
        try:
            self.cancel_open_orders_for_symbol(symbol)
            self.client.close_position(symbol)
            return True
        except Exception as e: 
            print(f"BROKER: Error submitting sell order: {e}"); return False
            
    def place_oco_order(self, symbol, quantity, take_profit_price, stop_loss_price):
        if not self.client: return False
        try:
            oco_order_data = LimitOrderRequest(
                symbol=symbol, qty=quantity, side=OrderSide.SELL, time_in_force=TimeInForce.GTC, order_class=OrderClass.OCO,
                take_profit=TakeProfitRequest(limit_price=round(take_profit_price, 2)),
                stop_loss=StopLossRequest(stop_price=round(stop_loss_price, 2))
            )
            self.client.submit_order(order_data=oco_order_data)
            return True
        except Exception as e:
            print(f"\n!!! BROKER: FAILED to submit OCO order for {symbol}. Error: {e}\n")
            return False