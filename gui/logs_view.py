from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit


class LogsView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    def update_log(self, message):
        self.log_output.append(message)