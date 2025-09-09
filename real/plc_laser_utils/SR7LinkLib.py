#######################################################################################################################
# Company: SSZN
# Author:  WangMing
# Date:    2023-06-06
# Copyright (c) 2023. Shenzhen sincevision technology co.,ltd. All rights reserved. 
# Description:
#          Python 调用SR7Link的接口库
# Modification:
#          
#######################################################################################################################
import os
from ctypes import *
import struct
from enum import IntEnum

from IIDS.settings import BASE_DIR

# Z向数据分辨率(单位mm)
Z_RESOLUTION = 0.00001

# 返回码枚举
class SR7IF_RETURN_CODE(IntEnum):
    ERROR_NOT_FOUND          = -999
    ERROR_COMMAND            = -998
    ERROR_PARAMETER          = -997
    ERROR_UNIMPLEMENTED      = -996
    ERROR_HANDLE             = -995
    ERROR_MEMORY             = -994
    ERROR_TIMEOUT            = -993
    ERROR_DATABUFFER         = -992
    ERROR_STREAM             = -991
    ERROR_CLOSED             = -990
    ERROR_VERSION            = -989
    ERROR_ABORT              = -988
    ERROR_ALREADY_EXISTS     = -987
    ERROR_FRAME_LOSS         = -986
    ERROR_ROLL_DATA_OVERFLOW = -985
    ERROR_ROLL_BUSY          = -984
    ERROR_MODE               = -983
    ERROR_CAMERA_NOT_ONLINE  = -982
    ERROR                    = -1
    NORMAL_STOP              = -100
    OK                       = 0


class SR7IF_ETHERNET_CONFIG(Structure):
    _fields_ = [('abyIpAddr', c_ubyte * 4)]


dll_path = os.path.join(BASE_DIR, "real", 'plc_laser_utils', "SR7Link.dll")
SR7Lib = CDLL(dll_path)
# SR7Lib = CDLL("./SR7Link.dll")

def save_as_ecd(path: str, data: list, xInterval: float, yInterval: float):
    """将整型的矩阵数据转换成ecd格式

    Args:
        path (str): ecd文件存储路径
        data (list): 矩阵数据（每行的数据个数必须一样), 数据为整型
        xInterval (float): x向间距
        yInterval (float): y向间距
    """
    # 创建文件头
    header = create_string_buffer(10240)
    struct.pack_into('I', header, 0, 2)
    struct.pack_into('i', header, 4, len(data[0]))
    struct.pack_into('i', header, 8, len(data))
    struct.pack_into('d', header, 12, xInterval)
    struct.pack_into('d', header, 20, yInterval)
    struct.pack_into('s', header, 28, "SSZN2021 V00000002".encode())

    # 写入数据
    with open(path, 'wb') as f:
        f.write(header)
        for row in data:
            for d in row:
                tmp = struct.pack('i', d)
                f.write(tmp)

def SR7IF_EthernetOpen(deviceID:int, ip:tuple) -> int:
    """通过IP地址连接设备

    Args:

        deviceID (int) : 设备号，范围0-3.

        ip      (tuple): IP地址，格式: (192, 168, 0, 10)

    Returns:
    
        int: 返回码
            <0:  失败 
            =0:  成功
    """
    _ip = SR7IF_ETHERNET_CONFIG()
    _ip.abyIpAddr = ip

    return SR7Lib.SR7IF_EthernetOpen(deviceID, _ip.abyIpAddr)

def SR7IF_CommClose(deviceID:int) -> int:
    """断开与设备的连接

    Args:

        deviceID (int): 设备号，范围0-3.

    Returns:

        int: 返回码
    """
    return SR7Lib.SR7IF_CommClose(deviceID)

def SR7IF_SwitchProgram(deviceID:int, No:int) -> int:
    """切换相机配置的配方，设备断电重启后不保存配方号.

    Args:

        deviceID (int): 设备号，范围0~3.

        No       (int): 配方编号，范围0~63.

    Returns:
    
        int: 返回码
            <0:  失败 
            =0:  成功
    """
    return SR7Lib.SR7IF_SwitchProgram(deviceID, No)

