import os
import time
import threading
import yaml
import pandas as pd
import ta
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox
from ta.trend import ADXIndicator, SMAIndicator
from exchange.binance_connector import BinanceFuturesConnector
from strategies.strategy_manager import StrategyManager
from risk.risk_manager import RiskManager

# Optional Telegram alerts
try:
    from utils.helpers import send_telegram_message
except ImportError:
    def send_telegram_message(msg):
        print("[TELEGRAM DISABLED]", msg)


class Dashboard(QWidget):
    def __init__(self, log_callback=None):
        super().__init__()
        self.log_callback = log_callback

        # Load configuration
        cfg_path = "config.yaml"
        if not os.path.exists(cfg_path):
            raise FileNotFoundError(f"Missing config file: {cfg_path}")
        with open(cfg_path, "r") as f:
            self.cfg = yaml.safe_load(f)

        # Core settings
        self.symbol           = self.cfg["symbol"]
        self.timeframe        = self.cfg["timeframe"]
        self.limit            = int(self.cfg.get("limit", 100))
        self.poll_interval    = int(self.cfg.get("poll_interval", 60))

        # Capital & risk
        self.initial_capital  = float(self.cfg.get("initial_capital", 1000))
        self.capital          = self.initial_capital
        self.leverage         = int(self.cfg.get("leverage", 1))
        self.risk_per_trade   = float(self.cfg.get("risk_per_trade", 0.01))

        # ATR / SL / TP settings
        self.atr_window              = int(self.cfg.get("atr_window", 14))
        self.sl_atr_mult             = float(self.cfg.get("atr_multiplier", 1.5))
        self.tp_atr_mult             = float(self.cfg.get("tp_multiplier", 3.0))
        self.trailing_atr_multiplier = float(self.cfg.get("trailing_atr_multiplier", 1.5))

        # Trend filter settings
        self.adx_window     = int(self.cfg.get("adx_window", 14))
        self.adx_threshold  = float(self.cfg.get("adx_threshold", 25))
        self.ma_period      = int(self.cfg.get("ma_period", 200))

        # Time-stop
        self.max_holding_bars = int(self.cfg.get("max_holding_bars", 48))

        # Fees
        self.fee_rate       = float(self.cfg.get("taker_fee", 0.0004))

        # Mode & logging
        self.paper_mode     = bool(self.cfg.get("paper_mode", True))
        self.trade_log_file = self.cfg.get("trade_log_file", "data/trades.csv")

        # Managers and connectors
        self.connector      = BinanceFuturesConnector()
        self.risk_manager   = RiskManager()
        self.strategy_mgr   = StrategyManager()

        # In‐trade state
        self.in_position    = False
        self.position_type  = None
        self.entry_price    = None
        self.entry_atr      = None
        self.entry_size     = None
        self.sl_price       = None
        self.tp_price       = None
        self.highest_price  = None
        self.lowest_price   = None
        self.entry_bar_idx  = None

        # Build UI
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

    def start_live(self):
        symbol = self.sym_box.currentText()
        strategy_name = self.strat_box.currentText()
        self.log(f"[INFO] Starting live bot: {symbol} | Strategy={strategy_name}")
        threading.Thread(
            target=self._live_loop,
            args=(symbol, strategy_name),
            daemon=True
        ).start()

    def _live_loop(self, symbol, strategy_name):
        try:
            strategy = self.strategy_mgr.get_strategy(strategy_name)
            if not strategy:
                raise ValueError(f"Unknown strategy '{strategy_name}'")

            while True:
                # 1) Fetch OHLCV
                df = self.connector.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=self.timeframe,
                    limit=self.limit
                )
                df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")

                # 2) Signals
                sig_df = strategy.generate_signal(df.copy())
                latest = sig_df.iloc[-1]
                signal = int(latest["signal"])
                exit_sig = int(latest.get("exit_signal", 0))
                price = float(latest["close"])

                # 3) ATR
                sig_df["atr"] = ta.volatility.average_true_range(
                    sig_df["high"], sig_df["low"], sig_df["close"],
                    window=self.atr_window
                )
                atr = float(sig_df["atr"].dropna().iloc[-1])
                self.log(f"[DEBUG] ATR={atr:.5f}")

                # 4) Trend filter: ADX + MA200
                adx_vals = ADXIndicator(
                    sig_df["high"], sig_df["low"], sig_df["close"],
                    window=self.adx_window
                ).adx()
                ma_vals = SMAIndicator(sig_df["close"], window=self.ma_period).sma_indicator()
                adx_val = float(adx_vals.iloc[-1])
                ma_val = float(ma_vals.iloc[-1])
                self.log(f"[DEBUG] ADX={adx_val:.2f} MA{self.ma_period}={ma_val:.5f}")

                # 5) Position sizing
                balance = self.capital if self.paper_mode else \
                          float(self.connector.exchange.fetch_balance()["total"]["USDT"])
                stop_dist = atr * self.sl_atr_mult
                size = self.risk_manager.calculate_position_size(
                    balance=balance,
                    price=price,
                    stop_loss=stop_dist,
                    leverage=self.leverage,
                    risk_percent=self.risk_per_trade
                )
                self.log(f"[DEBUG] Signal={signal} ExitSig={exit_sig} Size={size:.5f}")

                # 6) Trend‐filtered entry
                if not self.in_position:
                    if signal == 1 and (adx_val < self.adx_threshold or price < ma_val):
                        self.log("[DEBUG] LONG filtered out by ADX/MA")
                        signal = 0
                    if signal == -1 and (adx_val < self.adx_threshold or price > ma_val):
                        self.log("[DEBUG] SHORT filtered out by ADX/MA")
                        signal = 0

                # 7) Strategy‐based exit
                if self.in_position and exit_sig != 0:
                    reason = "Strategy Exit"
                    self.log(f"[DEBUG] Strategy exit {self.position_type.upper()} @ {price:.5f}")
                    self._exit_position(symbol, price, reason)
                    time.sleep(self.poll_interval)
                    continue

                # 8) Entry logic
                if not self.in_position and signal == 1:
                    self._enter_long(symbol, price, atr, size, len(sig_df)-1)
                elif not self.in_position and signal == -1:
                    self._enter_short(symbol, price, atr, size, len(sig_df)-1)

                # 9) Time-stop exit
                if self.in_position:
                    bars_held = (len(sig_df)-1) - self.entry_bar_idx
                    if bars_held >= self.max_holding_bars:
                        self.log(f"[TIME STOP] Held {bars_held} bars; exiting {self.position_type}")
                        self._exit_position(symbol, price, "Time Stop")
                        time.sleep(self.poll_interval)
                        continue

                # 10) ATR & trailing stop exits
                if self.in_position:
                    self._check_atr_exits(symbol, price)

                time.sleep(self.poll_interval)

        except Exception as e:
            self.log(f"[ERROR] Live loop failed: {e}")

    def _enter_long(self, sym, price, atr, size, current_idx):
        if self.paper_mode:
            self.log(f"[PAPER] BUY  {sym} size={size:.5f}")
        else:
            self.connector.exchange.create_market_buy_order(sym, size)
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
        # trailing threshold from config
        self.trailing_dist  = atr * self.trailing_atr_multiplier

        self.log(
            f"[LONG] Open @ {price:.5f} | "
            f"SL={self.sl_price:.5f} TP={self.tp_price:.5f} "
            f"TrailDist={self.trailing_dist:.5f}"
        )

    def _enter_short(self, sym, price, atr, size, current_idx):
        if self.paper_mode:
            self.log(f"[PAPER] SELL {sym} size={size:.5f}")
        else:
            self.connector.exchange.create_market_sell_order(sym, size)
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

        self.log(
            f"[SHORT] Open @ {price:.5f} | "
            f"SL={self.sl_price:.5f} TP={self.tp_price:.5f} "
            f"TrailDist={self.trailing_dist:.5f}"
        )

    def _check_atr_exits(self, sym, price):
        if self.position_type == "long":
            self.highest_price = max(self.highest_price, price)
            trail_stop = self.highest_price - self.trailing_dist
            self.log(
                f"[DEBUG] Price={price:.5f} ULT={self.sl_price:.5f} "
                f"TP={self.tp_price:.5f} TRL={trail_stop:.5f}"
            )
            if price <= self.sl_price:
                self._exit_position(sym, price, "Ultimate SL")
            elif price >= self.tp_price:
                self._exit_position(sym, price, "Take Profit")
            elif price <= trail_stop:
                self._exit_position(sym, price, "Trailing SL")
        else:  # short
            self.lowest_price = min(self.lowest_price, price)
            trail_stop = self.lowest_price + self.trailing_dist
            self.log(
                f"[DEBUG] Price={price:.5f} ULT={self.sl_price:.5f} "
                f"TP={self.tp_price:.5f} TRL={trail_stop:.5f}"
            )
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
        net = gross - fees
        self.capital += net

        if not self.paper_mode:
            if self.position_type == "long":
                self.connector.exchange.create_market_sell_order(sym, size)
            else:
                self.connector.exchange.create_market_buy_order(sym, size)

        self.log(
            f"[CLOSE] {self.position_type.upper()} @ {exit_price:.5f} "
            f"Gross={gross:.5f} Fees={fees:.5f} Net={net:.5f} "
            f"Capital={self.capital:.5f} Reason={reason}"
        )
        self.send_alert(
            f"[CLOSE] {self.position_type.upper()} @ {exit_price:.5f} "
            f"Net={net:.5f} Reason={reason}"
        )
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

        # Reset
        self.in_position    = False
        self.position_type  = None
        self.entry_price    = None
        self.entry_atr      = None
        self.entry_size     = None
        self.sl_price       = None
        self.tp_price       = None
        self.highest_price  = None
        self.lowest_price   = None
        self.entry_bar_idx  = None

    def _save_trade(self, data):
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
