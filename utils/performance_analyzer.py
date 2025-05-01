# utils/performance_analyzer.py

import pandas as pd
import numpy as np

class PerformanceAnalyzer:
    def analyze_trades(self, trades_df: pd.DataFrame) -> dict:
        # extract profit series
        profits      = trades_df['profit'] if 'profit' in trades_df else trades_df.get('net_pnl', pd.Series(dtype=float))
        total_trades = len(profits)

        # basic stats
        win_rate    = (profits > 0).sum() / total_trades * 100 if total_trades > 0 else 0.0
        avg_profit  = profits.mean()    if total_trades > 0 else 0.0
        total_return= profits.sum()
        # cumulative PnL and drawdown
        cum_pnl     = profits.cumsum()
        max_dd      = (cum_pnl.expanding(min_periods=1).max() - cum_pnl).max()

        # safe Sharpe
        if total_trades < 2 or profits.std() == 0:
            sharpe = float('nan')
        else:
            sharpe = profits.mean() / profits.std() * np.sqrt(252)

        return {
            "Total Trades":         total_trades,
            "Win Rate (%)":         f"{win_rate:.2f}%",
            "Avg Profit per Trade": f"${avg_profit:.2f}",
            "Sharpe Ratio":         ("nan" if np.isnan(sharpe) else f"{sharpe:.2f}"),
            "Total Return ($)":     f"${total_return:.2f}",
            "Max Drawdown ($)":     f"${max_dd:.2f}"
        }
