import json
import struct
from socket import socket

PACK_FMT_STR = '!BBHLHHH2s'


class RBKUtils:

    @staticmethod
    def pack(number, _json:dict = None, data: bytes = None, id=1):
        dataLength = 0
        jsonLength = 0

        jsData = b''
        if _json is not None:
            jsData = json.dumps(_json).encode()
            jsonLength = len(jsData)
            dataLength = jsonLength

        if data is not None:
            dataLength += len(data)

        d = struct.pack(PACK_FMT_STR, 0x5A, 0x01, id, dataLength, number, number, jsonLength, b'\x00\x00')

        if jsData is not None:
            d = d + jsData

        if data is not None:
            d = d + data

        return d

    @staticmethod
    def unpack(data):
        return struct.unpack(PACK_FMT_STR, data)

    @staticmethod
    def request(so: socket, number, _json:dict = None, data: bytes = None, id=1):
        req = RBKUtils.pack(number, _json, data, id)
        so.sendall(req)
        # 接收报文头
        headData = so.recv(16)
        # 解析报文头
        header = RBKUtils.unpack(headData)
        # 获取报文体长度
        bodyLen = header[3]
        jsonLen = header[6]
        readSize = 1024
        recvData = b''
        while (bodyLen > 0):
            recv = so.recv(readSize)
            recvData += recv
            bodyLen -= len(recv)
            if bodyLen < readSize:
                readSize = bodyLen
        js = {}
        try:
            if jsonLen > 0:
                js = json.loads(recvData[:jsonLen])
        except Exception as e:
            print("Error:", e)
        return js, recvData[jsonLen:header[3]]
