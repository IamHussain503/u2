from ta.trend import MACD

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
