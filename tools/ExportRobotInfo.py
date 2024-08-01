from datetime import datetime

from PySide6 import QtWidgets
from PySide6.QtGui import QPainter, QPixmap, QPen, QKeyEvent, QImage
from PySide6.QtMultimedia import QMediaDevices, QMediaCaptureSession, QCamera, QImageCapture
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QPushButton, QGroupBox, QTextEdit, \
    QFileDialog, QDialog
from PySide6.QtCore import QDir, QMargins, QRectF, QRect, Qt, QPoint, Slot

from init import printLog, cfg, tempDir


class PictureViewer(QWidget):
    """
    预览图片的控件
    """

    def __init__(self):
        super().__init__()
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

        self.pixmap: QPixmap = None
        self.prePos = QPoint(0, 0)

    def setPixmap(self, pixmap: QPixmap):
        self.pixmap = pixmap
        self.scale = 1
        self.translate = QPoint(0, 0)

    def paintEvent(self, event):
        painter = QPainter(self)
        rect = self.rect() - QMargins(0, 0, 1, 1)
        painter.save()
        if self.pixmap is not None:
            painter.translate(rect.center())
            painter.translate(self.translate)
            v = min(rect.width() / self.pixmap.width(), rect.height() / self.pixmap.height())
            painter.scale(v, v)
            painter.scale(self.scale, self.scale)
            painter.translate(-self.pixmap.width() / 2, -self.pixmap.height() / 2)
            painter.drawPixmap(self.pixmap.rect(), self.pixmap)
        painter.restore()
        painter.setPen(QPen(Qt.GlobalColor.white, 7))
        painter.drawRect(rect)
        painter.setPen(QPen(Qt.GlobalColor.black))
        painter.drawRect(rect)

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

        self.picturePath = ""

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

    def localButtonClicked(self):
        f = QFileDialog.getOpenFileName(self, "选择一个图片", "", "image (*.png *.jpg *.jpeg *.bmp)")
        if f[0]:
            self.picturePath = f[0]
            self.pictureViewer.setPixmap(QPixmap(self.picturePath))
            self.pictureViewer.update()

    def shootButtonClicked(self):
        cv = CameraViewer()
        cv.exec()
        if not cv.isFinished:
            return
        filePath = tempDir.filePath(datetime.now().strftime("IMG_%Y%m%d%H%M%S.png"))
        if not cv.img.save(filePath):
            print("保存图片失败！")
            return
        self.picturePath = filePath
        self.pictureViewer.setPixmap(QPixmap(self.picturePath))
        self.pictureViewer.update()


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

    def initUI(self):
        layout = QVBoxLayout(self)

        hLayout = QHBoxLayout()
        hLayout.addWidget(QLabel("IP:"))
        self.ipLineEdit = QLineEdit()
        hLayout.addWidget(self.ipLineEdit)
        self.getInfoButton = QPushButton("获取配置信息")
        self.saveButton = QPushButton("导出机器人配置信息")
        hLayout.addWidget(self.getInfoButton)
        hLayout.addWidget(self.saveButton)
        layout.addLayout(hLayout)

        groupBox = QGroupBox("配置信息")
        groupBoxLayout = QVBoxLayout(groupBox)
        self.infoTextEdit = QTextEdit()
        groupBoxLayout.addWidget(self.infoTextEdit)
        layout.addWidget(groupBox)

        hLayout = QHBoxLayout()
        self.pictureWidget1 = PictureWidgetPrivate()
        self.pictureWidget2 = PictureWidgetPrivate()
        hLayout.addWidget(self.pictureWidget1)
        hLayout.addWidget(self.pictureWidget2)
        layout.addLayout(hLayout)
