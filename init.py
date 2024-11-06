import configparser
import inspect
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QTemporaryDir

VERSION_MAJOR = 0
VERSION_MINOR = 2
VERSION_PATCH = 0
VERSION_NUMBER = 5

VERSION = f"{VERSION_MAJOR}.{VERSION_MINOR}.{VERSION_PATCH}"


class __Obj__(QObject):
    sigPrintLog = Signal(object)

    def __init__(self):
        super().__init__()


__obj__ = __Obj__()


def printLog(*args):
    tm = datetime.now().strftime('%Y-%m-%d %H:%M:%S:%f')[:-3]
    s = ""
    if len(args) == 1:
        s = str(args[0])
    else:
        for i in args:
            s += str(i) + " "
    __obj__.sigPrintLog.emit(f"{tm}\t{s}")

    # 获取当前堆栈帧
    frame = inspect.currentframe()
    # 获取调用者的堆栈帧（即当前函数的调用者）
    caller_frame = frame.f_back
    # 获取调用者的文件名
    filename = caller_frame.f_code.co_filename
    # 获取调用者的行号
    lineno = caller_frame.f_lineno
    fullname = caller_frame.f_code.co_name
    print(f'[{tm}][{filename}][{lineno}][{fullname}] [{s}]')


class __CFG__:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

    def __getitem__(self, item):
        if not self.config.has_option(item[0], item[1]):
            return None
        return self.config.get(item[0], item[1])

    def __setitem__(self, key, value):
        if not self.config.has_section(key[0]):
            self.config.add_section(key[0])
        printLog(f"设置：{key[0]}::{key[1]} = {str(value)}")
        self.config.set(key[0], key[1], str(value))
        with open('config.ini', 'w') as f:
            self.config.write(f)


cfg = __CFG__()

tempDir: QTemporaryDir = QTemporaryDir()
if not tempDir.isValid():
    printLog("创建临时目录失败！")


def clearn():
    tempDir.remove()
