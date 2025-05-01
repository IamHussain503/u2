from ta.volatility import DonchianChannel

class TurtleThreeScreenStrategy:
    def generate_signal(self, df):
        df = df.copy()
        dc20 = DonchianChannel(high=df['high'], low=df['low'], window=20)
        dc55 = DonchianChannel(high=df['high'], low=df['low'], window=55)
        df['breakout20'] = df['close'] > dc20.donchian_channel_hband()
        df['trend55'] = df['close'] > dc55.donchian_channel_hband()
        
        df['signal'] = 0
        df.loc[(df['breakout20']) & (df['trend55']), 'signal'] = 1
        df.loc[(~df['breakout20']) & (~df['trend55']), 'signal'] = -1
        
        df['exit_signal'] = 0
        df.loc[(df['signal'].shift(1) == 1) & (~df['trend55']), 'exit_signal'] = 1
        df.loc[(df['signal'].shift(1) == -1) & (df['trend55']), 'exit_signal'] = -1
        
        return df
