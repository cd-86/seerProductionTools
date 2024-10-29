import struct
from socket import socket

PACK_FMT_STR = '!BBHLH6s'


class RBKUtils:

    @staticmethod
    def pack(number, data: bytes = None, id=1):
        length = 0
        if data is not None:
            length = len(data)
        d = struct.pack(PACK_FMT_STR, 0x5A, 0x01, id, length, number, b'\x00\x00\x00\x00\x00\x00')
        if data is not None:
            d = d + data
        return d

    @staticmethod
    def unpack(data):
        return struct.unpack(PACK_FMT_STR, data)

    @staticmethod
    def request(so: socket, number, data: bytes = None, id=1):
        req = RBKUtils.pack(number, data, id)
        so.sendall(req)
        # 接收报文头
        headData = so.recv(16)
        # 解析报文头
        header = RBKUtils.unpack(headData)
        # 获取报文体长度
        bodyLen = header[3]
        readSize = 1024
        recvData = b''
        while (bodyLen > 0):
            recv = so.recv(readSize)
            recvData += recv
            bodyLen -= len(recv)
            if bodyLen < readSize:
                readSize = bodyLen
        return recvData[:header[3]]
