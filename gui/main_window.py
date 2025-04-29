from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget
from gui.dashboard import Dashboard
from gui.backtest_view import BacktestView
from gui.logs_view import LogsView
from gui.strategy_form import StrategyForm


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quantum Trader Pro")
        self.setGeometry(100, 100, 1200, 800)

        self.logs_view = LogsView()  # Initialize once for shared access

        tabs = QTabWidget()
        tabs.addTab(Dashboard(log_callback=self.logs_view.update_log), "Dashboard")
        tabs.addTab(BacktestView(), "Backtester")
        tabs.addTab(self.logs_view, "Trade Log")
        tabs.addTab(StrategyForm(), "Custom Strategy")

        self.setCentralWidget(tabs)