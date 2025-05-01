from ta.momentum import rsi

class RSIDivergenceStrategy:
    def generate_signal(self, df):
        df = df.copy()
        df['rsi'] = rsi(df['close'], window=14)

        # Entry
        df['signal'] = 0
        df.loc[df['rsi'] < 30, 'signal'] = 1
        df.loc[df['rsi'] > 70, 'signal'] = -1

        # Exit
        df['exit_signal'] = 0
        # previously long and now RSI > 50 → exit long
        df.loc[
            (df['signal'].shift(1) == 1) &
            (df['rsi'] > 50),
            'exit_signal'
        ] = 1
        # previously short and now RSI < 50 → exit short
        df.loc[
            (df['signal'].shift(1) == -1) &
            (df['rsi'] < 50),
            'exit_signal'
        ] = -1

        return df
