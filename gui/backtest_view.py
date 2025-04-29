# gui/backtest_view.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QComboBox
from exchange.binance_connector import BinanceFuturesConnector
from strategies.strategy_manager import StrategyManager
from backtester.backtester import Backtester
from utils.performance_analyzer import PerformanceAnalyzer
import threading

class BacktestView(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout()
        self.select_label = QLabel("Select Strategy:")
        self.strategy_selector = QComboBox()
        self.strategy_selector.addItems(["EMA Crossover", "RSI Divergence", "Bollinger Breakout"])
        self.backtest_button = QPushButton("Run Strategy Backtest")
        self.output = QTextEdit()
        self.output.setReadOnly(True)

        self.layout.addWidget(self.select_label)
        self.layout.addWidget(self.strategy_selector)
        self.layout.addWidget(self.backtest_button)
        self.layout.addWidget(self.output)
        self.setLayout(self.layout)

        # Event binding
        self.backtest_button.clicked.connect(self.run_backtest)

    def run_backtest(self):
        strategy_name = self.strategy_selector.currentText()
        self.output.append(f"[INFO] Running backtest for: {strategy_name}\n")

        # Run in thread to avoid freezing UI
        threading.Thread(target=self._run_in_thread, args=(strategy_name,), daemon=True).start()

    def _run_in_thread(self, strategy_name):
        try:
            connector = BinanceFuturesConnector()
            df = connector.fetch_ohlcv(symbol="BTC/USDT", timeframe="1h", limit=200)
            strategy_manager = StrategyManager()
            strategy = strategy_manager.get_strategy(strategy_name)

            if not strategy:
                raise ValueError(f"Strategy '{strategy_name}' not found.")

            backtester = Backtester()
            trades_df, capital = backtester.run_backtest(df, strategy)

            if len(trades_df) == 0:
                self.output.append("[INFO] No trades generated during backtest.")
                return

            analyzer = PerformanceAnalyzer()
            analysis = analyzer.analyze_trades(trades_df)

            # Display result
            self.output.append(f"\n[RESULT] Final Capital: ${capital:.2f}")
            for key, value in analysis.items():
                self.output.append(f"{key}: {value}")

        except Exception as e:
            self.output.append(f"[ERROR] {e}")