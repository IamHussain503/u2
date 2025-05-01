from ta.volatility import BollingerBands
from ta.trend import ADXIndicator

class ADXBollingerSqueezeStrategy:
    def generate_signal(self, df):
        df = df.copy()
        bb = BollingerBands(df['close'], window=20, window_dev=2)
        df['bandwidth'] = (bb.bollinger_hband() - bb.bollinger_lband()) / bb.bollinger_mavg()
        df['adx'] = ADXIndicator(df['high'], df['low'], df['close'], window=14).adx()
        
        df['signal'] = 0
        df.loc[(df['bandwidth'] < 0.05) & (df['adx'] > 25), 'signal'] = 1
        df.loc[(df['bandwidth'] < 0.05) & (df['adx'] > 25), 'signal'] = -1  # adapt for short if needed
        
        df['exit_signal'] = 0
        df.loc[df['adx'] < 20, 'exit_signal'] = df['signal'].shift(1)
        
        return df
