import pandas as pd
from ta import momentum

class RSIDivergenceStrategy:
    def generate_signal(self, df):
        df = df.copy()
        df['rsi'] = momentum.rsi(df['close'], window=14)
        df['signal'] = 0
        df.loc[df['rsi'] > 70, 'signal'] = -1
        df.loc[df['rsi'] < 30, 'signal'] = 1
        return df