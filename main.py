import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

# main.py

from model_trainer import start_background_training

def main():
    # 1) start background training (will also run immediately once)
    start_background_training()

    # 2) now launch your Qt GUI
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
