from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QGridLayout, QLineEdit, QToolButton, QFileDialog, \
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QLabel, QPushButton

import tools
from init import cfg


class SettingDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingDialog, self).__init__(parent)
        self.initUI()

    def initUI(self):
        self.settingDialog = QDialog(self)
        self.setWindowTitle("设置")
        self.resize(400, 600)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for c in dir(tools):
            if c.startswith("__"):
                continue
            cls = getattr(tools, c)
            if not hasattr(cls, "META"):
                continue
            config = cls.META.get("config")
            if not config or not isinstance(config, dict):
                continue
            groupBox = QGroupBox(cls.META.get("title", c))
            groupBox.key = c
            layout.addWidget(groupBox)
            gridLayout = QGridLayout(groupBox)
            for i, (k, d) in enumerate(config.items()):
                if not isinstance(d, dict) and not d.get("value"):
                    continue
                w = None
                if d["type"] == "str":
                    w = QLineEdit(d["value"] if not (v := cfg[c, k]) else v)
                elif d["type"] == "dir":
                    w = QLineEdit(d["value"] if not (v := cfg[c, k]) else v)
                    toolButton = QToolButton()
                    toolButton.setText("...")
                    gridLayout.addWidget(toolButton, i, 2)
                    toolButton.clicked.connect(self.getExistingDirectoryButtonClicked)
                elif d["type"] == "bool":
                    w = QCheckBox()
                    w.setChecked(d["value"] if not (v := cfg[c, k]) else (True if v.lower() == "true" else False))
                elif d["value"] == "int":
                    w = QSpinBox()
                    w.setRange(d["minValue"], d["maxValue"])
                    try:
                        v = int(cfg[c, k])
                    except:
                        v = d["value"]
                    w.setValue(v)
                elif d["value"] == "float":
                    w = QDoubleSpinBox()
                    w.setRange(d["minValue"], d["maxValue"])
                    try:
                        v = float(cfg[c, k])
                    except:
                        v = d["value"]
                    w.setValue(v)
                elif d["type"] == "enum":
                    w = QComboBox()
                    w.addItems(d["enum"])
                    if (v := cfg[c, k]) and v in d["enum"]:
                        w.setCurrentText(v)
                    else:
                        w.setCurrentText(d["value"])
                if w:
                    name = d.get("name", k)
                    gridLayout.addWidget(QLabel(name), i, 0)
                    w.key = k
                    w.setToolTip(d.get("desc", ""))
                    gridLayout.addWidget(w, i, 1)
        savaBtn = QPushButton("保存")
        layout.addWidget(savaBtn)
        savaBtn.clicked.connect(self.saveSettingButtonTriggered)

    def getExistingDirectoryButtonClicked(self):
        layout: QGridLayout = self.sender().parent().layout()
        row, column, _, _ = layout.getItemPosition(layout.indexOf(self.sender()))
        lineEdit: QLineEdit = layout.itemAtPosition(row, column - 1).widget()
        dir = QFileDialog.getExistingDirectory(self, "选择目录", lineEdit.text())
        if not dir:
            return
        lineEdit.setText(dir)

    @Slot()
    def saveSettingButtonTriggered(self):
        for i in range(self.layout().count()):
            w = self.layout().itemAt(i).widget()
            if not w or not (gridlayout := w.layout()):
                continue
            for j in range(gridlayout.rowCount()):
                cw = gridlayout.itemAtPosition(j, 1).widget()
                if isinstance(cw, QLineEdit):
                    cfg[w.key, cw.key] = cw.text()
                elif isinstance(cw, QCheckBox):
                    cfg[w.key, cw.key] = cw.isChecked()
                elif isinstance(cw, (QSpinBox, QDoubleSpinBox)):
                    cfg[w.key, cw.key] = cw.value()
                elif isinstance(cw, QComboBox):
                    cfg[w.key, cw.key] = cw.currentText()
        self.close()
