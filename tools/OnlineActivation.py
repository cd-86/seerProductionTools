import json
import socket

from PySide6.QtCore import QRegularExpression, QThread, Qt
from PySide6.QtGui import QRegularExpressionValidator
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
import requests

from init import printLog
from lib.RBKUtils import RBKUtils


class Thread(QThread):
    URL = "https://api.jiandaoyun.com/api/v5/app/entry/data/list"

    def __init__(self):
        super().__init__()
        self.ip = "192.168.192.5"

    def run(self):
        try:
            printLog(f"连接 {self.ip}:19204")
            so: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            so.connect((self.ip, 19204))
            so.settimeout(60)
            printLog("查询机器人信息")
            _, data = RBKUtils.request(so, 1000)
            robot_status_info = json.loads(data)
        except Exception as e:
            printLog("Exception:,", e)
            return
        else:
            printLog(f"关闭连接 {self.ip}:19204")
            so.close()

        # for feature in robot_status_info.get('features', []):
        #     if not isinstance(feature, dict):
        #         continue
        #     if feature.get("active", False):
        #         printLog(f"设备已激活，无需重复激活 {self.ip}")
        #         return

        echoid = robot_status_info.get('echoid', "")
        printLog(f"查询授权信息 机器码：{echoid}")
        try:
            res = requests.request(
                "post",
                Thread.URL,
                headers={
                    "Authorization": "Bearer QwGGmlzc1ltw9FQzz3nlqIul4GTr8Zui",
                    "Content-Type": "application/json"
                },
                json={
                    "rel": "and",
                    "filter": {
                        "cond": [
                            {
                                "field": "code",
                                "method": "in",
                                "type": "text",
                                "value": [echoid]
                            },
                        ],
                        "data_id": "",
                        "limit": 1
                    },
                    "fields": ["code", "expire_date", "file"],
                    "app_id": "66a0780319cf2b0711956914",
                    "entry_id": "66a1bc0351655f9db8b479b7"
                })
            data: list = res.json().get("data", [])
            if len(data) == 0:
                printLog("没有查询到授权信息")
                return
            files = data[0].get("file", [])
            if len(files) == 0:
                printLog("没有查询到授权信息")
                return
            licenseUrl = files[0].get("url")
        except Exception as e:
            printLog(e)
            return

        try:
            printLog("下载授权文件")
            res = requests.request("get", licenseUrl)
        except Exception as e:
            printLog(e)
            return

        d = res.text.encode()
        try:
            printLog(f"连接 {self.ip}:19208")
            so: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            so.connect((self.ip, 19208))
            so.settimeout(60)
            printLog("查询 Robod 版本")
            _, data = RBKUtils.request(so, 5041)

            version_info: dict = json.loads(data)
            robodVersion = int(version_info.get("version").split(".")[0])
            printLog(f"激活 {self.ip}")
            if robodVersion >= 5:
                RBKUtils.request(so, 5106, {"type": "activeRobot"}, d)
            else:
                RBKUtils.request(so, 5106, None, d)
            printLog(f"授权文件上传 {self.ip} 成功")
        except Exception as e:
            printLog("Exception:,", e)
            return
        else:
            printLog(f"关闭连接 {self.ip}:19208")
            so.close()


class OnlineActivation(QWidget):
    META = {
        "title": "在线激活"
    }

    def __init__(self):
        super().__init__()
        self.initUI()

        self.workThread = Thread()
        self.workThread.finished.connect(self.slotWorkThreadFinished)

    def initUI(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        hLayout = QHBoxLayout()
        layout.addLayout(hLayout)
        hLayout.addWidget(QLabel("IP:"))
        self.ipLineEdit = QLineEdit("192.168.192.5")
        self.ipLineEdit.setValidator(QRegularExpressionValidator(
            QRegularExpression(r"((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}"), self))
        hLayout.addWidget(self.ipLineEdit)
        self.onlineActivationButton = QPushButton("在线激活")
        hLayout.addWidget(self.onlineActivationButton)

        self.onlineActivationButton.clicked.connect(self.slotOnlineActivationButtonClicked)

    def slotOnlineActivationButtonClicked(self):
        self.onlineActivationButton.setDisabled(True)
        self.workThread.ip = self.ipLineEdit.text()
        self.workThread.start()

    def slotWorkThreadFinished(self):
        self.onlineActivationButton.setEnabled(True)
