# Requires pivot point calculation library or custom implementation
import pandas as pd

def calculate_pivots(df):
    # Basic pivot point calculation
    df['pp'] = (df['high'] + df['low'] + df['close']) / 3
    df['r1'] = 2 * df['pp'] - df['low']
    df['s1'] = 2 * df['pp'] - df['high']
    return df

class PivotPointBreakoutStrategy:
    def generate_signal(self, df):
        df = calculate_pivots(df.copy())
        df['signal'] = 0
        df.loc[df['close'] > df['r1'], 'signal'] = 1
        df.loc[df['close'] < df['s1'], 'signal'] = -1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['close'] < df['pp']), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['close'] > df['pp']), 'exit_signal'] = -1
        
        return df
