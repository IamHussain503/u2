from ta.volatility import BollingerBands

class BollingerBreakoutStrategy:
    def generate_signal(self, df):
        df = df.copy()
        bb = BollingerBands(close=df["close"], window=20, window_dev=2)
        df["bb_upper"] = bb.bollinger_hband()
        df["bb_lower"] = bb.bollinger_lband()
        df["bb_mid"]   = bb.bollinger_mavg()

        # Entry signals
        df["signal"] = 0
        df.loc[df["close"] > df["bb_upper"], "signal"] = 1
        df.loc[df["close"] < df["bb_lower"], "signal"] = -1

        # Exit signals
        df["exit_signal"] = 0
        # if we were long and price < middle → exit long
        df.loc[
            (df["signal"].shift(1) == 1) &
            (df["close"] < df["bb_mid"]),
            "exit_signal"
        ] = 1
        # if we were short and price > middle → exit short
        df.loc[
            (df["signal"].shift(1) == -1) &
            (df["close"] > df["bb_mid"]),
            "exit_signal"
        ] = -1

        return df
