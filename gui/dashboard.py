import os
import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox
from exchange.binance_connector import BinanceFuturesConnector
from strategies.strategy_manager import StrategyManager
from risk.risk_manager import RiskManager
import pandas as pd
import ta
import threading
import yaml

# Optional alerting
try:
    from utils.helpers import send_telegram_message
except ImportError:
    def send_telegram_message(msg):
        print("[TELEGRAM DISABLED] Missing API keys:", msg)

class Dashboard(QWidget):
    def __init__(self, log_callback=None):
        super().__init__()
        self.log_callback = log_callback
        self.connector = BinanceFuturesConnector()
        self.risk_manager = RiskManager()

        # Load configuration
        self.config_path = "config.yaml"
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Missing {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize capital based on paper/live mode
        self.capital = self.config.get("initial_capital", 10000)
        self.in_position = False
        self.position_type = None
        self.entry_price = None

        layout = QVBoxLayout()

        # GUI Elements
        self.symbol_input = QComboBox()
        self.symbol_input.addItems(["BTC/USDT", "ETH/USDT"])
        
        self.strategy_selector = QComboBox()
        self.strategy_selector.addItems(["EMA Crossover", "RSI Divergence", "Bollinger Breakout"])

        self.run_button = QPushButton("Run Live Bot")
        self.run_button.clicked.connect(self.start_live_trading)

        layout.addWidget(QLabel("Select Symbol:"))
        layout.addWidget(self.symbol_input)
        layout.addWidget(QLabel("Select Strategy:"))
        layout.addWidget(self.strategy_selector)
        layout.addWidget(self.run_button)
        self.setLayout(layout)

    def start_live_trading(self):
        """Start live trading in background thread"""
        symbol = self.symbol_input.currentText()
        strategy_name = self.strategy_selector.currentText()
        self.log(f"[INFO] Starting bot for {symbol} using '{strategy_name}' strategy...")
        threading.Thread(target=self._live_trading_loop, args=(symbol, strategy_name), daemon=True).start()

    def _live_trading_loop(self, symbol, strategy_name):
        try:
            strategy = StrategyManager().get_strategy(strategy_name)
            if not strategy:
                raise ValueError(f"Strategy '{strategy_name}' could not be loaded.")

            while True:
                df = self.connector.fetch_ohlcv(symbol=symbol, timeframe=self.config['timeframe'], limit=100)

                # Apply selected strategy
                signal_df = strategy.generate_signal(df.copy())

                # Ensure 'signal' column exists
                if 'signal' not in signal_df.columns:
                    self.log("[ERROR] Strategy did not return valid signals.")
                    time.sleep(60)
                    continue

                latest = signal_df.iloc[-1]
                close_price = latest['close']

                # Calculate ATR for stop-loss
                signal_df['atr'] = ta.volatility.average_true_range(signal_df['high'], signal_df['low'], signal_df['close'], window=14)
                atr_value = float(signal_df['atr'].dropna().iloc[-1])
                stop_loss_distance = atr_value * 1.5

                # Get balance and calculate size
                balance = self.get_account_balance()
                size = self.risk_manager.calculate_position_size(
                    balance,
                    close_price,
                    stop_loss_distance,
                    leverage=int(self.config.get('leverage', 10)),
                    risk_percent=float(self.config.get('risk_per_trade', 0.01))
                )

                # Extract signal safely
                signal = int(latest['signal'])

                # --- Long Entry ---
                if not self.in_position and signal == 1:
                    self.place_long_order(symbol, size)
                    message = f"[LONG] Opening position at ${close_price:.2f}"
                    self.log(message)
                    self.send_alert(message)

                    self.in_position = True
                    self.position_type = 'long'
                    self.entry_price = close_price

                # --- Short Entry ---
                elif not self.in_position and signal == -1:
                    self.place_short_order(symbol, size)
                    message = f"[SHORT] Opening position at ${close_price:.2f}"
                    self.log(message)
                    self.send_alert(message)

                    self.in_position = True
                    self.position_type = 'short'
                    self.entry_price = close_price

                # --- Exit Conditions (Long) ---
                elif self.in_position and self.position_type == 'long':
                    trailing_sl = close_price - atr_value
                    take_profit = self.entry_price + (atr_value * 3)
                    ultimate_sl = self.entry_price - (atr_value * 3)

                    if close_price <= ultimate_sl:
                        profit = close_price - self.entry_price
                        self._exit_position('long', close_price, profit, reason='Ultimate SL')
                    elif close_price >= take_profit:
                        profit = close_price - self.entry_price
                        self._exit_position('long', close_price, profit, reason='Take Profit')
                    elif close_price <= trailing_sl:
                        profit = close_price - self.entry_price
                        self._exit_position('long', close_price, profit, reason='Trailing SL')

                # --- Exit Conditions (Short) ---
                elif self.in_position and self.position_type == 'short':
                    trailing_sl = close_price + atr_value
                    take_profit = self.entry_price - (atr_value * 3)
                    ultimate_sl = self.entry_price + (atr_value * 3)

                    if close_price >= ultimate_sl:
                        profit = self.entry_price - close_price
                        self._exit_position('short', close_price, profit, reason='Ultimate SL')
                    elif close_price <= take_profit:
                        profit = self.entry_price - close_price
                        self._exit_position('short', close_price, profit, reason='Take Profit')
                    elif close_price >= trailing_sl:
                        profit = self.entry_price - close_price
                        self._exit_position('short', close_price, profit, reason='Trailing SL')

                time.sleep(60)  # Re-check every minute

        except Exception as e:
            self.log(f"[ERROR] Live trading failed: {e}")

    def place_long_order(self, symbol, size):
        if self.config.get('paper_mode', True):
            self.log(f"[PAPER] Placed LONG order: {size:.6f} contracts at {symbol}")
        else:
            # Real trading logic here
            self.connector.exchange.create_market_buy_order(symbol, size)
            self.log(f"[LIVE] Long order placed: {size:.6f} on {symbol}")

    def place_short_order(self, symbol, size):
        if self.config.get('paper_mode', True):
            self.log(f"[PAPER] Placed SHORT order: {size:.6f} contracts at {symbol}")
        else:
            params = {'positionSide': 'SHORT'}
            self.connector.exchange.create_market_sell_order(symbol, size, params=params)
            self.log(f"[LIVE] Short order placed: {size:.6f} on {symbol}")

    def get_account_balance(self):
        if self.config.get('paper_mode'):
            return self.capital
        else:
            return float(self.connector.exchange.fetch_balance()['total']['USDT'])

    def _exit_position(self, pos_type, exit_price, profit, reason=""):
        # Update capital

        symbol = self.symbol_selector.currentText()
        size = abs(exit_size)  # Get size from risk manager or stored value

        if pos_type == "long":
            self.connector.create_market_exit_order(symbol, size, side='sell')
        else:
            self.connector.create_market_exit_order(symbol, size, side='buy')
        self.capital += profit

        # Log output
        message = f"[CLOSE] {pos_type.upper()} exited at ${exit_price:.2f} | Reason: {reason}, Profit: ${profit:.2f}, Capital: ${self.capital:.2f}"
        self.log(message)
        self.send_alert(message)

        # Save to CSV
        self.save_trade_to_csv({
            'timestamp': pd.Timestamp.now(),
            'entry_price': self.entry_price,
            'exit_price': exit_price,
            'type': pos_type,
            'profit': profit,
            'reason': reason
        })

        # Reset flags
        self.in_position = False
        self.position_type = None
        self.entry_price = None

    def save_trade_to_csv(self, data):
        import csv
        file_path = self.config.get('trade_log_file', 'data/trades.csv')
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        fieldnames = ['timestamp', 'entry_price', 'exit_price', 'type', 'profit', 'reason']
        write_header = not os.path.exists(file_path)

        with open(file_path, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(data)

    def log(self, msg):
        if self.log_callback:
            self.log_callback(f"{msg}")

    def send_alert(self, msg):
        if os.getenv("TELEGRAM_BOT_TOKEN") and not self.config.get('paper_mode'):
            try:
                send_telegram_message(msg)
            except Exception as e:
                print("Telegram alert failed:", e)