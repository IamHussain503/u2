import pandas as pd
from ta import trend

class EMACrossoverStrategy:
    def generate_signal(self, df):
        df = df.copy()
        df['ema_short'] = trend.ema_indicator(df['close'], window=9)
        df['ema_long'] = trend.ema_indicator(df['close'], window=21)
        df['signal'] = 0
        df.loc[df['ema_short'] > df['ema_long'], 'signal'] = 1
        df.loc[df['ema_short'] < df['ema_long'], 'signal'] = -1
        return df