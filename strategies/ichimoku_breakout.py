from ta.trend import IchimokuIndicator

class IchimokuBreakoutStrategy:
    def generate_signal(self, df):
        df = df.copy()
        ich = IchimokuIndicator(high=df['high'], low=df['low'], window1=9, window2=26, window3=52)
        df['conversion'] = ich.ichimoku_conversion_line()
        df['base']       = ich.ichimoku_base_line()
        
        # Entry: price above cloud and conversion > base
        df['signal'] = 0
        df.loc[(df['close'] > ich.ichimoku_a()) & (df['conversion'] > df['base']), 'signal'] = 1
        df.loc[(df['close'] < ich.ichimoku_b()) & (df['conversion'] < df['base']), 'signal'] = -1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (df['conversion'] < df['base']), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['conversion'] > df['base']), 'exit_signal'] = -1
        
        return df
