import os
import time
import threading
import yaml
import pandas as pd
import ta
import ccxt

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox
from PyQt6.QtCore    import pyqtSignal

from ta.trend                    import ADXIndicator, SMAIndicator
from exchange.binance_connector  import BinanceFuturesConnector
from strategies.strategy_manager import StrategyManager
from risk.risk_manager           import RiskManager
from utils.retry                 import retry
from utils.config                import Config

# Optional Telegram alerts
try:
    from utils.helpers import send_telegram_message
except ImportError:
    def send_telegram_message(msg):
        print("[TELEGRAM DISABLED]", msg)


class Dashboard(QWidget):
    log_signal = pyqtSignal(str)

    def __init__(self, log_callback=None):
        super().__init__()
        self.log_callback = log_callback

        # Load & validate config
        cfg_path = "config.yaml"
        if not os.path.exists(cfg_path):
            raise FileNotFoundError(f"Missing config file: {cfg_path}")
        with open(cfg_path, "r") as f:
            cfg_dict = yaml.safe_load(f)
        self.cfg = Config(**cfg_dict)

        # Core settings
        self.symbol        = self.cfg.symbol
        self.timeframe     = self.cfg.timeframe
        self.limit         = self.cfg.limit
        self.poll_interval = self.cfg.poll_interval

        # Capital & risk
        self.initial_capital = self.cfg.initial_capital
        self.capital         = self.initial_capital
        self.leverage        = self.cfg.leverage
        self.risk_per_trade  = self.cfg.risk_per_trade

        # ATR / SL / TP
        self.atr_window              = self.cfg.atr_window
        self.sl_atr_mult             = self.cfg.atr_multiplier
        self.tp_atr_mult             = self.cfg.tp_multiplier
        self.trailing_atr_multiplier = self.cfg.trailing_atr_multiplier

        # Trend filter
        self.adx_window    = self.cfg.adx_window
        self.adx_threshold = self.cfg.adx_threshold
        self.ma_period     = self.cfg.ma_period

        # Time‐stop
        self.max_holding_bars = self.cfg.max_holding_bars

        # Fees & mode
        self.fee_rate       = self.cfg.taker_fee
        self.paper_mode     = self.cfg.paper_mode
        self.trade_log_file = self.cfg.trade_log_file

        # Managers & connectors
        self.connector    = BinanceFuturesConnector()
        self.risk_manager = RiskManager()
        self.strategy_mgr = StrategyManager()

        # In‐trade state
        self._reset_trade_state()

        # Build UI
        self._build_ui()

        # Hook up logging
        self.log_signal.connect(self._append_log)


    def _build_ui(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Symbol:"))
        self.sym_box = QComboBox()
        self.sym_box.addItem(self.symbol)
        layout.addWidget(self.sym_box)

        layout.addWidget(QLabel("Strategy:"))
        self.strat_box = QComboBox()
        self.strat_box.addItems(list(self.strategy_mgr.strategy_map.keys()))
        layout.addWidget(self.strat_box)

        self.run_btn = QPushButton("Run Live Bot")
        self.run_btn.clicked.connect(self.start_live)
        layout.addWidget(self.run_btn)

        self.setLayout(layout)


    def _reset_trade_state(self):
        self.in_position    = False
        self.position_type  = None
        self.entry_price    = None
        self.entry_atr      = None
        self.entry_size     = None
        self.sl_price       = None
        self.tp_price       = None
        self.highest_price  = None
        self.lowest_price   = None
        self.trailing_dist  = None
        self.entry_bar_idx  = None


    def _append_log(self, msg: str):
        if self.log_callback:
            self.log_callback(msg)
        else:
            print(msg)


    def log(self, msg: str):
        self.log_signal.emit(msg)


    @retry((ccxt.NetworkError, ccxt.ExchangeError, ConnectionError), tries=5, delay=1, backoff=2)
    def fetch_candles(self, symbol, timeframe, limit):
        return self.connector.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)

    @retry((ccxt.NetworkError, ccxt.ExchangeError, ConnectionError), tries=3, delay=1)
    def fetch_balance(self):
        return self.connector.exchange.fetch_balance()

    @retry((ccxt.NetworkError, ccxt.ExchangeError, ConnectionError), tries=3, delay=1)
    def place_buy(self, symbol, size):
        return self.connector.exchange.create_market_buy_order(symbol, size)

    @retry((ccxt.NetworkError, ccxt.ExchangeError, ConnectionError), tries=3, delay=1)
    def place_sell(self, symbol, size, params=None):
        return self.connector.exchange.create_market_sell_order(symbol, size, params or {})


    def start_live(self):
        symbol = self.sym_box.currentText()
        strat  = self.strat_box.currentText()
        self.log(f"[INFO] Starting live bot: {symbol} | Strategy={strat}")
        threading.Thread(
            target=self._live_loop,
            args=(symbol, strat),
            daemon=True
        ).start()


    def _live_loop(self, symbol, strategy_name):
        strategy = self.strategy_mgr.get_strategy(strategy_name)
        if not strategy:
            self.log(f"[ERROR] Unknown strategy: {strategy_name}")
            return

        while True:
            try:
                # Fetch candles
                df = self.fetch_candles(symbol, self.timeframe, self.limit)
                df.columns = ["timestamp","open","high","low","close","volume"]
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

                # Generate signals
                sig_df = strategy.generate_signal(df.copy())
                latest = sig_df.iloc[-1]
                signal = int(latest["signal"])
                exit_sig = int(latest.get("exit_signal", 0))
                price = float(latest["close"])

                # ATR
                sig_df["atr"] = ta.volatility.average_true_range(
                    sig_df["high"], sig_df["low"], sig_df["close"],
                    window=self.atr_window
                )
                atr = float(sig_df["atr"].dropna().iloc[-1])
                self.log(f"[DEBUG] ATR={atr:.5f}")

                # 1) derive stop‐loss distance from ATR
                stop_loss_distance = atr * self.sl_atr_mult
                self.log(f"[DEBUG] stop_loss_distance={stop_loss_distance:.5f}")

                # 2) ask RiskManager for size
                balance = self.capital if self.paper_mode \
                    else float(self.fetch_balance()["total"]["USDT"])
                size = self.risk_manager.calculate_position_size(
                    balance=balance,
                    stop_loss_distance=stop_loss_distance,
                    leverage=self.leverage,
                    risk_percent=self.risk_per_trade
                )
                self.log(f"[DEBUG] Position size = {size:.5f} contracts")

                # … then proceed with entry logic …


                # Trend filter
                adx_vals = ADXIndicator(
                    sig_df["high"], sig_df["low"], sig_df["close"],
                    window=self.adx_window
                ).adx()
                ma_vals = SMAIndicator(sig_df["close"], window=self.ma_period).sma_indicator()
                adx_val, ma_val = float(adx_vals.iloc[-1]), float(ma_vals.iloc[-1])
                self.log(f"[DEBUG] ADX={adx_val:.2f} MA{self.ma_period}={ma_val:.5f}")

                # Position sizing
                bal = self.capital if self.paper_mode else float(self.fetch_balance()["total"]["USDT"])
                stop_dist = atr * self.sl_atr_mult
                size = self.risk_manager.calculate_position_size(
                    balance=bal,
                    price=price,
                    stop_loss=stop_dist,
                    leverage=self.leverage,
                    risk_percent=self.risk_per_trade
                )
                self.log(f"[DEBUG] Sig={signal} ExitSig={exit_sig} Size={size:.5f}")

                # Trend-filtered entry
                if not self.in_position:
                    if signal == 1 and (adx_val < self.adx_threshold or price < ma_val):
                        self.log("[DEBUG] LONG filtered out by ADX/MA")
                        signal = 0
                    if signal == -1 and (adx_val < self.adx_threshold or price > ma_val):
                        self.log("[DEBUG] SHORT filtered out by ADX/MA")
                        signal = 0

                # Strategy-based exit
                if self.in_position and exit_sig != 0:
                    self.log(f"[DEBUG] Strategy exit {self.position_type.upper()} @ {price:.5f}")
                    self._exit_position(symbol, price, "Strategy Exit")
                    time.sleep(self.poll_interval)
                    continue

                # Entry logic
                if not self.in_position and signal == 1:
                    self._enter_long(symbol, price, atr, size, len(sig_df)-1)
                elif not self.in_position and signal == -1:
                    self._enter_short(symbol, price, atr, size, len(sig_df)-1)

                # Time-stop
                if self.in_position:
                    held = (len(sig_df)-1) - self.entry_bar_idx
                    if held >= self.max_holding_bars:
                        self.log(f"[TIME STOP] Held {held} bars; exiting {self.position_type}")
                        self._exit_position(symbol, price, "Time Stop")
                        time.sleep(self.poll_interval)
                        continue

                # ATR & trailing exits
                if self.in_position:
                    self._check_atr_exits(symbol, price)

                time.sleep(self.poll_interval)

            except Exception as e:
                self.log(f"[ERROR] Live loop iteration failed: {e}")
                time.sleep(self.poll_interval)


    def _enter_long(self, sym, price, atr, size, current_idx):
        if self.paper_mode:
            self.log(f"[PAPER] BUY  {sym} size={size:.5f}")
        else:
            self.place_buy(sym, size)
            self.log(f"[LIVE] BUY  {sym} size={size:.5f}")

        self.in_position    = True
        self.position_type  = "long"
        self.entry_price    = price
        self.entry_atr      = atr
        self.entry_size     = size
        self.sl_price       = price - (atr * self.sl_atr_mult)
        self.tp_price       = price + (atr * self.tp_atr_mult)
        self.highest_price  = price
        self.entry_bar_idx  = current_idx
        self.trailing_dist  = atr * self.trailing_atr_multiplier

        self.log(f"[LONG] Open @ {price:.5f} | SL={self.sl_price:.5f} TP={self.tp_price:.5f} TrailDist={self.trailing_dist:.5f}")


    def _enter_short(self, sym, price, atr, size, current_idx):
        if self.paper_mode:
            self.log(f"[PAPER] SELL {sym} size={size:.5f}")
        else:
            self.place_sell(sym, size)
            self.log(f"[LIVE] SELL {sym} size={size:.5f}")

        self.in_position    = True
        self.position_type  = "short"
        self.entry_price    = price
        self.entry_atr      = atr
        self.entry_size     = size
        self.sl_price       = price + (atr * self.sl_atr_mult)
        self.tp_price       = price - (atr * self.tp_atr_mult)
        self.lowest_price   = price
        self.entry_bar_idx  = current_idx
        self.trailing_dist  = atr * self.trailing_atr_multiplier

        self.log(f"[SHORT] Open @ {price:.5f} | SL={self.sl_price:.5f} TP={self.tp_price:.5f} TrailDist={self.trailing_dist:.5f}")


    def _check_atr_exits(self, sym, price):
        if self.position_type == "long":
            self.highest_price = max(self.highest_price, price)
            trail_stop = self.highest_price - self.trailing_dist
            self.log(f"[DEBUG] Price={price:.5f} ULT={self.sl_price:.5f} TP={self.tp_price:.5f} TRL={trail_stop:.5f}")
            if price <= self.sl_price:
                self._exit_position(sym, price, "Ultimate SL")
            elif price >= self.tp_price:
                self._exit_position(sym, price, "Take Profit")
            elif price <= trail_stop:
                self._exit_position(sym, price, "Trailing SL")
        else:
            self.lowest_price = min(self.lowest_price, price)
            trail_stop = self.lowest_price + self.trailing_dist
            self.log(f"[DEBUG] Price={price:.5f} ULT={self.sl_price:.5f} TP={self.tp_price:.5f} TRL={trail_stop:.5f}")
            if price >= self.sl_price:
                self._exit_position(sym, price, "Ultimate SL")
            elif price <= self.tp_price:
                self._exit_position(sym, price, "Take Profit")
            elif price >= trail_stop:
                self._exit_position(sym, price, "Trailing SL")


    def _exit_position(self, sym, exit_price, reason):
        size = self.entry_size
        if self.position_type == "long":
            gross = (exit_price - self.entry_price) * size
        else:
            gross = (self.entry_price - exit_price) * size
        fees = (self.entry_price + exit_price) * size * self.fee_rate
        net  = gross - fees
        self.capital += net

        if not self.paper_mode:
            if self.position_type == "long":
                self.place_sell(sym, size)
            else:
                self.place_buy(sym, size)

        msg = (f"[CLOSE] {self.position_type.upper()} @ {exit_price:.5f} "
               f"Gross={gross:.5f} Fees={fees:.5f} Net={net:.5f} "
               f"Capital={self.capital:.5f} Reason={reason}")
        self.log(msg)
        send_telegram_message(msg)

        self._save_trade({
            "timestamp":   pd.Timestamp.now(),
            "type":        self.position_type,
            "entry_price": self.entry_price,
            "exit_price":  exit_price,
            "size":        size,
            "gross":       gross,
            "fees":        fees,
            "net":         net,
            "reason":      reason
        })
        self._reset_trade_state()


    def _save_trade(self, data: dict):
        import csv
        os.makedirs(os.path.dirname(self.trade_log_file), exist_ok=True)
        write_header = not os.path.exists(self.trade_log_file)
        with open(self.trade_log_file, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(data.keys()))
            if write_header:
                writer.writeheader()
            writer.writerow(data)
