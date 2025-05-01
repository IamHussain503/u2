from ta.momentum import RSIIndicator
from ta.trend import SMAIndicator

class RSIMovingAverageEnvelopeStrategy:
    def generate_signal(self, df):
        df = df.copy()
        df['sma'] = SMAIndicator(df['close'], window=20).sma_indicator()
        df['upper_env'] = df['sma'] * 1.05
        df['lower_env'] = df['sma'] * 0.95
        df['rsi'] = RSIIndicator(df['close'], window=14).rsi()
        
        df['signal'] = 0
        df.loc[(df['close'] > df['upper_env']) & (df['rsi'] < 50), 'signal'] = -1
        df.loc[(df['close'] < df['lower_env']) & (df['rsi'] > 50), 'signal'] = 1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['close'] >= df['sma']), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['close'] <= df['sma']), 'exit_signal'] = -1
        
        return df