def SR7IF_StartMeasure(deviceID:int, timeout:int=50000):
    """开始批处理,立即执行批处理程序.

    Args:
        deviceID (int): 设备ID号，范围0~63

        timeout (int, optional): 非循环获取时,超时时间(单位ms),-1为无限等待;循环模式该参数可设置为-1. Defaults to 50000.

    Returns:
        int: 返回码
            <0:  失败 
            =0:  成功
    """
    return SR7Lib.SR7IF_StartMeasure(deviceID, timeout)

def SR7IF_StartIOTriggerMeasure(deviceID:int, timeout:int=50000):
    """开始批处理,硬件IO触发开始批处理

    Args:
        deviceID (int): 设备ID号，范围0~63

        timeout (int, optional): 非循环获取时,超时时间(单位ms),-1为无限等待;循环模式该参数可设置为-1. Defaults to 50000.

    Returns:
        int: 返回码
            <0:  失败 
            =0:  成功
    """
    return SR7Lib.SR7IF_StartIOTriggerMeasure(deviceID, timeout)

def SR7IF_StopMeasure(deviceID:int):
    """停止批处理

    Args:
        deviceID (int): 设备ID号，范围0~63

    Returns:
        int: 返回码
            <0:  失败 
            =0:  成功
    """
    return SR7Lib.SR7IF_StopMeasure(deviceID)

def SR7IF_ReceiveData(deviceID:int):
    """阻塞方式获取数据

    Args:
        deviceID (int): 设备ID号，范围0~63

    Returns:
        int: 返回码
            <0:  失败 
            =0:  成功
    """
    obj = c_void_p()
    return SR7Lib.SR7IF_ReceiveData(deviceID, obj)

def SR7IF_ProfilePointSetCount(deviceID:int):
    """获取当前批处理设定行数

    Args:
        deviceID (int): 设备ID号，范围0~63

    Returns:
        int: 返回设定批处理行数
    """
    obj = c_void_p()
    return SR7Lib.SR7IF_ProfilePointSetCount(deviceID, obj)

def SR7IF_ProfilePointCount(deviceID:int):
    """获取批处理实际获取行数

    Args:
        deviceID (int): 设备ID号，范围0~63

    Returns:
        int: 返回批处理实际获取行数
    """
    obj = c_void_p()
    return SR7Lib.SR7IF_ProfilePointCount(deviceID, obj)

def SR7IF_ProfileDataWidth(deviceID:int):
    """获取单行数据宽度

    Args:
        deviceID (int): 设备ID号，范围0~63

    Returns:
        int: 返回数据宽度(单位像素).
    """
    obj = c_void_p()
    return SR7Lib.SR7IF_ProfileDataWidth(deviceID, obj)

def SR7IF_ProfileData_XPitch(deviceID:int):
    """获取数据x方向间距

    Args:
        deviceID (int): 设备ID号，范围0~63

    Returns:
        int: 返回数据x方向间距(mm).
    """
    obj = c_void_p()
    return SR7Lib.SR7IF_ProfileData_XPitch(deviceID, obj)

def SR7IF_GetProfileData(deviceID:int, dataSize:int):
    """阻塞方式获取轮廓数据

    Args:
        deviceID (int): 设备ID号，范围0~63

        dataSize (int): 数据缓存的大小，需大于等于行宽*帧数

    Returns:
        int: 返回码， <0:  失败  =0:  成功

        c_long_Array: 轮廓数据，双相机为A/B行交替数据
    """
    obj = c_void_p()
    data = (c_int * dataSize)()
    rc = SR7Lib.SR7IF_GetProfileData(deviceID, obj, byref(data))
    return rc, data

