import json
import math
import os
import socket

from PySide6.QtCore import QDir, QRegularExpression, Qt, QModelIndex, QThread
from PySide6.QtGui import QRegularExpressionValidator, QStandardItemModel, QStandardItem, QPainter, QPen, QColor, \
    QPainterPath, QBrush, QRadialGradient, QConicalGradient
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QListView, QSizePolicy

from init import cfg, printLog
from lib.RBKUtils import RBKUtils


class Thread(QThread):
    upgradeStatusDict = {
        "0": "设备正在接收升级文件…",
        "1": "接收完成，正在解压文件…",
        "2": "解压完成，正在分析文件…",
        "3": "更新 IMU…",
        "4": "更新 firmware…",
        "5": "更新 主程序…",
        "6": "更新 守护程序…",
        "7": "增量更新主程序资源文件…",
        "8": "增量更新主程序…",
        "9": "更新 辅助程序…"
    }

    reductionStatusDict = {
        "0": "设备正在接收升级文件…",
        "1": "接收完成，正在解压文件…",
        "2": "解压完成，正在分析文件…",
        "3": "恢复 IMU…",
        "4": "恢复 firmware…",
        "5": "恢复 主程序…",
        "6": "恢复 守护程序…",
        "7": "增量恢复主程序资源文件…",
        "8": "增量恢复主程序…",
        "9": "恢复 辅助程序…"
    }

    def __init__(self):
        super().__init__()
        self.ip = "192.168.192.5"
        self.filePath = ""

        self.updateState = 0 # 0: 1:成功 2:失败

    def run(self):
        self.updateState = 0
        if not os.path.exists(self.filePath):
            printLog(f"文件不存在 {self.filePath}")
            return

        with open(self.filePath, "rb") as f:
            data = f.read()

        try:
            printLog(f"连接 {self.ip}:19208")
            so: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            so.connect((self.ip, 19208))
            # so.settimeout(60)
            printLog(f"上传升级包 {self.filePath} {self.ip}")
            RBKUtils.request(so, 5104, data)
            req = RBKUtils.pack(5104, data)
            so.sendall(req)
            printLog(f"升级包上传成功 {self.ip}")

            recvData = b''
            while True:
                while True:
                    # 接收报文头
                    l = 16 - len(recvData)
                    if l > 0:
                        recvData += so.recv(l)
                    # 解析报文头
                    print(recvData)
                    try:
                        header = RBKUtils.unpack(recvData)
                    except:
                        recvData = recvData[1:]
                        continue
                    if header[0] == 90 and header[1] == 1:
                        recvData = recvData[16:]
                        break
                    recvData = recvData[1:]
                # 获取报文体长度
                bodyLen = header[3]
                readSize = 1024
                while (bodyLen > 0):
                    recv = so.recv(readSize)
                    recvData += recv
                    bodyLen -= len(recv)
                    if bodyLen < readSize:
                        readSize = bodyLen
                if header[4] == 15125:
                    try:
                        js = json.loads(recvData[:header[3]])
                    except:
                        printLog(str(recvData[:header[3]]))
                    else:
                        reductionStatus = js.get("reductionStatus", "")
                        upgradeStatus = js.get("upgradeStatus", "")
                        if upgradeStatus:
                            printLog(Thread.upgradeStatusDict.get(upgradeStatus, upgradeStatus).rstrip())
                        elif reductionStatus:
                            printLog(Thread.reductionStatusDict.get(reductionStatus, reductionStatus).rstrip())
                elif header[4] == 15104:
                    if header[3] == 0:
                        printLog(f"升级完成 {self.ip}")
                        printLog(f"关闭连接 {self.ip}:19208")
                        so.close()
                        self.updateState = 1
                        break
                    try:
                        js = json.loads(recvData[:header[3]])
                    except:
                        printLog(str(recvData[:header[3]]))
                    else:
                        printLog(js)
                else:
                    printLog(header[4], str(recvData[:header[3]]))
                recvData = recvData[header[3]:]
        except Exception as e:
            printLog("Exception:,", e)
            self.updateState = 2
            return


