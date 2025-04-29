import ccxt
import os
from dotenv import load_dotenv
import pandas as pd
import time

load_dotenv()

# Global offset (in milliseconds)
time_offset = 0

class BinanceFuturesConnector:
    def __init__(self):
        global time_offset

        self.exchange = ccxt.binance({
            'apiKey': os.getenv("BINANCE_API_KEY"),
            'secret': os.getenv("BINANCE_SECRET_KEY"),
            'options': {
                'defaultType': 'future',
                'recvWindow': 10000  # Increase recvWindow to tolerate delays
            },
            'enableRateLimit': True,
        })

        # Fetch Binance server time once at start
        try:
            server_time = self.exchange.fetch_time()
            local_time = int(time.time() * 1000)  # in ms
            time_offset = server_time - local_time
            print(f"[INFO] Adjusted timestamp by {time_offset}ms")
        except Exception as e:
            print("[ERROR] Could not fetch server time:", e)

    def fetch_ohlcv(self, symbol="BTC/USDT", timeframe="1h", limit=100):
        ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df

    def create_market_buy_order(self, symbol, size):
        params = {'timestamp': self.get_synced_timestamp()}
        order = self.exchange.create_order(
            symbol=symbol,
            type='market',
            side='buy',
            amount=size,
            price=None,
            params=params
        )
        return order

    def create_market_sell_order(self, symbol, size):
        params = {'timestamp': self.get_synced_timestamp()}
        order = self.exchange.create_order(
            symbol=symbol,
            type='market',
            side='sell',
            amount=size,
            price=None,
            params=params
        )
        return order

    def get_synced_timestamp(self):
        global time_offset
        return int((time.time() * 1000) + time_offset)