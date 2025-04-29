import pandas as pd

class Backtester:
    def run_backtest(self, df, strategy):
        df = strategy.generate_signal(df.copy())
        capital = 10000
        trades = []
        entry_price = None

        for i in range(len(df)):
            row = df.iloc[i]
            signal = row['signal']
            close_price = row['close']

            if signal == 1 and entry_price is None:
                entry_price = close_price
                entry_time = row['timestamp']
            elif signal == -1 and entry_price is not None:
                profit = close_price - entry_price
                capital += profit
                trades.append({
                    'entry_time': entry_time,
                    'exit_time': row['timestamp'],
                    'entry_price': entry_price,
                    'exit_price': close_price,
                    'profit': profit
                })
                entry_price = None

        return pd.DataFrame(trades), capital