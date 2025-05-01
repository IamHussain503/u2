from ta.volatility import BollingerBands
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
