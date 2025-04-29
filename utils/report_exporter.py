import pandas as pd

class ReportExporter:
    def export_to_csv(self, trades_df, filename="data/backtest_report.csv"):
        trades_df.to_csv(filename, index=False)