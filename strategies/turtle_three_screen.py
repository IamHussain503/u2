# strategies/turtle_three_screen.py

import pandas as pd
from ta.volatility import DonchianChannel
from ta.trend       import CCIIndicator

class TurtleThreeScreenStrategy:
    def generate_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # 1) Donchian Channel needs high, low AND close
        dc = DonchianChannel(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            window=20
        )
        df["dc_upper"] = dc.donchian_channel_hband()
        df["dc_lower"] = dc.donchian_channel_lband()

        # 2) CCI for momentum filter
        df["cci"] = CCIIndicator(
            high=df["high"],
            low=df["low"],
            close=df["close"],
            window=20
        ).cci()

        # 3) Entry signals: breakout + extreme CCI
        df["signal"] = 0
        df.loc[
            (df["close"] > df["dc_upper"]) & (df["cci"] > 100),
            "signal"
        ] = 1
        df.loc[
            (df["close"] < df["dc_lower"]) & (df["cci"] < -100),
            "signal"
        ] = -1

        # no rule-based exits in this strat
        df["exit_signal"] = 0
        return df
