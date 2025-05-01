from ta.trend import ema_indicator

class EMACrossoverStrategy:
    def generate_signal(self, df):
        df = df.copy()
        df['ema_short'] = ema_indicator(df['close'], window=9)
        df['ema_long']  = ema_indicator(df['close'], window=21)

        # Entry
        df['signal'] = 0
        df.loc[df['ema_short'] > df['ema_long'], 'signal'] = 1
        df.loc[df['ema_short'] < df['ema_long'], 'signal'] = -1

        # Exit
        df['exit_signal'] = 0
        # previously long but now short → close long
        df.loc[
            (df['signal'].shift(1) == 1) &
            (df['ema_short'] < df['ema_long']),
            'exit_signal'
        ] = 1
        # previously short but now long → close short
        df.loc[
            (df['signal'].shift(1) == -1) &
            (df['ema_short'] > df['ema_long']),
            'exit_signal'
        ] = -1

        return df
