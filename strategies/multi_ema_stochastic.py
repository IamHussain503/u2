from ta.trend import EMAIndicator
from ta.momentum import StochasticOscillator

class MultiEMAStochasticStrategy:
    def generate_signal(self, df):
        df = df.copy()
        # EMA Trend
        df['ema_short'] = EMAIndicator(df['close'], window=20).ema_indicator()
        df['ema_long']  = EMAIndicator(df['close'], window=50).ema_indicator()
        # Stochastic Oscillator
        stoch = StochasticOscillator(df['high'], df['low'], df['close'], window=14, smooth_window=3)
        df['stoch'] = stoch.stoch()
        
        # Entry: EMAs bullish and Stoch oversold
        df['signal'] = 0
        df.loc[(df['ema_short'] > df['ema_long']) & (df['stoch'] < 20), 'signal'] = 1
        df.loc[(df['ema_short'] < df['ema_long']) & (df['stoch'] > 80), 'signal'] = -1
        
        # Exit: EMA cross or Stoch mid-cross
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['stoch'] > 50), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['stoch'] < 50), 'exit_signal'] = -1
        
        return df
