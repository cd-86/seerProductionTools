import json
import socket
from datetime import datetime

from PySide6.QtCore import QDir, QMargins, Qt, QPoint, Slot, QThread, QFile, QFileInfo, QRegularExpression
from PySide6.QtGui import QPainter, QPixmap, QPen, QImage, QColor, QIntValidator, QRegularExpressionValidator
from PySide6.QtMultimedia import QMediaDevices, QMediaCaptureSession, QCamera, QImageCapture
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QGroupBox, QFileDialog, \
    QDialog, QGridLayout, QFrame, QSizePolicy, QScrollArea, QStyleOption, QStyleOptionViewItem, QStyle

from init import printLog, cfg, tempDir
from lib.RBKUtils import RBKUtils


class PictureViewer(QWidget):
    """
    预览图片的控件
    """

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pixmap: QPixmap = None
        self.prePos = QPoint(0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_StyleSheet, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def setPixmap(self, pixmap: QPixmap):
        self.pixmap = pixmap
        self.scale = 1
        self.translate = QPoint(0, 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.save()
        if self.pixmap is not None and self.pixmap.width() != 0 and self.pixmap.height() != 0:
            rect = self.rect() - QMargins(0, 0, 1, 1)
            painter.translate(rect.center())
            painter.translate(self.translate)
            v = min(rect.width() / self.pixmap.width(), rect.height() / self.pixmap.height())
            painter.scale(v, v)
            painter.scale(self.scale, self.scale)
            painter.translate(-self.pixmap.width() / 2, -self.pixmap.height() / 2)
            painter.drawPixmap(self.pixmap.rect(), self.pixmap)
            painter.restore()
        opt = QStyleOption()
        opt.initFrom(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self);

    def wheelEvent(self, event):
        if self.pixmap is not None:
            self.scale *= 1.1 if event.angleDelta().x() + event.angleDelta().y() > 0 else 0.9
            self.update()

    def mousePressEvent(self, event):
        if self.pixmap is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.prePos = event.pos()

    def mouseMoveEvent(self, event):
        if self.pixmap is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.translate += QPoint(event.pos() - self.prePos)
            self.prePos = event.pos()
            self.update()


class CameraViewer(QDialog):
    """
    拍照的对话框
    """

    def __init__(self):
        super().__init__()
        self.initUI()
        self.img: QImage = None
        self.isFinished = False

    def initUI(self):
        self.setWindowTitle("相机")
        self.resize(640, 480)
        layout = QVBoxLayout(self)
        self.captureSession = QMediaCaptureSession()
        dev = None
        for d in QMediaDevices.videoInputs():
            if d.description() == cfg["ExportRobotInfo", "camera"]:
                dev = d
                break
        self.camera = QCamera(dev)
        self.captureSession.setCamera(self.camera)
        self.viewfinder = QVideoWidget()
        self.captureSession.setVideoOutput(self.viewfinder)

        self.imageCapture = QImageCapture(self.camera)
        self.captureSession.setImageCapture(self.imageCapture)
        self.camera.start()
        layout.addWidget(self.viewfinder)
        self.shootButton = QPushButton("拍摄")
        self.finishButton = QPushButton("完成")
        hBoxLayout = QHBoxLayout()
        hBoxLayout.addWidget(self.shootButton)
        hBoxLayout.addWidget(self.finishButton)
        layout.addLayout(hBoxLayout)

        self.shootButton.clicked.connect(self.shoot)
        self.finishButton.clicked.connect(self.finishButtonClicked)
        self.imageCapture.imageCaptured.connect(self.slotImageCaptured)
        self.imageCapture.errorChanged.connect(self.imageCaptureErrorChanged)

    @Slot(int, QImage)
    def slotImageCaptured(self, id: int, img: QImage):
        self.shootButton.setText("重新拍摄")
        self.camera.stop()
        self.img = img

    @Slot()
    def imageCaptureErrorChanged(self):
        printLog(self.imageCapture.errorString())

    @Slot()
    def shoot(self):
        if self.camera.isActive():
            self.imageCapture.capture()
        else:
            self.shootButton.setText("拍摄")
            self.camera.start()

    def finishButtonClicked(self):
        self.isFinished = True
        self.close()


class PictureWidgetPrivate(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.__picturePath__ = ""

    def initUI(self):
        layout = QVBoxLayout(self)
        self.pictureViewer = PictureViewer()
        layout.addWidget(self.pictureViewer)
        hBoxLayout = QHBoxLayout()
        self.localButton = QPushButton("选择本地图片")
        self.shootButton = QPushButton("拍摄一张图片")
        hBoxLayout.addWidget(self.localButton)
        hBoxLayout.addWidget(self.shootButton)
        layout.addLayout(hBoxLayout)

        self.localButton.clicked.connect(self.localButtonClicked)
        self.shootButton.clicked.connect(self.shootButtonClicked)

        self.setStyleSheet("""
        PictureViewer {
            border: 2px solid rgb(0, 0, 0);
        }
        """)

    @property
    def picturePath(self):
        return self.__picturePath__

    @picturePath.setter
    def picturePath(self, value):
        self.__picturePath__ = value
        self.pictureViewer.setPixmap(QPixmap(self.__picturePath__))
        self.pictureViewer.update()

    def localButtonClicked(self):
        f = QFileDialog.getOpenFileName(self, "选择一个图片", "", "image (*.png *.jpg *.jpeg *.bmp)")
        if f[0]:
            self.picturePath = f[0]

    def shootButtonClicked(self):
        cv = CameraViewer()
        cv.exec()
        if not cv.isFinished:
            return
        filePath = tempDir.filePath(datetime.now().strftime("IMG_%Y%m%d%H%M%S.png"))
        if not cv.img.save(filePath):
            printLog("保存图片失败！")
            return
        self.picturePath = filePath


class Thread(QThread):
    def __init__(self):
        super().__init__()
        self.ip = "192.168.192.5"
        self.robotID = ""
        self.robot_status_info = {}
        self.robot_status_run_info = {}
        self.robot_status_battery_info = {}
        self.robot_status_alarm_info = {}

        self.robot_core_status_info = {}
        self.robot_core_robod_version_info = {}

        self.widgetPixmap: QPixmap = None

    def run(self):
        try:
            printLog(f"连接 {self.ip}:19204")
            so: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            so.connect((self.ip, 19204))
            so.settimeout(60)
            printLog("查询机器人信息")
            data = RBKUtils.request(so, 1000)
            self.robot_status_info = json.loads(data)
            printLog("查询机器人运行信息")
            data = RBKUtils.request(so, 1002)
            self.robot_status_run_info = json.loads(data)
            printLog("查询机器人电池信息")
            data = RBKUtils.request(so, 1007)
            self.robot_status_battery_info = json.loads(data)
            printLog("查询机器人报警信息")
            data = RBKUtils.request(so, 1050)
            self.robot_status_alarm_info = json.loads(data)
        except Exception as e:
            printLog("Exception:,", e)
        else:
            printLog(f"关闭连接 {self.ip}:19204")
            so.close()
        try:
            printLog(f"连接 {self.ip}:19208")
            so: socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            so.connect((self.ip, 19208))
            so.settimeout(60)
            printLog("查询查询 Robokit 运行状态")
            data = RBKUtils.request(so, 5011)
            self.robot_core_status_info = json.loads(data)
            printLog("查询 Robod 版本")
            data = RBKUtils.request(so, 5041)
            self.robot_core_robod_version_info = json.loads(data)
        except Exception as e:
            printLog("Exception:,", e)
        else:
            printLog(f"关闭连接 {self.ip}:19208")
            so.close()
        self.robotID = self.robot_status_info.get('id', "")
        printLog(f"生成机器人信息图片 {self.robotID}")
        self.offScreenRenderingWidget()
        printLog(f"完成 {self.robotID}")

    def ms2dateStr(self, ms):
        s = ms // 1000
        d = s // (24 * 3600)
        h = s // 3600 % 24
        m = s // 60 % 60
        s = ms // 1000 % 60
        return f"{d}天/{h:0>2d}时/{m:0>2d}分/{s:0>2d}"

    def offScreenRenderingWidget(self):
        """
        离屏渲染
        """

        def newLine(shape: QFrame.Shape) -> QLabel:
            label = QLabel()
            label.setFrameStyle(shape | QFrame.Shadow.Plain)
            label.setLineWidth(1)
            return label

        def alignLabel(txt: str) -> QLabel:
            label = QLabel(txt)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return label

        w = QWidget()
        layout = QVBoxLayout(w)
        hLayout = QHBoxLayout(w)
        layout.addLayout(hLayout)
        # 运行状态
        statusGroup = QGroupBox("机器人运行状态")
        gridLayout = QGridLayout(statusGroup)
        gridLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row = 0
        gridLayout.addWidget(QLabel("累计里程"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_run_info.get('odo', 0) / 1000} km"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("今日累计里程"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_run_info.get('today_odo', 0)} m"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("累计运行时间"), row, 0)
        gridLayout.addWidget(QLabel(self.ms2dateStr(self.robot_status_run_info.get('total_time', 0))), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("本次运行时间"), row, 0)
        gridLayout.addWidget(QLabel(self.ms2dateStr(self.robot_status_run_info.get('time', 0))), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("控制器电压"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_run_info.get('controller_voltage', 0):.2f} V"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("控制器温度"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_run_info.get('controller_temp', 0):.2f} ℃"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("控制器湿度"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_run_info.get('controller_humi', 0):.2f} %"), row, 1)
        # 电池信息
        row += 1
        gridLayout.addWidget(QLabel("电池电量"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_battery_info.get('battery_level', 0) * 100:.2f} %"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("电池温度"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_battery_info.get('battery_temp', 0):.2f} ℃"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("电池电压"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_battery_info.get('voltage', 0):.2f} V"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("电池电流"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_battery_info.get('current', 0):.2f} A"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("电池循环次数"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_battery_info.get('battery_cycle', 0)}"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("电池数据(自定义)"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_battery_info.get('battery_user_data', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("手动充电:"), row, 0)
        gridLayout.addWidget(
            QLabel("手动充电" if self.robot_status_battery_info.get('manual_charge', False) else "未充电"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("最大充电电压"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_battery_info.get('max_charge_voltage', 0):.2f} V"), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("最大充电电流"), row, 0)
        gridLayout.addWidget(QLabel(f"{self.robot_status_battery_info.get('max_charge_current', 0):.2f} A"), row, 1)
        hLayout.addWidget(statusGroup)
        # 机器人基本信息
        statusGroup = QGroupBox("机器人基本信息")
        gridLayout = QGridLayout(statusGroup)
        gridLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row = 0
        gridLayout.addWidget(QLabel("机器人ID"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('id', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("机器人名称"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('vehicle_id', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("机器人备注"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('robot_note', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("机器人型号"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('model', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("Robokit版本"), row, 0)
        gridLayout.addWidget(
            QLabel(f"{self.robot_status_info.get('version', '')}({self.robot_status_info.get('architecture', '')})"),
            row, 1)
        row += 1
        gridLayout.addWidget(QLabel("底层固件版本"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('dsp_version', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("陀螺仪版本"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('gyro_version', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("TCP API 版本"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('netprotocol_version', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("Modbus 版本"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('modbus_version', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("地图版本"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('map_version', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("模型版本"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('model_version', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("MAC"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('MAC', "")), row, 1)
        row += 1
        gridLayout.addWidget(QLabel("无线网 MAC"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('WLANMAC', "")), row, 1)
        hLayout.addWidget(statusGroup)
        # 网卡信息单独放一个group
        statusGroup = QGroupBox("网卡信息")
        gridLayout = QGridLayout(statusGroup)
        gridLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row = 0
        gridLayout.addWidget(newLine(QFrame.Shape.HLine), row, 0, 1, 2)
        row += 1
        for nwc in self.robot_status_info.get('network_controllers', []):
            if not isinstance(nwc, dict):
                continue
            for k, v in nwc.items():
                gridLayout.addWidget(QLabel(k), row, 0)
                gridLayout.addWidget(QLabel(v), row, 1)
                row += 1
            gridLayout.addWidget(newLine(QFrame.Shape.HLine), row, 0, 1, 2)
            row += 1
        hLayout.addWidget(statusGroup)
        # 版本列表单独一个 group
        statusGroup = QGroupBox("版本信息")
        gridLayout = QGridLayout(statusGroup)
        gridLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row = 0
        for k, v in self.robot_status_info.get('VERSION_LIST', {}).items():
            gridLayout.addWidget(QLabel(k), row, 0)
            gridLayout.addWidget(QLabel(v), row, 1)
            row += 1
        hLayout.addWidget(statusGroup)
        # 激活授权信息单独一个group
        statusGroup = QGroupBox("激活/授权信息")
        gridLayout = QGridLayout(statusGroup)
        gridLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        row = 0
        gridLayout.addWidget(QLabel("机器码"), row, 0)
        gridLayout.addWidget(QLabel(self.robot_status_info.get('echoid', "")), row, 1)
        row += 1
        for feature in self.robot_status_info.get('features', []):
            if not isinstance(feature, dict):
                continue
            gridLayout.addWidget(QLabel(feature.get("name", "")), row, 0)
            gridLayout.addWidget(
                QLabel(f"已激活({feature.get('expiry_date', '')})" if feature.get("active", False) else "未激活"), row,
                1)
            row += 1
        hLayout.addWidget(statusGroup)
        # Robod 设备信息
        statusGroup = QGroupBox("设备信息")
        gridLayout = QGridLayout(statusGroup)
        gridLayout.setAlignment(Qt.AlignmentFlag.AlignLeft)  # 左对齐
        column = 0
        gridLayout.addWidget(alignLabel("启动次数"), 0, column)
        gridLayout.addWidget(alignLabel(f"{self.robot_core_status_info.get('count', 0)}"), 1, column)
        column += 1
        gridLayout.addWidget(newLine(QFrame.Shape.VLine), 0, column, 2, 1)
        column += 1
        gridLayout.addWidget(alignLabel("内存占用"), 0, column)
        gridLayout.addWidget(alignLabel(f"{self.robot_core_status_info.get('mem', 0):.2f} MB"), 1, column)
        column += 1
        gridLayout.addWidget(newLine(QFrame.Shape.VLine), 0, column, 2, 1)
        column += 1
        gridLayout.addWidget(alignLabel("CPU占用率"), 0, column)
        if self.robot_core_status_info.get("cpu_num") <= 0:
            txt = f"{self.robot_core_status_info.get('cpu'):.1f}% 温度 {self.robot_core_status_info.get('cpu_temp'):.1f} ℃"
        else:
            txt = f"{self.robot_core_status_info.get('cpu') / self.robot_core_status_info.get('cpu_num'):.1f}% ({self.robot_core_status_info.get('cpu'):.1f}%/{self.robot_core_status_info.get('cpu_num')}) 温度 {self.robot_core_status_info.get('cpu_temp'):.1f} ℃"
        gridLayout.addWidget(alignLabel(txt), 1, column)
        column += 1
        gridLayout.addWidget(newLine(QFrame.Shape.VLine), 0, column, 2, 1)
        column += 1
        gridLayout.addWidget(alignLabel("运行状态"), 0, column)
        gridLayout.addWidget(
            alignLabel("已启动" if {self.robot_core_status_info.get('is_running', False)} else "未启动"),
            1, column)
        column += 1
        gridLayout.addWidget(newLine(QFrame.Shape.VLine), 0, column, 2, 1)
        column += 1
        gridLayout.addWidget(alignLabel("守护进程版本"), 0, column)
        srcName = self.robot_core_robod_version_info.get("srcName")
        if not srcName:
            srcType = self.robot_core_robod_version_info.get("srcName", -1)
            if 0 <= srcType <= 4:
                srcName = ["[SRC-2000]", "[SRC-3000]", "[SRC-800]", "[SRC-2000.2]", "[SRC-2000.1]", "[SRC-?]"][srcType]
            else:
                srcName = "[SRC-?]"
        gridLayout.addWidget(alignLabel(f"{self.robot_core_robod_version_info.get('version', '')} {srcName}"), 1,
                             column)

        layout.addWidget(statusGroup)
        # 报警的信息放在底部
        statusGroup = QGroupBox("报警信息")
        vBoxLayout = QVBoxLayout(statusGroup)
        for k in ["errors", "fatals", "notices", "warnings"]:
            for d in self.robot_status_alarm_info.get(k, []):
                if not isinstance(d, dict):
                    continue
                vBoxLayout.addWidget(QLabel(
                    f"[{d.get('dateTime', '')}][{d.get('code', '')}][第{d.get('times', '')}次]{d.get('desc', '')}"))
        layout.addWidget(statusGroup)

        # 渲染
        w.adjustSize()
        pixmap = QPixmap(w.size())
        w.render(pixmap)
        # 右下角加一个时间水印
        painter = QPainter(pixmap)
        painter.setPen(QColor(255, 0, 0, 100))
        painter.drawText(pixmap.rect() - QMargins(0, 0, 20, 20), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        painter.end()
        self.widgetPixmap = pixmap

class ExportRobotInfo(QWidget):
    META = {
        "title": "导出机器人配置信息",
        "config": {
            "export_directory": {
                "name": "导出目录",
                "desc": "导出机器人配置信息的目录",
                "value": QDir.current().absolutePath() + "/ExportRobotInfo",
                "type": "dir"
            },
            "camera": {
                "name": "摄像头",
                "desc": "用于拍摄照片的摄像头",
                "value": "None",
                "type": "enum",
                "enum": ["None"] + [d.description() for d in QMediaDevices.videoInputs()]
            }
        }
    }

    def __init__(self):
        super().__init__()
        self.initUI()

        self.setAcceptDrops(True)
        self.workThread = Thread()
        self.workThread.finished.connect(self.slotWorkThreadFinished)

    def initUI(self):
        layout = QVBoxLayout(self)

        hLayout = QHBoxLayout()
        hLayout.addWidget(QLabel("IP:"))
        self.ipLineEdit = QLineEdit("192.168.192.5")
        self.ipLineEdit.setValidator(QRegularExpressionValidator(QRegularExpression(r"((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})(\.((2(5[0-5]|[0-4]\d))|[0-1]?\d{1,2})){3}"), self))
        hLayout.addWidget(self.ipLineEdit)
        self.getInfoButton = QPushButton("获取配置信息")
        self.saveButton = QPushButton("导出机器人配置信息")
        self.saveButton.setEnabled(False)
        hLayout.addWidget(self.getInfoButton)
        hLayout.addWidget(self.saveButton)
        layout.addLayout(hLayout)

        groupBox = QGroupBox("配置信息")
        groupBoxLayout = QVBoxLayout(groupBox)
        self.scrollArea = QScrollArea()
        self.infoLabel = QLabel()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.infoLabel)
        groupBoxLayout.addWidget(self.scrollArea)
        layout.addWidget(groupBox)

        hLayout = QHBoxLayout()
        self.pictureWidget1 = PictureWidgetPrivate()
        self.pictureWidget2 = PictureWidgetPrivate()
        hLayout.addWidget(self.pictureWidget1)
        hLayout.addWidget(self.pictureWidget2)
        layout.addLayout(hLayout)

        self.getInfoButton.clicked.connect(self.slotGetInfoButtonClicked)
        self.saveButton.clicked.connect(self.slotSaveButtonClicked)

    def slotGetInfoButtonClicked(self):
        self.workThread.ip = self.ipLineEdit.text()
        self.workThread.start()
        self.getInfoButton.setEnabled(False)

    def slotSaveButtonClicked(self):
        # 创建一个目录
        saveDir = cfg[self.__class__.__name__, "export_directory"]
        if not saveDir:
            saveDir = ExportRobotInfo.META["config"]["export_directory"]["value"]
        saveDir = QDir(saveDir + "/" + self.workThread.robotID + datetime.now().strftime("_%Y%m%d%H%M%S"))
        saveDir.mkpath(saveDir.absolutePath())
        printLog(f"导出机器人配置信息 到 {saveDir.absolutePath()}")
        # 保存图片
        self.workThread.widgetPixmap.save(saveDir.filePath(self.workThread.robotID + ".png"))
        # 控制器的图片
        if self.pictureWidget1.picturePath:
            file = QFileInfo(self.pictureWidget1.picturePath)
            QFile.copy(self.pictureWidget1.picturePath, saveDir.filePath(file.fileName()))
        if self.pictureWidget2.picturePath:
            file = QFileInfo(self.pictureWidget2.picturePath)
            QFile.copy(self.pictureWidget2.picturePath, saveDir.filePath(file.fileName()))

        # 原始数据
        with open(saveDir.filePath("robot_status_info.json"), "w") as f:
            json.dump(self.workThread.robot_status_info, f)
        with open(saveDir.filePath("robot_status_run_info.json"), "w") as f:
            json.dump(self.workThread.robot_status_run_info, f)
        with open(saveDir.filePath("robot_status_battery_info.json"), "w") as f:
            json.dump(self.workThread.robot_status_battery_info, f)
        with open(saveDir.filePath("robot_status_alarm_info.json"), "w") as f:
            json.dump(self.workThread.robot_status_alarm_info, f)

        with open(saveDir.filePath("robot_core_status_info.json"), "w") as f:
            json.dump(self.workThread.robot_core_status_info, f)
        with open(saveDir.filePath("robot_core_robod_version_info.json"), "w") as f:
            json.dump(self.workThread.robot_core_robod_version_info, f)
        printLog(f"完成")


    def slotWorkThreadFinished(self):
        self.infoLabel.setPixmap(self.workThread.widgetPixmap)
        self.getInfoButton.setEnabled(True)
        self.saveButton.setEnabled(True)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()


    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            pList = []
            for url in event.mimeData().urls():
                fileInfo = QFileInfo(url.toLocalFile())
                if fileInfo.suffix().lower() in ["jpg", "jpeg", "png"]:
                    pList.append(fileInfo.filePath())
            if len(pList) >= 1:
                self.pictureWidget1.picturePath = pList[0]
            if len(pList) >= 2:
                self.pictureWidget2.picturePath = pList[1]
