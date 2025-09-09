import snap7
import struct
from datetime import datetime, timedelta
from snap7 import util
import logging

# 创建日志记录器
plcLog = logging.getLogger('plcLog')


def create_connect():
    # PLC客户端实例
    plc = snap7.client.Client()
    # 连接到PLC
    plc.connect('192.168.1.1', 0, 1)  # PLC的IP地址、机架号和槽号
    # 检查连接是否成功
    if plc.get_connected():
        plcLog.info("Connect to PLC")
    else:
        plcLog.info("Failed to connect to PLC")

    # 读取数据块 DB160，偏移量为0，长度为356字节
    data_bcd = plc.db_read(160, 0, 358)
    # print("Raw data:", data_bcd)
    return data_bcd

# 解析数据
def parse_struct(data):
    res_data = {}

    # ver (Byte)
    idx = 0
    res_data['ver'] = util.get_byte(data[idx:idx + 2], 0)

    # Date_And_Time (8 Byte)
    idx = 2
    res_data['plcDt'] = util.get_dt(data[idx:idx + 8], 0)

    # userName (String[16])
    idx = 10
    res_data['userName'] = util.get_string(data[idx:idx + 16], 0)

    # errorBytes (Array[1..40] of Byte)
    idx = 28
    res_data['errorBytes'] = list(data[idx:idx + 40])
    # res_data['errorBytes'] = util.get_array(data[idx:idx + 40], 0)

    # bladeName (String[16])
    idx = 68
    res_data['bladeName'] = util.get_string(data[idx:idx + 16], 0)

    # bladeType (String[16])
    idx = 86
    res_data['bladeType'] = util.get_string(data[idx:idx + 16], 0)

    # bladeLength (Real)
    idx = 104
    res_data['bladeLength'] = util.get_real(data[idx:idx + 4], 0)

    # bladeDiameter (Real)
    idx = 108
    res_data['bladeDiameter'] = util.get_real(data[idx:idx + 4], 0)

    # bladeHoles (Byte)
    idx = 112
    res_data['bladeHoles'] = util.get_byte(data[idx:idx + 1], 0)

    # PowerStatus (Byte)
    idx = 113
    res_data['PowerStatus'] =util.get_byte(data[idx:idx + 1], 0)

    # DoorsStatus (Byte)
    idx = 114
    res_data['DoorsStatus'] = util.get_byte(data[idx:idx + 1], 0)

    # MachineBaseStatus (Byte 1)
    idx = 115
    res_data['MachineBaseStatus'] = util.get_byte(data[idx:idx + 1], 0)

    # ModeStatus (DWORD 4)
    idx = 116
    res_data['ModeStatus'] = util.get_dword(data[idx:idx + 4], 0)

    # MWheelStatus (Byte)
    idx = 120
    res_data['MWheelStatus'] = util.get_byte(data[idx:idx + 1], 0)

    # CutProgNum (Byte)
    idx = 121
    res_data['CutProgNum'] = util.get_byte(data[idx:idx + 1], 0)

    # CutProgStep (Byte)
    idx = 122
    res_data['CutProgStep'] = util.get_byte(data[idx:idx + 1], 0)

    # CutAutoStatus (Byte)
    idx = 123
    res_data['CutAutoStatus'] = util.get_byte(data[idx:idx + 1], 0)

    # MillProgNum (Byte)
    idx = 124
    res_data['MillProgNum'] = util.get_byte(data[idx:idx + 1], 0)

    # MillProgStep (Byte)
    idx = 125
    res_data['MillProgStep'] = util.get_byte(data[idx:idx + 1], 0)

    # MillAutoStatus (Byte)
    idx = 126
    res_data['MillAutoStatus'] = util.get_byte(data[idx:idx + 1], 0)

    # DrillProgNum (Byte)
    idx = 127
    res_data['DrillProgNum'] = util.get_byte(data[idx:idx + 1], 0)

    # DrillProgStep (Byte)
    idx = 128
    res_data['DrillProgStep'] = util.get_byte(data[idx:idx + 1], 0)
    # DrillAutoStatus (Byte)
    idx = 129
    res_data['DrillAutoStatus'] = util.get_byte(data[idx:idx + 1], 0)
    # armStatus (Byte)
    idx = 130
    res_data['armStatus'] = util.get_byte(data[idx:idx + 1], 0)

    # armPositionTarg (Real)
    idx = 132
    res_data['armPositionTarg'] = util.get_real(data[idx:idx + 4], 0)

    # armPositionAct (Real)
    idx = 136
    res_data['armPositionAct'] = util.get_real(data[idx:idx + 4], 0)

    # armPositionMot (Real)
    idx = 140
    res_data['armPositionMot'] = util.get_real(data[idx:idx + 4], 0)

    # armSpeed (Real)
    idx = 144
    res_data['armSpeed'] = util.get_real(data[idx:idx + 4], 0)

    # cutStatus (Byte)
    idx = 148
    res_data['cutStatus'] = util.get_byte(data[idx:idx + 2], 0)
    # cutFeedTarget (Real)
    idx = 150
    res_data['cutFeedTarget'] = util.get_real(data[idx:idx + 4], 0)
    # cutFeedPosition (Real)
    idx = 154
    res_data['cutFeedPosition'] = util.get_real(data[idx:idx + 4], 0)
    # cutFeedSpeed (Real)
    idx = 158
    res_data['cutFeedSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # cutSpindleSpeed (Real)
    idx = 162
    res_data['cutSpindleSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # cutSpindlePower (Real)
    idx = 166
    res_data['cutSpindlePower'] = util.get_real(data[idx:idx + 4], 0)
    # millStatus (Byte)
    idx = 170
    res_data['millStatus'] = util.get_byte(data[idx:idx + 2], 0)
    # millFeedTarget (Real)
    idx = 172
    res_data['millFeedTarget'] = util.get_real(data[idx:idx + 4], 0)
    # millFeedPosition (Real)
    idx = 176
    res_data['millFeedPosition'] = util.get_real(data[idx:idx + 4], 0)
    # millFeedSpeed (Real)
    idx = 180
    res_data['millFeedSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # millSpindleSpeed (Real)
    idx = 184
    res_data['millSpindleSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # millSpindlePower (Real)
    idx = 188
    res_data['millSpindlePower'] = util.get_real(data[idx:idx + 4], 0)
    # radial1Status (Byte)
    idx = 192
    res_data['radial1Status'] = util.get_byte(data[idx:idx + 2], 0)
    # radial1FeedTarget (Real)
    idx = 194
    res_data['radial1FeedTarget'] = util.get_real(data[idx:idx + 4], 0)
    # radial1FeedPosition (Real)
    idx = 198
    res_data['radial1FeedPosition'] = util.get_real(data[idx:idx + 4], 0)
    # radial1FeedSpeed (Real)
    idx = 202
    res_data['radial1FeedSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # radial1SpindleSpeed (Real)
    idx = 206
    res_data['radial1SpindleSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # radial1SpindlePower (Real)
    idx = 210
    res_data['radial1SpindlePower'] = util.get_real(data[idx:idx + 4], 0)
    # radial2Status (Byte)
    idx = 214
    res_data['radial2Status'] = util.get_byte(data[idx:idx + 2], 0)
    # radial2FeedTarget (Real)
    idx = 216
    res_data['radial2FeedTarget'] = util.get_real(data[idx:idx + 4], 0)
    # radial2FeedPosition (Real)
    idx = 220
    res_data['radial2FeedPosition'] = util.get_real(data[idx:idx + 4], 0)
    # radial2FeedSpeed (Real)
    idx = 224
    res_data['radial2FeedSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # radial2SpindleSpeed (Real)
    idx = 228
    res_data['radial2SpindleSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # radial2SpindlePower (Real)
    idx = 232
    res_data['radial2SpindlePower'] = util.get_real(data[idx:idx + 4], 0)
    # axial1Status (Byte)
    idx = 236
    res_data['axial1Status'] = util.get_byte(data[idx:idx + 2], 0)
    # axial1FeedTarget (Real)
    idx = 238
    res_data['axial1FeedTarget'] = util.get_real(data[idx:idx + 4], 0)
    # axial1FeedPosition (Real)
    idx = 242
    res_data['axial1FeedPosition'] = util.get_real(data[idx:idx + 4], 0)
    # axial1FeedSpeed (Real)
    idx = 246
    res_data['axial1FeedSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # axial1SpindleSpeed (Real)
    idx = 250
    res_data['axial1SpindleSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # axial1SpindlePower (Real)
    idx = 254
    res_data['axial1SpindlePower'] = util.get_real(data[idx:idx + 4], 0)
    # axial2Status (Byte)
    idx = 258
    res_data['axial2Status'] = util.get_byte(data[idx:idx + 2], 0)
    # axial2FeedTarget (Real)
    idx = 260
    res_data['axial2FeedTarget'] = util.get_real(data[idx:idx + 4], 0)
    # axial2FeedPosition (Real)
    idx = 264
    res_data['axial2FeedPosition'] = util.get_real(data[idx:idx + 4], 0)
    # axial2FeedSpeed (Real)
    idx = 268
    res_data['axial2FeedSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # axial2SpindleSpeed (Real)
    idx = 272
    res_data['axial2SpindleSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # axial2SpindlePower (Real)
    idx = 276
    res_data['axial2SpindlePower'] = util.get_real(data[idx:idx + 4], 0)
    # axial3Status (Byte)
    idx = 280
    res_data['axial3Status'] = util.get_byte(data[idx:idx + 2], 0)
    # axial3FeedTarget (Real)
    idx = 282
    res_data['axial3FeedTarget'] = util.get_real(data[idx:idx + 4], 0)
    # axial3FeedPosition (Real)
    idx = 286
    res_data['axial3FeedPosition'] = util.get_real(data[idx:idx + 4], 0)
    # axial3FeedSpeed (Real)
    idx = 290
    res_data['axial3FeedSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # axial3SpindleSpeed (Real)
    idx = 294
    res_data['axial3SpindleSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # axial3SpindlePower (Real)
    idx = 298
    res_data['axial3SpindlePower'] = util.get_real(data[idx:idx + 4], 0)
    # mill2Status (Byte)
    idx = 302
    res_data['mill2Status'] = util.get_byte(data[idx:idx + 2], 0)
    # mill2FeedTarget (Real)
    idx = 304
    res_data['mill2FeedTarget'] = util.get_real(data[idx:idx + 4], 0)
    # mill2FeedPosition (Real)
    idx = 308
    res_data['mill2FeedPosition'] = util.get_real(data[idx:idx + 4], 0)
    # mill2FeedSpeed (Real)
    idx = 312
    res_data['mill2FeedSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # machineBaseStatus_1 (Byte)
    idx = 316
    res_data['machineBaseStatus_1'] = util.get_byte(data[idx:idx + 2], 0)
    # machineBaseTarget (Real)
    idx = 318
    res_data['machineBaseTarget'] = util.get_real(data[idx:idx + 4], 0)
    # machineBasePosition (Real)
    idx = 322
    res_data['machineBasePosition'] = util.get_real(data[idx:idx + 4], 0)
    # machineBaseSpeed (Real)
    idx = 326
    res_data['machineBaseSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # clampXStatus (Byte)
    idx = 330
    res_data['clampXStatus'] = util.get_byte(data[idx:idx + 2], 0)
    # clampXTarget (Real)
    idx = 332
    res_data['clampXTarget'] = util.get_real(data[idx:idx + 4], 0)
    # clampXPosition (Real)
    idx = 336
    res_data['clampXPosition'] = util.get_real(data[idx:idx + 4], 0)
    # clampXSpeed (Real)
    idx = 340
    res_data['clampXSpeed'] = util.get_real(data[idx:idx + 4], 0)
    # clampYStatus (Byte)
    idx = 344
    res_data['clampYStatus'] = util.get_byte(data[idx:idx + 2], 0)
    # clampYTarget (Real)
    idx = 346
    res_data['clampYTarget'] = util.get_real(data[idx:idx + 4], 0)
    # clampYPosition (Real)
    idx = 350
    res_data['clampYPosition'] = util.get_real(data[idx:idx + 4], 0)
    # clampYSpeed (Real)
    idx = 354
    res_data['clampYSpeed'] = util.get_real(data[idx:idx + 4], 0)

    return res_data


def get_plc_data():
    try:
        # 连接plc并获取原始数据
        plc_real_data = create_connect()
        # 解析数据并返回
        res_data = parse_struct(plc_real_data)
        # plcLog.info(res_data)
    except Exception as e:
        plcLog.error(f"Get Plc error: {e}")
        raise RuntimeError("Failed to get PLC data.") from e
    else:
        return res_data


if __name__ == "__main__":
    # 连接设备获取数据
    data_bcd = create_connect()

    # 解析数据
    parsed_data = parse_struct(data_bcd)

    # 打印解析后的数据
    for key, value in parsed_data.items():
        print(f"{key}: {value}")
