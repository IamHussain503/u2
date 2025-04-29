import pandas as pd
import numpy as np

class PerformanceAnalyzer:
    def analyze_trades(self, trades_df):
        total_trades = len(trades_df)
        win_rate = (trades_df['profit'] > 0).mean() * 100
        avg_profit = trades_df['profit'].mean()
        sharpe_ratio = trades_df['profit'].mean() / trades_df['profit'].std() * np.sqrt(252)
        total_return = trades_df['profit'].sum()
        max_drawdown = (trades_df['profit'].cumsum().expanding(min_periods=1).max() -
                        trades_df['profit'].cumsum()).max()
        return {
            "Total Trades": total_trades,
            "Win Rate (%)": f"{win_rate:.2f}%",
            "Avg Profit per Trade": f"${avg_profit:.2f}",
            "Sharpe Ratio": f"{sharpe_ratio:.2f}",
            "Total Return ($)": f"${total_return:.2f}",
            "Max Drawdown ($)": f"${max_drawdown:.2f}"
        }