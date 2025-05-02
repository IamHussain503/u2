# backtester/backtester.py

import os
import pandas as pd
import ta
import yaml
from risk.risk_manager import RiskManager

class Backtester:
    def __init__(self, config_path="config.yaml"):
        # load parameters
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        self.initial_capital = float(cfg.get("initial_capital", 1000.0))
        self.leverage        = int(cfg.get("leverage", 50))
        print(f"Using leverage: {self.leverage}x")
        self.risk_per_trade  = float(cfg.get("risk_per_trade", 1.0))
        print(f"Risk per trade: {self.risk_per_trade * 100:.1f}%")

        self.atr_window            = int(cfg.get("atr_window", 14))
        self.atr_mult              = float(cfg.get("atr_multiplier", 1.5))
        self.tp_mult               = float(cfg.get("tp_multiplier", 3.0))
        self.trailing_atr_mult     = float(cfg.get("trailing_atr_multiplier", self.atr_mult))

        # realistic backtest parameters
        self.fee_rate        = float(cfg.get("taker_fee", 0.0004))
        self.slippage        = float(cfg.get("slippage", 0.0005))

        self.risk_manager    = RiskManager()

    def run_backtest(self, df: pd.DataFrame, strategy):
        # 1) Prepare data
        df = df.copy()
        if "timestamp" not in df.columns:
            df = df.reset_index().rename(columns={"index": "timestamp"})

        # 2) Generate signals and ATR
        df = strategy.generate_signal(df)
        df["atr"] = ta.volatility.average_true_range(
            df["high"], df["low"], df["close"], window=self.atr_window
        )

        # 3) Initialize state
        capital        = self.initial_capital
        in_position    = False
        entry_price    = entry_time = entry_atr = None
        entry_size     = tp_price = sl_price = None
        highest_price  = lowest_price = None
        direction      = None
        trades         = []

        # 4) Prepare helper columns
        df["prev_sig"] = df["signal"].shift(1).fillna(0).astype(int)
        exit_sig       = df.get("exit_signal", pd.Series(0, index=df.index)).astype(int)

        # 5) Loop over bars
        for _, row in df.iterrows():
            sig    = int(row["signal"])
            prev   = int(row["prev_sig"])
            ex_sig = int(exit_sig.loc[row.name])
            price  = float(row["close"])
            atr    = float(row["atr"])
            h, l   = float(row["high"]), float(row["low"])
            ts     = row["timestamp"]

            # ENTRY LONG
            if not in_position and sig == 1 and prev != 1:
                in_position   = True
                direction     = "long"
                entry_price   = price * (1 + self.slippage)
                entry_time    = ts
                entry_atr     = atr
                sl_price      = entry_price - (atr * self.atr_mult)
                tp_price      = entry_price + (atr * self.tp_mult)
                highest_price = entry_price

                stop_dist  = atr * self.atr_mult
                entry_size = self.risk_manager.calculate_position_size(
                    balance=capital,
                    price=entry_price,
                    stop_loss=stop_dist,
                    leverage=self.leverage,
                    risk_percent=self.risk_per_trade
                )
                if entry_size <= 0:
                    in_position = False
                continue

            # ENTRY SHORT
            if not in_position and sig == -1 and prev != -1:
                in_position   = True
                direction     = "short"
                entry_price   = price * (1 - self.slippage)
                entry_time    = ts
                entry_atr     = atr
                sl_price      = entry_price + (atr * self.atr_mult)
                tp_price      = entry_price - (atr * self.tp_mult)
                lowest_price  = entry_price

                stop_dist  = atr * self.atr_mult
                entry_size = self.risk_manager.calculate_position_size(
                    balance=capital,
                    price=entry_price,
                    stop_loss=stop_dist,
                    leverage=self.leverage,
                    risk_percent=self.risk_per_trade
                )
                if entry_size <= 0:
                    in_position = False
                continue

            # MANAGE POSITION & EXIT
            if in_position:
                reason     = None
                exit_price = price

                if direction == "long":
                    highest_price = max(highest_price, price)
                    # dynamic trailing multiplier based on profit
                    profit_atr = (price - entry_price) / entry_atr if entry_atr else 0
                    if profit_atr > 2:
                        trail_mult = self.trailing_atr_mult * 0.5
                    elif profit_atr > 1:
                        trail_mult = self.trailing_atr_mult * 0.75
                    else:
                        trail_mult = self.trailing_atr_mult
                    trail_price = highest_price - (entry_atr * trail_mult)

                    # 1) trailing stop
                    if l <= trail_price:
                        reason     = "Trailing SL"
                        exit_price = trail_price * (1 - self.slippage)
                    # 2) static stop
                    elif l <= sl_price:
                        reason     = "Ultimate SL"
                        exit_price = sl_price * (1 - self.slippage)
                    # 3) take profit
                    elif h >= tp_price:
                        reason     = "Take Profit"
                        exit_price = tp_price * (1 - self.slippage)
                    # 4) strategy exit
                    elif ex_sig == 1:
                        reason     = "Strategy Exit"
                        exit_price = price * (1 - self.slippage)

                else:  # short
                    lowest_price = min(lowest_price, price)
                    # dynamic trailing multiplier based on profit
                    profit_atr = (entry_price - price) / entry_atr if entry_atr else 0
                    if profit_atr > 2:
                        trail_mult = self.trailing_atr_mult * 0.5
                    elif profit_atr > 1:
                        trail_mult = self.trailing_atr_mult * 0.75
                    else:
                        trail_mult = self.trailing_atr_mult
                    trail_price = lowest_price + (entry_atr * trail_mult)

                    # 1) trailing stop
                    if h >= trail_price:
                        reason     = "Trailing SL"
                        exit_price = trail_price * (1 + self.slippage)
                    # 2) static stop
                    elif h >= sl_price:
                        reason     = "Ultimate SL"
                        exit_price = sl_price * (1 + self.slippage)
                    # 3) take profit
                    elif l <= tp_price:
                        reason     = "Take Profit"
                        exit_price = tp_price * (1 + self.slippage)
                    # 4) strategy exit
                    elif ex_sig == -1:
                        reason     = "Strategy Exit"
                        exit_price = price * (1 + self.slippage)

                if reason:
                    # compute P&L
                    if direction == "long":
                        gross = (exit_price - entry_price) * entry_size
                    else:
                        gross = (entry_price - exit_price) * entry_size

                    fees   = (entry_price + exit_price) * entry_size * self.fee_rate
                    net    = gross - fees
                    capital += net

                    trades.append({
                        "entry_time":  entry_time,
                        "exit_time":   ts,
                        "direction":   direction,
                        "entry_price": round(entry_price, 5),
                        "exit_price":  round(exit_price, 5),
                        "size":        round(entry_size, 5),
                        "gross_pnl":   round(gross, 5),
                        "fees":        round(fees, 5),
                        "net_pnl":     round(net, 5),
                        "profit":      round(net, 5),
                        "reason":      reason
                    })

                    # reset position state
                    in_position   = False
                    entry_price   = entry_time = entry_atr = None
                    entry_size    = tp_price = sl_price = None
                    highest_price = lowest_price = None
                    direction     = None

        # 6) Build DataFrame & convert times to UTC+5
        trades_df = pd.DataFrame(trades)
        if not trades_df.empty and "entry_time" in trades_df.columns:
            trades_df["entry_time"] = (
                pd.to_datetime(trades_df["entry_time"])
                  .dt.tz_localize("UTC")
                  .dt.tz_convert("Asia/Karachi")
            )
            trades_df["exit_time"] = (
                pd.to_datetime(trades_df["exit_time"])
                  .dt.tz_localize("UTC")
                  .dt.tz_convert("Asia/Karachi")
            )

        return trades_df, capital
