import sys
from PySide6.QtWidgets import QApplication
from MainWinodw import MainWindow
from init import clearn

if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    app.exec()
    # 删除临时目录
    clearn()
