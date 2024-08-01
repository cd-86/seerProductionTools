from PySide6.QtWidgets import QVBoxLayout, QPlainTextEdit, QWidget
from init import __obj__


class LogView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("日志")
        #
        layout = QVBoxLayout(self)
        self.setLayout(layout)
        self.plainTextEdit = QPlainTextEdit()
        layout.addWidget(self.plainTextEdit)
        __obj__.sigPrintLog.connect(lambda args: self.plainTextEdit.appendPlainText(str(args)))