class Progress(QWidget):
    def __init__(self):
        super().__init__()

        self.setMinimumSize(10, 10)

        self.updateState = 0

        self.timeID = -1
        self.startAngle = 0
        self.angleSpan = 0
        self.step = 10

    def start(self):
        if self.timeID != -1:
            self.killTimer(self.timeID)
        self.timeID = self.startTimer(33)

    def stop(self):
        if self.timeID == -1:
            return
        self.killTimer(self.timeID)
        self.timeID = -1
        self.update()

    def timerEvent(self, event):
        self.startAngle += 10
        self.startAngle %= 360

        self.angleSpan += self.step
        if -20 <= self.angleSpan < 0:
            self.startAngle = (self.startAngle + self.angleSpan) % 360
            self.angleSpan = -self.angleSpan
            self.step = 15
        if self.angleSpan >= 320:
            self.startAngle = (self.startAngle + self.angleSpan) % 360
            self.angleSpan = -self.angleSpan
            self.step = 10
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.timeID == -1:
            if self.updateState == 1:
                path = QPainterPath()
                path.moveTo(self.width() * 0.1, self.height() * 0.5)
                path.lineTo(self.width() * 0.4, self.height() * 0.8)
                path.lineTo(self.width() * 0.9, self.height() * 0.2)
                painter.setPen(QPen(QColor(25, 200, 25, 255), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                    Qt.PenJoinStyle.RoundJoin))
                painter.drawPath(path)
            elif self.updateState == 2:
                painter.setPen(QPen(QColor(200, 25, 25, 255), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                                    Qt.PenJoinStyle.RoundJoin))
                painter.drawLine(self.width() * 0.2, self.height() * 0.2, self.width() * 0.8, self.height() * 0.8)
                painter.drawLine(self.width() * 0.2, self.height() * 0.8, self.width() * 0.8, self.height() * 0.2)
            return

        painter.setPen(QPen(QColor(25, 25, 200, 255), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                            Qt.PenJoinStyle.RoundJoin))

        painter.drawArc(2, 2, self.width() - 4, self.height() - 4, -self.startAngle * 16, -self.angleSpan * 16)


class UpgradeRBK(QWidget):
    META = {
        "title": "升级 RBK",
        "config": {
            "rbk_package_directory": {
                "name": "RBK 整包目录",
                "desc": "存放 RBK 升级包的目录",
                "value": QDir.current().absolutePath() + "/RBKPackage",
                "type": "dir"
            }
        }
    }

    def __init__(self):
        super().__init__()

        self.workThread = Thread()
        self.model = QStandardItemModel()
        self.initUI()

        self.workThread.finished.connect(self.slotWorkThreadFinished)

    def initUI(self):
        layout = QVBoxLayout(self)

        hLayout = QHBoxLayout()
        layout.addLayout(hLayout)
        hLayout.addWidget(QLabel("IP:"))
        self.ipLineEdit = QLineEdit("192.168.192.5")
        self.ipLineEdit.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}"), self))
        hLayout.addWidget(self.ipLineEdit)
        self.progress = Progress()
        hLayout.addWidget(self.progress)
        self.refreshButton = QPushButton("刷新文件列表")
        hLayout.addWidget(self.refreshButton)
        self.startUpgradeButton = QPushButton("开始升级")
        hLayout.addWidget(self.startUpgradeButton)
        self.refreshButton.adjustSize()
        self.progress.setFixedSize(self.refreshButton.height(), self.refreshButton.height())

        self.filesListView = QListView()
        self.filesListView.setModel(self.model)
        layout.addWidget(self.filesListView)

        self.refreshButton.clicked.connect(self.slotRefreshButtonClicked)
        self.startUpgradeButton.clicked.connect(self.slotStartUpgradeButtonClicked)
        self.refreshButton.click()

    def slotRefreshButtonClicked(self):
        self.model.clear()
        rbkDir = cfg[self.__class__.__name__, "rbk_package_directory"]
        if not rbkDir:
            rbkDir = UpgradeRBK.META["config"]["rbk_package_directory"]["value"]

        if (not os.path.exists(rbkDir)):
            os.makedirs(rbkDir)
        for f in os.listdir(rbkDir):
            path = os.path.join(rbkDir, f)
            if os.path.isfile(path) and path[-4:] == ".zip":
                item = QStandardItem(os.path.basename(f))
                item.setData(path, Qt.ItemDataRole.UserRole)
                self.model.appendRow(item)
        self.filesListView.setCurrentIndex(self.model.index(0, 0))

    def slotStartUpgradeButtonClicked(self):
        filePath = self.filesListView.currentIndex().data(Qt.ItemDataRole.UserRole)
        if not filePath:
            printLog("没有选择升级包")
            return
        self.startUpgradeButton.setDisabled(True)
        self.progress.start()
        self.workThread.ip = self.ipLineEdit.text()
        self.workThread.filePath = filePath
        self.workThread.start()

    def slotWorkThreadFinished(self):
        self.startUpgradeButton.setEnabled(True)
        self.progress.updateState = self.workThread.updateState
        self.progress.stop()
