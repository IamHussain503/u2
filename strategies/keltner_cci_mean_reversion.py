# strategies/keltner_cci_mean_reversion.py

from ta.volatility import KeltnerChannel
from ta.trend import CCIIndicator

class KeltnerCCIMeanReversionStrategy:
    def generate_signal(self, df):
        df = df.copy()
        # Keltner Channel
        kc = KeltnerChannel(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=20,
            window_atr=10
        )
        df['kc_lower'] = kc.keltner_channel_lband()
        df['kc_upper'] = kc.keltner_channel_hband()

        # CCI
        df['cci'] = CCIIndicator(
            high=df['high'],
            low=df['low'],
            close=df['close'],
            window=20
        ).cci()

        # Entry: price outside channel and CCI extreme
        df['signal'] = 0
        df.loc[(df['close'] < df['kc_lower']) & (df['cci'] < -100), 'signal'] = 1
        df.loc[(df['close'] > df['kc_upper']) & (df['cci'] > 100),  'signal'] = -1

        # Exit: CCI mean‐reversion
        df['exit_signal'] = 0
        df.loc[
            (df['signal'].shift(1) == 1) & (df['cci'] > 0),
            'exit_signal'
        ] = 1
        df.loc[
            (df['signal'].shift(1) == -1) & (df['cci'] < 0),
            'exit_signal'
        ] = -1

        return df
