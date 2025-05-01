from ta.volume import VolumeWeightedAveragePrice

class VWAPReversionStrategy:
    def generate_signal(self, df):
        df = df.copy()
        vwap = VolumeWeightedAveragePrice(df['high'], df['low'], df['close'], df['volume'], window=14)
        df['vwap'] = vwap.volume_weighted_average_price()
        df['deviation'] = (df['close'] - df['vwap']).abs()
        
        # Entry: price deviates > 1 ATR from VWAP
        df['atr'] = df['deviation'].rolling(14).mean()
        df['signal'] = 0
        df.loc[df['close'] > df['vwap'] + df['atr'], 'signal'] = -1
        df.loc[df['close'] < df['vwap'] - df['atr'], 'signal'] = 1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['close'] >= df['vwap']), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['close'] <= df['vwap']), 'exit_signal'] = -1
        
        return df