def SR7IF_GetIntensityData(deviceID:int, dataSize:int):
    """阻塞方式获取亮度数据

    Args:
        deviceID (int): 设备ID号，范围0~63

        dataSize (int): 数据缓存的大小，需大于等于行宽*帧数

    Returns:
        int: 返回码， <0:  失败  =0:  成功
        c_ubyte_Array: 亮度数据，双相机为A/B行交替数据
    """
    obj = c_void_p()
    data = (c_uint8 * dataSize)()
    rc = SR7Lib.SR7IF_GetIntensityData(deviceID, obj, byref(data))
    return rc, data

def SR7IF_GetBatchRollData(deviceID:int, dataSize:int, getCnt:int):
    """无终止循环获取数据

    Args:
        deviceID (int): 设备ID号，范围0~63

        dataSize (int): 数据缓存的大小，需大于等于行宽*获取帧数

        getCnt (int): 获取帧数

    Returns:
        int: 返回码， <0:  失败  >=0:  实际返回的帧数

        c_long_Array: 轮廓数据，双相机为A/B行交替数据

        c_ubyte_Array: 亮度数据，双相机为A/B行交替数据

        c_ulong_Array: 编码器值，双相机为A/B行交替数据
        
        c_longlong_Array: 帧编号数据
        
        c_ulong_Array: 批处理过快掉帧数量，双相机为A/B交替数据

    """
    obj = c_void_p()
    profileData = (c_int * dataSize)()
    intensityData = (c_uint8 * dataSize)()
    # 兼容双相机
    encoderData = (c_uint * (getCnt *2))()
    frameID = (c_longlong * dataSize)()
    frameLoss = (c_uint * 1024)()
    rc = SR7Lib.SR7IF_GetBatchRollData(deviceID, obj, byref(profileData), byref(intensityData), byref(encoderData), byref(frameID), byref(frameLoss), getCnt)
    return rc, profileData, intensityData, encoderData, frameID, frameLoss

def SR7IF_GetBatchRollError(deviceID:int):
    """无终止循环获取数据异常计算值

    Args:
        deviceID (int): 设备ID号，范围0~63

    Returns:
        int: 返回码， <0:  失败  =0:  成功

        int: 返回网络传输导致错误的数量

        int: 返回用户获取导致错误的数量
    """
    ethErrCnt = c_int()
    userErrCnt = c_int()
    rc = SR7Lib.SR7IF_GetBatchRollError(deviceID, byref(ethErrCnt), byref(userErrCnt))
    return rc, ethErrCnt.value, userErrCnt.value


def SR7IF_GetSingleProfile(deviceID:int, dataSize:int, getCnt:int):
    """无终止循环获取数据

    Args:
        deviceID (int): 设备ID号，范围0~63

        dataSize (int): 数据缓存的大小，需大于等于行宽*获取帧数

        getCnt (int): 获取帧数

    Returns:
        int: 返回码， <0:  失败  =0: 成功 

        c_long_Array: 轮廓数据，双相机为A/B行交替数据

        c_ulong_Array: 编码器值，双相机为A/B行交替数据       

    """
    profileData = (c_int * dataSize)()
    # 兼容双相机
    encoderData = (c_uint * (getCnt *2))()
    rc = SR7Lib.SR7IF_GetSingleProfile(deviceID, byref(profileData), byref(encoderData))
    return rc, profileData, encoderData

def SR7IF_SetSetting_Batch(deviceID:int, BatchSetting:int):
    """ 设置 Batch 模式
    Args:
        deviceID (int): 设备ID号，范围0~63

        BatchSetting (int): 0 ： 批处理 off， 1：批处理 On

    Returns:
        int: 返回码， <0:  失败  =0: 成功 
    """

    Target = (c_int * 4)()
    Target[0] = 0
    pData = (c_byte * 1)()
    pData[0] = BatchSetting

    rc = SR7Lib.SR7IF_SetSetting(deviceID, 0x02, -1, 0x00, 0x03,  byref(Target), byref(pData), 0x01)
    return rc
    