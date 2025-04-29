import pandas as pd
from ta import volatility

class BollingerBreakoutStrategy:
    def generate_signal(self, df):
        df = df.copy()
        indicator_bb = volatility.BollingerBands(close=df["close"], window=20, window_dev=2)
        df["bb_upper"] = indicator_bb.bollinger_hband()
        df["bb_lower"] = indicator_bb.bollinger_lband()
        df["signal"] = 0
        df.loc[df["close"] > df["bb_upper"], "signal"] = 1
        df.loc[df["close"] < df["bb_lower"], "signal"] = -1
        return df