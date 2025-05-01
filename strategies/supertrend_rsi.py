# strategies/supertrend_rsi.py

import numpy as np
import pandas as pd
from ta.volatility import AverageTrueRange
from ta.momentum import RSIIndicator

class SupertrendRSIStrategy:
    def generate_signal(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        # 1) Compute ATR
        df['atr'] = AverageTrueRange(
            high=df['high'], low=df['low'], close=df['close'], window=10
        ).average_true_range()

        # 2) Compute basic upper/lower bands
        hl2 = (df['high'] + df['low']) / 2
        mult = 3.0  # same as multiplier=3 in your original code
        basic_ub = hl2 + mult * df['atr']
        basic_lb = hl2 - mult * df['atr']

        # 3) Iterate to get final bands and Supertrend line
        final_ub = [basic_ub.iloc[0]]
        final_lb = [basic_lb.iloc[0]]
        supertrend = [hl2.iloc[0]]  # dummy first value

        for i in range(1, len(df)):
            bu = basic_ub.iloc[i]
            bl = basic_lb.iloc[i]
            prev_fu = final_ub[-1]
            prev_fl = final_lb[-1]
            close_prev = df['close'].iloc[i-1]

            # Final upper band
            if (bu < prev_fu) or (close_prev > prev_fu):
                fu = bu
            else:
                fu = prev_fu

            # Final lower band
            if (bl > prev_fl) or (close_prev < prev_fl):
                fl = bl
            else:
                fl = prev_fl

            final_ub.append(fu)
            final_lb.append(fl)

            # Supertrend = choose the band based on current close
            if df['close'].iloc[i] <= fu:
                supertrend.append(fu)
            else:
                supertrend.append(fl)

        df['supertrend'] = supertrend

        # 4) RSI filter
        df['rsi'] = RSIIndicator(df['close'], window=14).rsi()

        # 5) Entry signals: price above ST & RSI < 60 → long; below ST & RSI > 40 → short
        df['signal'] = 0
        df.loc[(df['close'] > df['supertrend']) & (df['rsi'] < 60), 'signal'] = 1
        df.loc[(df['close'] < df['supertrend']) & (df['rsi'] > 40), 'signal'] = -1

        # 6) Exit signals: when RSI goes beyond extreme back across your thresholds
        df['exit_signal'] = 0
        df.loc[
            (df['signal'].shift(1) == 1) & (df['rsi'] > 70),
            'exit_signal'
        ] = 1
        df.loc[
            (df['signal'].shift(1) == -1) & (df['rsi'] < 30),
            'exit_signal'
        ] = -1

        return df
