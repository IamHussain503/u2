from ta.momentum import RSIIndicator
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
