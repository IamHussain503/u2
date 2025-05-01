import os
import time
import threading
import yaml
import pandas as pd
import ta
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox
from exchange.binance_connector import BinanceFuturesConnector
from strategies.strategy_manager import StrategyManager
from risk.risk_manager import RiskManager

# Optional alerting
try:
    from utils.helpers import send_telegram_message
except ImportError:
    def send_telegram_message(msg):
        print("[TELEGRAM DISABLED]", msg)


class Dashboard(QWidget):
    def __init__(self, log_callback=None):
        super().__init__()
        self.log_callback = log_callback

        # connectors & managers
        self.connector = BinanceFuturesConnector()
        self.risk_manager = RiskManager()

        # load config
        cfg_path = "config.yaml"
        if not os.path.exists(cfg_path):
            raise FileNotFoundError(f"Missing config file: {cfg_path}")
        with open(cfg_path, "r") as f:
            self.config = yaml.safe_load(f)

        # basic settings
        self.symbol         = self.config["symbol"]
        self.timeframe      = self.config["timeframe"]
        self.limit          = int(self.config.get("limit", 100))
        self.poll_interval  = int(self.config.get("poll_interval", 60))
        self.initial_capital= float(self.config.get("initial_capital", 10000))
        self.capital        = self.initial_capital
        self.paper_mode     = bool(self.config.get("paper_mode", True))
        self.trade_log_file = self.config.get("trade_log_file", "data/trades.csv")

        # risk settings
        self.leverage       = int(self.config.get("leverage", 1))
        self.risk_per_trade = float(self.config.get("risk_per_trade", 0.01))

        # ATR & TP/SL settings
        self.atr_window     = int(self.config.get("atr_window", 14))
        self.atr_mult       = float(self.config.get("atr_multiplier", 1.5))
        self.tp_mult        = float(self.config.get("tp_multiplier", 3.0))

        # fee settings
        self.fee_rate       = float(self.config.get("taker_fee", 0.0004))

        # in-trade state
        self.in_position    = False
        self.position_type  = None
        self.entry_price    = None
        self.position_size  = None
        self.initial_atr    = None
        self.tp_price       = None
        self.ult_sl_price   = None
        self.highest_price  = None
        self.lowest_price   = None

        # build UI
        layout = QVBoxLayout()
        self.symbol_input = QComboBox()
        self.symbol_input.addItem(self.symbol)
        self.strategy_selector = QComboBox()
        self.strategy_selector.addItems(list(StrategyManager().strategy_map.keys()))
        self.run_button = QPushButton("Run Live Bot")
        self.run_button.clicked.connect(self.start_live_trading)

        layout.addWidget(QLabel("Select Symbol:"))
        layout.addWidget(self.symbol_input)
        layout.addWidget(QLabel("Select Strategy:"))
        layout.addWidget(self.strategy_selector)
        layout.addWidget(self.run_button)
        self.setLayout(layout)

    def start_live_trading(self):
        symbol = self.symbol_input.currentText()
        strategy_name = self.strategy_selector.currentText()
        self.log(f"[INFO] Starting bot for {symbol} using '{strategy_name}' strategy...")
        threading.Thread(
            target=self._live_trading_loop,
            args=(symbol, strategy_name),
            daemon=True
        ).start()

    def _live_trading_loop(self, symbol, strategy_name):
        try:
            strategy = StrategyManager().get_strategy(strategy_name)
            if not strategy:
                raise ValueError(f"Strategy '{strategy_name}' could not be loaded.")

            while True:
                # fetch latest candles
                df = self.connector.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=self.timeframe,
                    limit=self.limit
                )
                signal_df = strategy.generate_signal(df.copy())
                latest     = signal_df.iloc[-1]

                # basic signals
                signal      = int(latest.get("signal", 0))
                exit_signal = int(latest.get("exit_signal", 0))
                close_price = float(latest["close"])

                # compute ATR
                signal_df["atr"] = ta.volatility.average_true_range(
                    signal_df["high"],
                    signal_df["low"],
                    signal_df["close"],
                    window=self.atr_window
                )
                atr_value = float(signal_df["atr"].dropna().iloc[-1])

                # calculate position size
                balance            = self.get_account_balance()
                stop_loss_distance = atr_value * self.atr_mult
                self.position_size = self.risk_manager.calculate_position_size(
                    balance=balance,
                    price=close_price,
                    stop_loss=stop_loss_distance,
                    leverage=self.leverage,
                    risk_percent=self.risk_per_trade
                )

                self.log(f"[DEBUG] Signal={signal}, ExitSignal={exit_signal}")

                # 1) strategy-based exit
                if self.in_position and exit_signal != 0:
                    reason = "Strategy Exit"
                    if exit_signal == 1 and self.position_type == "long":
                        self.log(f"[DEBUG] Strategy exit LONG @ {close_price:.5f}")
                        self._exit_position("long", close_price, reason)
                    elif exit_signal == -1 and self.position_type == "short":
                        self.log(f"[DEBUG] Strategy exit SHORT @ {close_price:.5f}")
                        self._exit_position("short", close_price, reason)
                    time.sleep(self.poll_interval)
                    continue

                # 2) new entry
                if not self.in_position and signal == 1:
                    self.place_long_order(symbol, self.position_size)
                    self.entry_price = close_price
                    # lock in SL/TP
                    self.initial_atr   = atr_value
                    self.tp_price      = self.entry_price + (atr_value * self.tp_mult)
                    self.ult_sl_price  = self.entry_price - (atr_value * self.tp_mult)
                    self.highest_price = self.entry_price
                    self.position_type = "long"
                    self.in_position   = True
                    self.log(f"[LONG] Opened @ {self.entry_price:.5f} | Size={self.position_size:.5f}")

                elif not self.in_position and signal == -1:
                    self.place_short_order(symbol, self.position_size)
                    self.entry_price = close_price
                    # lock in SL/TP
                    self.initial_atr   = atr_value
                    self.tp_price      = self.entry_price - (atr_value * self.tp_mult)
                    self.ult_sl_price  = self.entry_price + (atr_value * self.tp_mult)
                    self.lowest_price  = self.entry_price
                    self.position_type = "short"
                    self.in_position   = True
                    self.log(f"[SHORT] Opened @ {self.entry_price:.5f} | Size={self.position_size:.5f}")

                # 3) ATR + trailing exits
                if self.in_position:
                    if self.position_type == "long":
                        # update trailing
                        self.highest_price = max(self.highest_price, close_price)
                        trailing_price = self.highest_price - (self.initial_atr * self.atr_mult)
                        self.log(
                            f"[DEBUG] Price={close_price:.5f} "
                            f"ULT_SL={self.ult_sl_price:.5f} "
                            f"TP={self.tp_price:.5f} "
                            f"TR_SL={trailing_price:.5f}"
                        )
                        if close_price <= self.ult_sl_price:
                            self._exit_position("long", close_price, "Ultimate SL")
                        elif close_price >= self.tp_price:
                            self._exit_position("long", close_price, "Take Profit")
                        elif close_price <= trailing_price:
                            self._exit_position("long", close_price, "Trailing SL")

                    else:  # short
                        self.lowest_price = min(self.lowest_price, close_price)
                        trailing_price = self.lowest_price + (self.initial_atr * self.atr_mult)
                        self.log(
                            f"[DEBUG] Price={close_price:.5f} "
                            f"ULT_SL={self.ult_sl_price:.5f} "
                            f"TP={self.tp_price:.5f} "
                            f"TR_SL={trailing_price:.5f}"
                        )
                        if close_price >= self.ult_sl_price:
                            self._exit_position("short", close_price, "Ultimate SL")
                        elif close_price <= self.tp_price:
                            self._exit_position("short", close_price, "Take Profit")
                        elif close_price >= trailing_price:
                            self._exit_position("short", close_price, "Trailing SL")

                time.sleep(self.poll_interval)

        except Exception as e:
            self.log(f"[ERROR] Live trading loop failed: {e}")

    def place_long_order(self, symbol, size):
        if self.paper_mode:
            self.log(f"[PAPER] LONG @{symbol}, size {size:.5f}")
        else:
            self.connector.exchange.create_market_buy_order(symbol, size)
            self.log(f"[LIVE] LONG @{symbol}, size {size:.5f}")

    def place_short_order(self, symbol, size):
        if self.paper_mode:
            self.log(f"[PAPER] SHORT @{symbol}, size {size:.5f}")
        else:
            self.connector.exchange.create_market_sell_order(symbol, size)
            self.log(f"[LIVE] SHORT @{symbol}, size {size:.5f}")

    def get_account_balance(self):
        if self.paper_mode:
            return self.capital
        bal = self.connector.exchange.fetch_balance()["total"]["USDT"]
        return float(bal)

    def _exit_position(self, pos_type, exit_price, reason=""):
        size = self.position_size
        # gross P&L
        if pos_type == "long":
            gross = (exit_price - self.entry_price) * size
        else:
            gross = (self.entry_price - exit_price) * size
        # fees
        fees = (self.entry_price + exit_price) * size * self.fee_rate
        net  = gross - fees

        # execute the close
        if not self.paper_mode:
            sym = self.symbol_input.currentText()
            if pos_type == "long":
                self.connector.exchange.create_market_sell_order(sym, size)
            else:
                self.connector.exchange.create_market_buy_order(sym, size)

        # update capital
        self.capital += net

        # log & alert
        self.log(
            f"[CLOSE] {pos_type.upper()} @ {exit_price:.5f} | "
            f"Gross={gross:.5f} Fees={fees:.5f} Net={net:.5f} "
            f"Capital={self.capital:.5f} Reason={reason}"
        )
        self.send_alert(
            f"[CLOSE] {pos_type.upper()} @ {exit_price:.5f} | Net={net:.5f} Reason={reason}"
        )

        # record
        self.save_trade_to_csv({
            "timestamp":    pd.Timestamp.now(),
            "entry_price":  self.entry_price,
            "exit_price":   exit_price,
            "type":         pos_type,
            "profit":       net,
            "reason":       reason
        })

        # reset
        self.in_position   = False
        self.position_type = None
        self.entry_price   = None
        self.position_size = None
        self.initial_atr   = None
        self.tp_price      = None
        self.ult_sl_price  = None
        self.highest_price = None
        self.lowest_price  = None

    def save_trade_to_csv(self, data):
        import csv
        os.makedirs(os.path.dirname(self.trade_log_file), exist_ok=True)
        write_header = not os.path.exists(self.trade_log_file)
        with open(self.trade_log_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(data.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(data)

    def log(self, msg):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)

    def send_alert(self, msg):
        if os.getenv("TELEGRAM_BOT_TOKEN") and not self.paper_mode:
            try:
                send_telegram_message(msg)
            except Exception as e:
                print("Telegram alert failed:", e)
