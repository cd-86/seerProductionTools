from PySide6.QtCore import Slot
from PySide6.QtGui import Qt
from PySide6.QtWidgets import QMainWindow, QTabWidget, QDockWidget, QListWidget, QListWidgetItem

import tools
from LogView import LogView
from SettingDialog import SettingDialog
from init import printLog, VERSION


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f'生产工具 - v{VERSION}')
        self.resize(640, 480)
        self.initUI()

    def initUI(self):
        # menu
        menu = self.menuBar().addMenu("文件")
        menu.addAction("设置", lambda: SettingDialog().exec())
        # 中间是主要工作窗口
        self.tabWidget = QTabWidget(self)
        self.tabWidget.setMovable(True)
        self.tabWidget.setTabsClosable(True)
        self.setCentralWidget(self.tabWidget)
        # 底部日志窗口
        self.logView = LogView(self)
        dockWidget = QDockWidget()
        dockWidget.setWidget(self.logView)
        dockWidget.setWindowTitle(self.logView.windowTitle())
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dockWidget)
        # 右侧列表
        self.listWidget = QListWidget(self)
        dockWidget = QDockWidget()
        dockWidget.setWidget(self.listWidget)
        dockWidget.setWindowTitle("工具")
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dockWidget)

        printLog("加载工具列表")
        i = 1
        for c in dir(tools):
            if not c.startswith("__"):
                cls = getattr(tools, c)
                item = QListWidgetItem(cls.META["title"])
                item.cls = cls
                self.listWidget.addItem(item)
                printLog(f"{i}. {cls.META['title']}")
                i += 1
        printLog("结束加载工具列表")

        # 信号槽
        self.listWidget.itemDoubleClicked.connect(self.listWidgetItemDoubleClicked)
        self.tabWidget.tabCloseRequested.connect(self.tabWidgetTabCloseRequested)

    @Slot(QListWidgetItem)
    def listWidgetItemDoubleClicked(self, item: QListWidgetItem):
        w = item.cls()
        self.tabWidget.addTab(w, w.META["title"])
        printLog(f"增加一个 Tab【{w.META['title']}】 位置 {self.tabWidget.count()}")

    @Slot(int)
    def tabWidgetTabCloseRequested(self, index):
        printLog(f"删除一个 Tab【{self.tabWidget.tabText(index)}】 位置 {index + 1}")
        self.tabWidget.removeTab(index)
