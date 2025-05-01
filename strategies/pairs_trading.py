import pandas as pd

class PairsTradingStrategy:
    def generate_signal(self, df):
        df = df.copy()
        # TODO: implement cointegration test & z-score of spread
        df['signal'] = 0
        df['exit_signal'] = 0
        return df
