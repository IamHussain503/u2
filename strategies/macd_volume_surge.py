from ta.trend import MACD
from ta.volume import VolumeWeightedAveragePrice

class MACDVolumeSurgeStrategy:
    def generate_signal(self, df):
        df = df.copy()
        macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
        df['macd_hist'] = macd.macd_diff()
        df['vwap'] = VolumeWeightedAveragePrice(df['high'], df['low'], df['close'], df['volume'], window=20).volume_weighted_average_price()
        
        df['signal'] = 0
        df.loc[(df['macd_hist'] > 0) & (df['volume'] > df['volume'].rolling(20).mean()*2), 'signal'] = 1
        df.loc[(df['macd_hist'] < 0) & (df['volume'] > df['volume'].rolling(20).mean()*2), 'signal'] = -1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['macd_hist'] < 0), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['macd_hist'] > 0), 'exit_signal'] = -1
        
        return df
