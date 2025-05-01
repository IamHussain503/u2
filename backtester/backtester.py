# backtester/backtester.py

import pandas as pd
import ta
import yaml
from risk.risk_manager import RiskManager

class Backtester:
    def __init__(self, config_path="config.yaml"):
        # load parameters
        with open(config_path, "r") as f:
            cfg = yaml.safe_load(f)

        self.initial_capital = float(cfg.get("initial_capital", 10000.0))
        self.leverage        = int(cfg.get("leverage", 1))
        self.risk_per_trade  = float(cfg.get("risk_per_trade", 0.01))

        self.atr_window      = int(cfg.get("atr_window", 14))
        self.atr_mult        = float(cfg.get("atr_multiplier", 1.5))
        self.tp_mult         = float(cfg.get("tp_multiplier", 3.0))

        self.fee_rate        = float(cfg.get("taker_fee", 0.0004))

        self.risk_manager    = RiskManager()

    def run_backtest(self, df: pd.DataFrame, strategy):
        df = df.copy()
        # ensure timestamp column
        if "timestamp" not in df.columns:
            df = df.reset_index().rename(columns={"index": "timestamp"})

        # generate entry/exit signals
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

        # helper columns for cross logic
        df["prev_sig"] = df["signal"].shift(1).fillna(0).astype(int)
        exit_sig       = df.get("exit_signal", pd.Series(0, index=df.index)).astype(int)

        for _, row in df.iterrows():
            sig    = int(row["signal"])
            prev   = int(row["prev_sig"])
            ex_sig = int(exit_sig.loc[row.name])
            price  = float(row["close"])
            atr    = float(row["atr"])
            ts     = row["timestamp"]

            # --- ENTRY LONG ---
            if not in_position and sig == 1 and prev != 1:
                in_position   = True
                direction     = "long"
                entry_price   = price
                entry_time    = ts
                entry_atr     = atr
                sl_price      = entry_price - (atr * self.tp_mult)
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
                continue

            # --- ENTRY SHORT ---
            if not in_position and sig == -1 and prev != -1:
                in_position   = True
                direction     = "short"
                entry_price   = price
                entry_time    = ts
                entry_atr     = atr
                sl_price      = entry_price + (atr * self.tp_mult)
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
                continue

            # --- MANAGE POSITION ---
            if in_position:
                reason = None

                if direction == "long":
                    highest_price = max(highest_price, price)
                    trailing_price = highest_price - (entry_atr * self.atr_mult)

                    if price <= sl_price:
                        reason = "Ultimate SL"
                    elif price >= tp_price:
                        reason = "Take Profit"
                    elif price <= trailing_price:
                        reason = "Trailing SL"
                    elif ex_sig == 1:
                        reason = "Strategy Exit"

                else:  # short
                    lowest_price = min(lowest_price, price)
                    trailing_price = lowest_price + (entry_atr * self.atr_mult)

                    if price >= sl_price:
                        reason = "Ultimate SL"
                    elif price <= tp_price:
                        reason = "Take Profit"
                    elif price >= trailing_price:
                        reason = "Trailing SL"
                    elif ex_sig == -1:
                        reason = "Strategy Exit"

                if reason:
                    # compute P&L
                    if direction == "long":
                        gross = (price - entry_price) * entry_size
                    else:
                        gross = (entry_price - price) * entry_size

                    fees = (entry_price + price) * entry_size * self.fee_rate
                    net  = gross - fees

                    capital += net

                    trades.append({
                        "entry_time":  entry_time,
                        "exit_time":   ts,
                        "direction":   direction,
                        "entry_price": round(entry_price, 5),
                        "exit_price":  round(price,       5),
                        "size":        round(entry_size,  5),
                        "gross_pnl":   round(gross,       5),
                        "fees":        round(fees,        5),
                        "net_pnl":     round(net,         5),
                        # **add a standard 'profit' column for the analyzer**
                        "profit":      round(net,         5),
                        "reason":      reason
                    })

                    # reset
                    in_position   = False
                    entry_price   = entry_time = entry_atr = None
                    entry_size    = tp_price = sl_price = None
                    highest_price = lowest_price = None
                    direction     = None

        return pd.DataFrame(trades), capital
