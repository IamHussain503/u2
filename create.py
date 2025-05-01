#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os

strategies = {
    "strategies/macd_crossover.py": """from ta.trend import MACD

class MACDCrossoverStrategy:
    def generate_signal(self, df):
        df = df.copy()
        macd = MACD(close=df["close"], window_slow=26, window_fast=12, window_sign=9)
        df["macd"]        = macd.macd()
        df["macd_signal"] = macd.macd_signal()

        # Entry
        df["signal"] = 0
        df.loc[df["macd"] > df["macd_signal"], "signal"] = 1
        df.loc[df["macd"] < df["macd_signal"], "signal"] = -1

        # Exit on cross back
        df["exit_signal"] = 0
        df.loc[
            (df["signal"].shift(1) == 1) &
            (df["macd"] < df["macd_signal"]),
            "exit_signal"
        ] = 1
        df.loc[
            (df["signal"].shift(1) == -1) &
            (df["macd"] > df["macd_signal"]),
            "exit_signal"
        ] = -1

        return df
""",
    "strategies/sma_crossover.py": """from ta.trend import SMAIndicator

class SMACrossoverStrategy:
    def generate_signal(self, df):
        df = df.copy()
        df["sma_short"] = SMAIndicator(df["close"], window=10).sma_indicator()
        df["sma_long"]  = SMAIndicator(df["close"], window=50).sma_indicator()

        # Entry
        df["signal"] = 0
        df.loc[df["sma_short"] > df["sma_long"], "signal"] = 1
        df.loc[df["sma_short"] < df["sma_long"], "signal"] = -1

        # Exit on crossover back
        df["exit_signal"] = 0
        df.loc[
            (df["signal"].shift(1) == 1) &
            (df["sma_short"] < df["sma_long"]),
            "exit_signal"
        ] = 1
        df.loc[
            (df["signal"].shift(1) == -1) &
            (df["sma_short"] > df["sma_long"]),
            "exit_signal"
        ] = -1

        return df
""",
    "strategies/rsi_macd_combo.py": """from ta.momentum import RSIIndicator
from ta.trend import MACD

class RSIMACDComboStrategy:
    def generate_signal(self, df):
        df = df.copy()
        # MACD
        macd = MACD(df["close"], window_slow=26, window_fast=12, window_sign=9)
        df["macd"]        = macd.macd()
        df["macd_signal"] = macd.macd_signal()
        # RSI
        df["rsi"] = RSIIndicator(df["close"], window=14).rsi()

        # Entry: require MACD cross plus RSI not overbought/oversold
        df["signal"] = 0
        df.loc[
            (df["macd"] > df["macd_signal"]) & (df["rsi"] < 70),
            "signal"
        ] = 1
        df.loc[
            (df["macd"] < df["macd_signal"]) & (df["rsi"] > 30),
            "signal"
        ] = -1

        # Exit: either opposite MACD cross or RSI crossing the midpoint
        df["exit_signal"] = 0
        df.loc[
            (df["signal"].shift(1) == 1) &
            ((df["macd"] < df["macd_signal"]) | (df["rsi"] > 50)),
            "exit_signal"
        ] = 1
        df.loc[
            (df["signal"].shift(1) == -1) &
            ((df["macd"] > df["macd_signal"]) | (df["rsi"] < 50)),
            "exit_signal"
        ] = -1

        return df
""",
    "strategies/donchian_breakout.py": """from ta.volatility import DonchianChannel

class DonchianBreakoutStrategy:
    def generate_signal(self, df):
        df = df.copy()
        dc = DonchianChannel(high=df["high"], low=df["low"], window=20)
        df["dc_upper"] = dc.donchian_channel_hband()
        df["dc_lower"] = dc.donchian_channel_lband()

        # Entry
        df["signal"] = 0
        df.loc[df["close"] > df["dc_upper"], "signal"] = 1
        df.loc[df["close"] < df["dc_lower"], "signal"] = -1

        # Exit on reversion into the channel
        df["exit_signal"] = 0
        df.loc[
            (df["signal"].shift(1) == 1) & (df["close"] < df["dc_upper"]),
            "exit_signal"
        ] = 1
        df.loc[
            (df["signal"].shift(1) == -1) & (df["close"] > df["dc_lower"]),
            "exit_signal"
        ] = -1

        return df
""",
    "strategies/bb_rsi_combo.py": """from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator

class BBRSIComboStrategy:
    def generate_signal(self, df):
        df = df.copy()
        bb  = BollingerBands(close=df["close"], window=20, window_dev=2)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_mid"]   = bb.bollinger_mavg()
        df["rsi"]      = RSIIndicator(df["close"], window=14).rsi()

        # Entry: break band with RSI confirmation
        df["signal"] = 0
        df.loc[
            (df["close"] > df["bb_upper"]) & (df["rsi"] < 70),
            "signal"
        ] = 1
        df.loc[
            (df["close"] < df["bb_lower"]) & (df["rsi"] > 30),
            "signal"
        ] = -1

        # Exit: reversion to mid-band or RSI cross
        df["exit_signal"] = 0
        df.loc[
            (df["signal"].shift(1) == 1) & (
                (df["close"] < df["bb_mid"]) | (df["rsi"] > 50)
            ),
            "exit_signal"
        ] = 1
        df.loc[
            (df["signal"].shift(1) == -1) & (
                (df["close"] > df["bb_mid"]) | (df["rsi"] < 50)
            ),
            "exit_signal"
        ] = -1

        return df
"""
}

def main():
    for path, content in strategies.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # Open in UTF-8 so we don't hit cp1252 errors
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    print("Created strategy files:")
    for p in strategies:
        print(" -", p)

if __name__ == "__main__":
    main()
