from ta.trend import SMAIndicator

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
