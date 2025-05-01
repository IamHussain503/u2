from ta.volatility import DonchianChannel

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
