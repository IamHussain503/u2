
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton

class StrategyForm(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Custom Strategy Name"))
        self.name_input = QLineEdit()
        layout.addWidget(self.name_input)
        layout.addWidget(QLabel("Condition (e.g., ema_short > ema_long)"))
        self.condition_input = QLineEdit()
        layout.addWidget(self.condition_input)
        self.save_button = QPushButton("Save Strategy")
        layout.addWidget(self.save_button)
        self.setLayout(layout)
