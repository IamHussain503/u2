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
        self.leverage        = int(cfg.get("leverage", 10))
        self.risk_per_trade  = float(cfg.get("risk_per_trade", 0.01))

        self.atr_window      = int(cfg.get("atr_window", 14))
        self.atr_mult        = float(cfg.get("atr_multiplier", 1.5))
        self.tp_mult         = float(cfg.get("tp_multiplier", 3.0))

        # realistic backtest parameters
        self.fee_rate        = float(cfg.get("taker_fee", 0.0004))
        self.slippage        = float(cfg.get("slippage", 0.0005))

        self.risk_manager    = RiskManager()

    def run_backtest(self, df: pd.DataFrame, strategy):
        df = df.copy()
        # ensure timestamp column
        if "timestamp" not in df.columns:
            df = df.reset_index().rename(columns={"index": "timestamp"})

        # generate signals
        df = strategy.generate_signal(df)

        # compute ATR
        df["atr"] = ta.volatility.average_true_range(
            df["high"], df["low"], df["close"], window=self.atr_window
        )

        # initial state
        capital        = self.initial_capital
        in_position    = False
        entry_price    = entry_time = entry_atr = None
        entry_size     = None
        tp_price       = None
        sl_price       = None
        highest_price  = lowest_price = None
        direction      = None

        trades = []

        # helper for previous signal and exit_signal
        df["prev_sig"] = df["signal"].shift(1).fillna(0).astype(int)
        exit_sig       = df.get("exit_signal", pd.Series(0, index=df.index)).astype(int)

        for _, row in df.iterrows():
            sig    = int(row["signal"])
            prev   = int(row["prev_sig"])
            ex_sig = int(exit_sig.loc[row.name])
            price  = float(row["close"])
            atr    = float(row["atr"])
            h      = float(row["high"])
            l      = float(row["low"])
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

                # calculate size
                stop_dist     = atr * self.atr_mult
                entry_size    = self.risk_manager.calculate_position_size(
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

                stop_dist     = atr * self.atr_mult
                entry_size    = self.risk_manager.calculate_position_size(
                    balance=capital,
                    price=entry_price,
                    stop_loss=stop_dist,
                    leverage=self.leverage,
                    risk_percent=self.risk_per_trade
                )
                if entry_size <= 0:
                    in_position = False
                continue

            # MANAGE POSITION
            if in_position:
                reason      = None
                exit_price  = price  # default if exit later

                if direction == "long":
                    highest_price = max(highest_price, price)
                    trail_price   = highest_price - (entry_atr * self.atr_mult)

                    # check intra-bar stops/targets
                    if l <= sl_price:
                        reason     = "Ultimate SL"
                        exit_price = sl_price * (1 - self.slippage)
                    elif h >= tp_price:
                        reason     = "Take Profit"
                        exit_price = tp_price * (1 - self.slippage)
                    elif l <= trail_price:
                        reason     = "Trailing SL"
                        exit_price = trail_price * (1 - self.slippage)
                    elif ex_sig == 1:
                        reason     = "Strategy Exit"
                        exit_price = price * (1 - self.slippage)

                else:  # short
                    lowest_price = min(lowest_price, price)
                    trail_price   = lowest_price + (entry_atr * self.atr_mult)

                    if h >= sl_price:
                        reason     = "Ultimate SL"
                        exit_price = sl_price * (1 + self.slippage)
                    elif l <= tp_price:
                        reason     = "Take Profit"
                        exit_price = tp_price * (1 + self.slippage)
                    elif h >= trail_price:
                        reason     = "Trailing SL"
                        exit_price = trail_price * (1 + self.slippage)
                    elif ex_sig == -1:
                        reason     = "Strategy Exit"
                        exit_price = price * (1 + self.slippage)

                if reason:
                    # compute P&L
                    if direction == "long":
                        gross = (exit_price - entry_price) * entry_size
                    else:
                        gross = (entry_price - exit_price) * entry_size

                    fees = (entry_price + exit_price) * entry_size * self.fee_rate
                    net  = gross - fees
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

                    # reset
                    in_position   = False
                    entry_price   = entry_time = entry_atr = None
                    entry_size    = tp_price = sl_price = None
                    highest_price = lowest_price = None
                    direction     = None

        return pd.DataFrame(trades), capital

# Example usage:
# backtester = Backtester()
# trades_df, final_capital = backtester.run_backtest(df, strategy)

