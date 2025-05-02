# gui/backtest_view.py

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QComboBox
from exchange.binance_connector import BinanceFuturesConnector
from strategies.strategy_manager import StrategyManager
from utils.report_exporter import ReportExporter
from backtester.backtester import Backtester
from utils.performance_analyzer import PerformanceAnalyzer
import threading
import pandas as pd

class BacktestView(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.select_label      = QLabel("Select Strategy:")
        self.strategy_selector = QComboBox()
# in Dashboard.__init__ after creating self.strategy_selector:
        self.strategy_selector.addItems([
            "EMA Crossover",
            "RSI Divergence",
            "Bollinger Breakout",
            "MACD Crossover",
            "SMA Crossover",
            "RSI+MACD Combo",
            "Donchian Breakout",
            "BB+RSI Combo",
            "MultiEMA Stochastic",
            "VWAP Reversion",
            "Ichimoku Breakout",
            "Supertrend RSI",
            "MACD Volume Surge",
            "Keltner CCI Mean Reversion",
            "Turtle Three Screen",
            "Pivot Point Breakout",
            "ADX Bollinger Squeeze",
            "RSI MA Envelope",
            "Machine Learning Signal",
            "Pairs Trading"
        ])

        self.backtest_button   = QPushButton("Run Strategy Backtest")
        self.output            = QTextEdit()
        self.output.setReadOnly(True)

        self.layout.addWidget(self.select_label)
        self.layout.addWidget(self.strategy_selector)
        self.layout.addWidget(self.backtest_button)
        self.layout.addWidget(self.output)
        self.setLayout(self.layout)

        self.backtest_button.clicked.connect(self.run_backtest)

    def run_backtest(self):
        self.backtest_button.setEnabled(False)
        strat = self.strategy_selector.currentText()
        self.output.append(f"[INFO] Running backtest for: {strat}\n")
        threading.Thread(target=self._worker, args=(strat,), daemon=True).start()

    def _worker(self, strategy_name):
        try:
            # 1) fetch data (spot or futures as you prefer)
            conn = BinanceFuturesConnector()
            df   = conn.fetch_ohlcv(symbol="TAO/USDT", timeframe="4h", limit=100)
            df.columns = ["timestamp","open","high","low","close","volume"]  # ensure names

            # 2) pick strategy
            strat = StrategyManager().get_strategy(strategy_name)
            if not strat:
                raise ValueError(f"Strategy '{strategy_name}' not found.")

            # 3) backtest
            backtester = Backtester()
            trades_df, final_cap = backtester.run_backtest(df, strat)
            ReportExporter().export_to_csv(trades_df, filename="data/backtest_trades.csv")


            # 4) display
            if trades_df.empty:
                self.output.append("[INFO] No trades generated during backtest.\n")
            else:
                # show final capital to 5 decimal places
                self.output.append(f"[RESULT] Final Capital: ${final_cap:.5f}\n")

                # performance summary
                analyzer = PerformanceAnalyzer()
                stats = analyzer.analyze_trades(trades_df)
                # print each stat on its own line
                for k, v in stats.items():
                    self.output.append(f"{k}: {v}")
                self.output.append("")  # blank line

        except Exception as e:
            self.output.append(f"[ERROR] {e}\n")
        finally:
            self.backtest_button.setEnabled(True)
