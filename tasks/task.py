# scheduler.py
import json
import logging
import os
import re

import redis
import snap7
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import time

import numpy as np
from django.utils import timezone
from django.db.models import Sum, F, ExpressionWrapper, DurationField
from snap7 import util

from his.models import DMMSnapLog, ErrMsg, BladePhaseLog, BladeRecord, AllBladePhaseStatistic

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# 需要监控的错误索引位 第一位索引为 1
indices_to_monitor = np.array([5, 26, 27, 28, 30, 32, 33, 34, 35, 37, 38, 39, 40, 42, 43, 44, 45, 48, 49, 50, 52, 53,
                               54, 55, 60, 61, 63, 64, 68, 78, 79, 80, 81, 82, 83, 103, 128, 129, 133, 135, 139,
                               143, 145, 147, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161,
                               162, 163, 165, 167, 169, 178, 179, 180, 188, 189, 190, 191, 192, 193, 194, 195,
                               196, 198, 199, 201, 204, 208, 212, 213])

error_map = {'1': {'id': '1001', 'type': 'Errors'},
             '2': {'id': '1002', 'type': 'Errors'},
             '3': {'id': '1003', 'type': 'Errors'},
             '4': {'id': '1004', 'type': 'Errors'},
             '5': {'id': '1005', 'type': 'Errors'},
             '6': {'id': '1006', 'type': 'Errors'},
             '7': {'id': '1007', 'type': 'Errors'},
             '8': {'id': '1008', 'type': 'Errors'},
             '9': {'id': '1009', 'type': 'Warnings'}, '10': {'id': '1010', 'type': 'Warnings'},
             '11': {'id': '1011', 'type': 'Errors'}, '12': {'id': '1012', 'type': 'Errors'},
             '13': {'id': '1013', 'type': 'Warnings'}, '14': {'id': '1014', 'type': 'Warnings'},
             '15': {'id': '1015', 'type': 'Warnings'}, '16': {'id': '1016', 'type': 'Warnings'},
             '17': {'id': '1017', 'type': 'Warnings'}, '18': {'id': '1018', 'type': 'Warnings'},
             '19': {'id': '1019', 'type': 'Warnings'}, '20': {'id': '1020', 'type': 'Warnings'},
             '21': {'id': '1021', 'type': 'Warnings'}, '22': {'id': '1022', 'type': 'Warnings'},
             '23': {'id': '1023', 'type': 'Warnings'}, '24': {'id': '1024', 'type': 'Warnings'},
             '25': {'id': '1025', 'type': 'Warnings'}, '26': {'id': '1026', 'type': 'Errors'},
             '27': {'id': '1027', 'type': 'Errors'}, '28': {'id': '1028', 'type': 'Errors'},
             '29': {'id': '1029', 'type': 'Errors'}, '30': {'id': '1030', 'type': 'Warnings'},
             '31': {'id': '1031', 'type': 'Errors'}, '32': {'id': '1032', 'type': 'Warnings'},
             '33': {'id': '1033', 'type': 'Errors'}, '34': {'id': '1034', 'type': 'Errors'},
             '35': {'id': '1035', 'type': 'Errors'}, '36': {'id': '1036', 'type': 'Errors'},
             '37': {'id': '1037', 'type': 'Warnings'}, '38': {'id': '1038', 'type': 'Errors'},
             '39': {'id': '1039', 'type': 'Errors'}, '40': {'id': '1040', 'type': 'Errors'},
             '41': {'id': '1041', 'type': 'Errors'}, '42': {'id': '1042', 'type': 'Warnings'},
             '43': {'id': '1043', 'type': 'Errors'}, '44': {'id': '1044', 'type': 'Errors'},
             '45': {'id': '1045', 'type': 'Errors'}, '46': {'id': '1046', 'type': 'Errors'},
             '47': {'id': '1047', 'type': 'Warnings'}, '48': {'id': '1048', 'type': 'Errors'},
             '49': {'id': '1049', 'type': 'Errors'}, '50': {'id': '1050', 'type': 'Errors'},
             '51': {'id': '1051', 'type': 'Errors'}, '52': {'id': '1052', 'type': 'Warnings'},
             '53': {'id': '1053', 'type': 'Errors'}, '54': {'id': '1054', 'type': 'Errors'},
             '55': {'id': '1055', 'type': 'Errors'}, '56': {'id': '1056', 'type': 'Errors'},
             '57': {'id': '1057', 'type': 'Warnings'}, '58': {'id': '1058', 'type': 'Warnings'},
             '59': {'id': '1059', 'type': 'Warnings'}, '60': {'id': '1060', 'type': 'Errors'},
             '61': {'id': '1061', 'type': 'Errors'}, '62': {'id': '1062', 'type': 'Errors'},
             '63': {'id': '1063', 'type': 'Errors'}, '64': {'id': '1064', 'type': 'Errors'},
             '65': {'id': '1065', 'type': 'Errors'}, '66': {'id': '1066', 'type': 'Errors'},
             '67': {'id': '1067', 'type': 'Errors'}, '68': {'id': '1068', 'type': 'Errors'},
             '69': {'id': '1069', 'type': 'Errors'}, '70': {'id': '1070', 'type': 'Errors'},
             '71': {'id': '1071', 'type': 'Errors'}, '72': {'id': '1072', 'type': 'Errors'},
             '73': {'id': '1073', 'type': 'Errors'}, '74': {'id': '1074', 'type': 'Errors'},
             '75': {'id': '1075', 'type': 'Errors'}, '76': {'id': '1076', 'type': 'Errors'},
             '77': {'id': '1077', 'type': 'Errors'}, '78': {'id': '1078', 'type': 'Errors'},
             '79': {'id': '1079', 'type': 'Errors'}, '80': {'id': '1080', 'type': 'Errors'},
             '81': {'id': '1081', 'type': 'Errors'}, '82': {'id': '1082', 'type': 'Errors'},
             '83': {'id': '1083', 'type': 'Errors'}, '84': {'id': '1084', 'type': 'Errors'},
             '85': {'id': '1085', 'type': 'Errors'}, '86': {'id': '1086', 'type': 'Errors'},
             '87': {'id': '1087', 'type': 'Errors'}, '88': {'id': '1088', 'type': 'Errors'},
             '89': {'id': '1089', 'type': 'Errors'}, '90': {'id': '1090', 'type': 'Errors'},
             '91': {'id': '1091', 'type': 'Errors'}, '92': {'id': '1092', 'type': 'Errors'},
             '93': {'id': '1093', 'type': 'Errors'}, '94': {'id': '1094', 'type': 'Errors'},
             '95': {'id': '1095', 'type': 'Errors'}, '96': {'id': '1096', 'type': 'Errors'},
             '97': {'id': '1097', 'type': 'Errors'}, '98': {'id': '1098', 'type': 'Errors'},
             '99': {'id': '1099', 'type': 'Errors'}, '100': {'id': '1100', 'type': 'Errors'},
             '101': {'id': '1101', 'type': 'Warnings'},
             '102': {'id': '1102', 'type': 'Errors'}, '103': {'id': '1103', 'type': 'Errors'},
             '104': {'id': '1104', 'type': 'Errors'}, '105': {'id': '1105', 'type': 'Warnings'},
             '106': {'id': '1106', 'type': 'Warnings'}, '107': {'id': '1107', 'type': 'Errors'},
             '108': {'id': '1108', 'type': 'Errors'}, '109': {'id': '1109', 'type': 'Warnings'},
             '110': {'id': '1110', 'type': 'Warnings'}, '111': {'id': '1111', 'type': 'Warnings'},
             '112': {'id': '1112', 'type': 'Warnings'}, '113': {'id': '1113', 'type': 'Warnings'},
             '114': {'id': '1114', 'type': 'Warnings'}, '115': {'id': '1115', 'type': 'Warnings'},
             '116': {'id': '1116', 'type': 'Warnings'}, '117': {'id': '1117', 'type': 'Warnings'},
             '118': {'id': '1118', 'type': 'Warnings'}, '119': {'id': '1119', 'type': 'Warnings'},
             '120': {'id': '1120', 'type': 'Warnings'}, '121': {'id': '1121', 'type': 'Warnings'},
             '122': {'id': '1122', 'type': 'Warnings'}, '123': {'id': '1123', 'type': 'Warnings'},
             '124': {'id': '1124', 'type': 'Warnings'}, '125': {'id': '1125', 'type': 'Errors'},
             '126': {'id': '1126', 'type': 'Errors'}, '127': {'id': '1127', 'type': 'Errors'},
             '128': {'id': '1128', 'type': 'Warnings'},
             '129': {'id': '1129', 'type': 'Errors'}, '130': {'id': '1130', 'type': 'Errors'},
             '131': {'id': '1131', 'type': 'Errors'}, '132': {'id': '1132', 'type': 'Errors'},
             '133': {'id': '1133', 'type': 'Errors'}, '134': {'id': '1134', 'type': 'Errors'},
             '135': {'id': '1135', 'type': 'Warnings'}, '136': {'id': '1136', 'type': 'Errors'},
             '137': {'id': '1137', 'type': 'Warnings'}, '138': {'id': '1138', 'type': 'Warnings'},
             '139': {'id': '1139', 'type': 'Warnings'}, '140': {'id': '1140', 'type': 'Errors'},
             '141': {'id': '1141', 'type': 'Warnings'}, '142': {'id': '1142', 'type': 'Errors'},
             '143': {'id': '1143', 'type': 'Warnings'}, '144': {'id': '1144', 'type': 'Errors'},
             '145': {'id': '1145', 'type': 'Errors'}, '146': {'id': '1146', 'type': 'Errors'},
             '147': {'id': '1147', 'type': 'Errors'}, '148': {'id': '1148', 'type': 'Errors'},
             '149': {'id': '1149', 'type': 'Errors'}, '150': {'id': '1150', 'type': 'Errors'},
             '151': {'id': '1151', 'type': 'Errors'}, '152': {'id': '1152', 'type': 'Errors'},
             '153': {'id': '1153', 'type': 'Errors'}, '154': {'id': '1154', 'type': 'Errors'},
             '155': {'id': '1155', 'type': 'Errors'}, '156': {'id': '1156', 'type': 'Errors'},
             '157': {'id': '1157', 'type': 'Errors'}, '158': {'id': '1158', 'type': 'Errors'},
             '159': {'id': '1159', 'type': 'Errors'}, '160': {'id': '1160', 'type': 'Errors'},
             '161': {'id': '1161', 'type': 'Errors'}, '162': {'id': '1162', 'type': 'Errors'},
             '163': {'id': '1163', 'type': 'Errors'}, '164': {'id': '1164', 'type': 'Errors'},
             '165': {'id': '1165', 'type': 'Errors'}, '166': {'id': '1166', 'type': 'Errors'},
             '167': {'id': '1167', 'type': 'Errors'}, '168': {'id': '1168', 'type': 'Errors'},
             '169': {'id': '1169', 'type': 'Errors'}, '170': {'id': '1170', 'type': 'Errors'},
             '171': {'id': '1171', 'type': 'Warnings'}, '172': {'id': '1172', 'type': 'Warnings'},
             '173': {'id': '1173', 'type': 'Warnings'}, '174': {'id': '1174', 'type': 'Warnings'},
             '175': {'id': '1175', 'type': 'Errors'}, '176': {'id': '1176', 'type': 'Errors'},
             '177': {'id': '1177', 'type': 'Errors'}, '178': {'id': '1178', 'type': 'Errors'},
             '179': {'id': '1179', 'type': 'Errors'}, '180': {'id': '1180', 'type': 'Errors'},
             '181': {'id': '1181', 'type': 'Errors'}, '182': {'id': '1182', 'type': 'Errors'},
             '183': {'id': '1183', 'type': 'Errors'}, '184': {'id': '1184', 'type': 'Errors'},
             '185': {'id': '1185', 'type': 'Errors'}, '186': {'id': '1186', 'type': 'Errors'},
             '187': {'id': '1187', 'type': 'Errors'}, '188': {'id': '1188', 'type': 'Errors'},
             '189': {'id': '1189', 'type': 'Errors'}, '190': {'id': '1190', 'type': 'Errors'},
             '191': {'id': '1191', 'type': 'Errors'}, '192': {'id': '1192', 'type': 'Errors'},
             '193': {'id': '1193', 'type': 'Errors'}, '194': {'id': '1194', 'type': 'Errors'},
             '195': {'id': '1195', 'type': 'Errors'}, '196': {'id': '1196', 'type': 'Errors'},
             '197': {'id': '1197', 'type': 'Errors'}, '198': {'id': '1198', 'type': 'Errors'},
             '199': {'id': '1199', 'type': 'Errors'}, '200': {'id': '1200', 'type': 'Errors'},
             '201': {'id': '1201', 'type': 'Errors'}, '202': {'id': '1202', 'type': 'Errors'},
             '203': {'id': '1203', 'type': 'Warnings'}, '204': {'id': '1204', 'type': 'Errors'},
             '205': {'id': '1205', 'type': 'Errors'}, '206': {'id': '1206', 'type': 'Warnings'},
             '207': {'id': '1207', 'type': 'Errors'}, '208': {'id': '1208', 'type': 'Errors'},
             '209': {'id': '1209', 'type': 'Errors'}, '210': {'id': '1210', 'type': 'Warnings'},
             '211': {'id': '1211', 'type': 'Errors'}, '212': {'id': '1212', 'type': 'Errors'},
             '213': {'id': '1213', 'type': 'Errors'}, '214': {'id': '1214', 'type': 'Errors'}}


# ---------------------------- 测试用 ----------------------------------
_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'plc.log')
_json_re = re.compile(r'plc data:\s*({.+})')

def _line_generator(path):
    """无限循环：文件读完一轮后，一直重复最后一行。"""
    last_line = ''                       # 缓存最后一行
    while True:                          # 外层循环：文件重新打开
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:               # 正常逐行读
                last_line = line
                print(f"读取plcLog日志：{len(line)}")
                yield line

        # 文件已读完，进入“复读”模式
        print("日志文件已读到末尾，开始重复最后一行")
        while True:
            print(f"【重复】读取plcLog日志：{len(last_line)}")
            time.sleep(1)
            yield last_line

_line_iter = _line_generator(_log_path)

def next_plc_json():
    """每次调用返回一行日志里 plc data 的 dict"""
    while True:
        line = next(_line_iter)
        m = _json_re.search(line)
        if m:
            return json.loads(m.group(1))
# ---------------------------- 测试用 ----------------------------------

class PLCHandler:
    def __init__(self):
        """
        初始化PLC处理类。
        """
        self.plc = None
        self.plcLog = logging.getLogger('plcLog')
        self.taskLog = logging.getLogger('taskLog')
        self.create_connect()

        self.blade_name = None
        self.blade_type = None
        self.blade_id = None

        self.m_wheel_second_bit = 0
        self.cut_second_bit = 0
        self.drill_second_bit = 0
        self.mill_second_bit = 0

    def create_connect(self):
        try:
            # PLC客户端实例
            self.plc = snap7.client.Client()
            # 连接到PLC
            self.plc.connect('192.168.1.1', 0, 1)  # PLC的IP地址、机架号和槽号
            # 检查连接是否成功
            if self.plc.get_connected():
                self.plcLog.info("Connect to PLC")
            else:
                self.plcLog.info("Failed to connect to PLC")
                # raise ConnectionError("Failed to connect to PLC.")
        except Exception as e:
            self.plcLog.error(f"snap7连接plc失败，报错:{e}")

    # 解析数据
    @staticmethod
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
        res_data['PowerStatus'] = util.get_byte(data[idx:idx + 1], 0)

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

    def get_plc_data(self):
        try:
            # 读取数据块 DB160，偏移量为0，长度为356字节
            data_bcd = self.plc.db_read(160, 0, 358)
            # 解析数据并返回
            res_data = self.parse_struct(data_bcd)
        except Exception as e:
            self.plcLog.error(f"Get Plc error: {e}")
            raise RuntimeError("Failed to get PLC data.") from e
        else:
            return res_data

    # 转换为二进制并获取第二个比特位（索引为1）
    @staticmethod
    def get_second_bit(value, flag=""):
        # 转为8位二进制字符串，取倒数第2位（第二个比特位）
        binary_str = format(value, '08b')  # 确保8位，如3→'00000011'
        if flag == "MWheelStatus":
            return binary_str[-1]  # 上下架用第一个比特位（索引1）
        else:
            return binary_str[-2]  # 第二个比特位（索引1）

    @staticmethod
    def monitor_error_alarm(binary_list):
        """
        监控告警类是否有变化:np.any(changed)
        监控告警类变化列表：monitor_changed_list.tolist()
        所有告警类变化列表：all_changed_list.tolist()
        所有告警信息列表：all_errors.tolist()
        """

        # 得到最新的二进制数组数据
        binary_representation = [format(byte, '08b')[::-1] for byte in binary_list]
        binary_list = np.array(binary_representation)
        binary_list = np.array([int(bit) for binary in binary_list for bit in binary])
        all_errors = np.where(binary_list == 1)[0]
        if len(binary_list) == 0:
            binary_list = np.array([0 for i in range(320)])
        # 得到之前的二进制数组数据
        old_list_json = redis_client.get("alarm_monitoring_list")
        if not old_list_json:
            old_list = np.array([0 for i in range(320)])
        else:
            binary_list_as_list = json.loads(old_list_json)
            if not binary_list_as_list:
                old_list = np.array([0 for i in range(320)])
            else:
                old_list = np.array(binary_list_as_list, dtype=int)

        # 更新redis中的缓存
        new_list_json = json.dumps(binary_list.tolist())
        redis_client.set("alarm_monitoring_list", new_list_json, ex=3600*24*3)  # 3天后过期
        all_changed = (old_list == 0) & (binary_list == 1)
        all_changed_list = np.where(all_changed)[0]

        current_state = binary_list[indices_to_monitor]
        previous_state = old_list[indices_to_monitor]

        changed = (previous_state == 0) & (current_state == 1)
        monitor_changed_list = indices_to_monitor[changed]

        # 输出变化
        return np.any(changed), monitor_changed_list.tolist(), all_changed_list.tolist(), all_errors.tolist()

    # 存储快照函数
    def monitor_record_snap(self, res_data):
        # 将data以json字符串的形式存入数据库中
        snap_str = json.dumps(res_data)
        snap_log = DMMSnapLog(snapStr=snap_str)

        # 保存数据
        snap_log.save()
        self.taskLog.info(f"快照存储： 快照ID-->{snap_log.id}")

        return snap_log.id

    def process_error(self, res_data):
        error_list = res_data.get("errorBytes", list())
        # 监控是否有关键错误发生，有进行快照存
        monitor_flag, monitor_changed_list, all_changed_list, all_error_list = self.monitor_error_alarm(error_list)

        if monitor_flag:
            snap_id = self.monitor_record_snap(res_data)
        else:
            snap_id = None

        # 遍历每个数字
        for num in all_changed_list:
            # 错误位对应的错误信息
            try:
                # error_message = error_map[str(num)]
                error_message = error_map.get(str(num))  # 比特位从 1 开始
                if error_message:
                    msg_type = error_message.get("type", "")
                    msg_text = error_message.get("id", "")

                    # 不仅是比特位为1 而且是由0变为1，进行日志存储
                    if num in monitor_changed_list:
                        self.taskLog.info(f"告警消息存储:{self.blade_name},{msg_type},{msg_text},{snap_id}")
                        error = ErrMsg(bladeName=self.blade_name, msgType=msg_type, msgText=msg_text, snapId=snap_id)
                    else:
                        self.taskLog.info(f"告警消息存储:{self.blade_name},{msg_type},{msg_text}")
                        error = ErrMsg(bladeName=self.blade_name, msgType=msg_type, msgText=msg_text)
                    error.save()  # Saves to the database
            except Exception as e:
                self.taskLog.error(f"process_error 发生错误: {e}")
                continue

        res_list = list()
        for i in all_error_list:
            error_map_data = error_map.get(str(i + 1))
            if error_map_data:
                res_list.append(error_map_data)
        return res_list

    # 执行各工序加工时间的统计
    def get_blade_phase_statistic(self, bladeName):
        # 查询该叶片的所有记录，排除 endTime 为 null 的记录
        logs = BladePhaseLog.objects.filter(bladeId=bladeName).exclude(endTime__isnull=True)

        # 计算每条记录的加工时间，使用 endTime - startTime
        logs = logs.annotate(
            processing_time=ExpressionWrapper(
                F('endTime') - F('startTime'),
                output_field=DurationField()
            )
        )

        # 按工序（phase）进行分组，统计每个工序的总加工时间
        result = logs.values('phase').annotate(total_processing_time=Sum('processing_time'))
        res_dic = dict()
        # 输出每个工序的总加工时间
        for record in result:
            # 获取总加工时间（秒）
            total_seconds = record['total_processing_time'].total_seconds()
            # 转换为小时
            total_hours = total_seconds / 3600

            if total_hours.is_integer():
                total_hours = int(total_hours)  # 如果是整数，转为整数
            else:
                total_hours = round(total_hours, 2)  # 如果有小数，保留两位小数

            self.taskLog.info(f"工序: {record['phase']}，总加工时间: {total_hours} 小时")
            res_dic[record['phase']] = total_hours

        return res_dic

    # 下架处理
    def leave_shelves(self, force_log=False):
        if force_log:
            self.taskLog.warning(f"工序-叶片强制下架: {self.blade_name}")
        else:
            self.taskLog.info(f"工序-叶片下架: {self.blade_name}")

        try:
            # 下架
            latest_log = BladePhaseLog.objects.filter(
                bladeId=self.blade_name,
                # bladeType=self.blade_type,
                phase='上架/下架',
                endTime__isnull=True  # 查找 endTime 为 NULL 的记录
            ).order_by('id').first()
            # print(latest_log, "is latest log", self.blade_name, self.blade_type)
            if latest_log:
                # 如果找到了满足条件的记录，则更新 endTime
                latest_log.endTime = timezone.now()
                latest_log.save()

                # 查找指定 bldname 的记录
                blade = BladeRecord.objects.get(bldname=self.blade_name)
                now = timezone.now()  # 获取当前时间

                if blade.dtleave is None:
                    blade.dtleave = now
                    blade.save()

                res_dict = self.get_blade_phase_statistic(self.blade_name)
                # 定义查询条件（根据 bladeId 判定记录是否存在）
                # defaults = {
                #     'bladeType': self.blade_type,
                #     'AutoCut': res_dict.get("切割", 0),
                #     'AutoMill': res_dict.get("铣磨", 0),
                #     'TestDrill': res_dict.get("测试孔", 0),
                #     'AutoDrill': res_dict.get("钻孔", 0),
                #     'AllTime': res_dict.get("上架/下架", 0)
                # }
                cut = res_dict.get("切割", 0)
                mill = res_dict.get("铣磨", 0)
                test = res_dict.get("测试孔", 0)
                drill = res_dict.get("钻孔", 0)

                defaults = {
                    'bladeType': self.blade_type,
                    'AutoCut': cut,
                    'AutoMill': mill,
                    'TestDrill': test,
                    'AutoDrill': drill,
                    'AllTime': cut + mill + test + drill,  # 四道工序合计
                }

                # 执行 update_or_create：存在则更新，不存在则创建
                record, created = AllBladePhaseStatistic.objects.update_or_create(
                    bladeId=self.blade_name,  # 查询条件：根据 bladeId 查找记录
                    defaults=defaults  # 要更新或创建的字段值
                )

                if created:
                    self.taskLog.info("叶片下架，创建统计记录成功")
                else:
                    self.taskLog.info("叶片下架，更新统计记录成功")
            else:
                self.taskLog.error(f"{self.blade_name}更新下架时间失败，未查到上架记录!")
        except Exception as e:
            self.taskLog.error(f"叶片下架处理报错: {e}")
        finally:
            self.m_wheel_second_bit = 0
            self.cut_second_bit = 0
            self.drill_second_bit = 0
            self.mill_second_bit = 0
            self.blade_name = None
            self.blade_type = None

    def log_if_changed(self, prev_vals, curr_vals):
        """
        当任意值发生变化时记录日志
        :param prev_vals: 上一次的值列表（如 [self.m_wheel_second_bit, ...]）
        :param curr_vals: 当前的新值列表（如 [m_wheel_second_bit, ...]）
        """
        # 检查是否有任意值变化
        if any(str(p) != str(c) for p, c in zip(prev_vals, curr_vals)):
            # 构建日志内容
            prev_str = " - ".join(map(str, prev_vals))
            curr_str = " - ".join(map(str, curr_vals))
            self.taskLog.info(f"上一次数据: {prev_str}")
            self.taskLog.info(f"现在数据: {curr_str}")

    # 对各加工阶段进行判断记录
    def blade_process_stage(self, data):
        """
        判断各阶段并进行记录，判断依据是数据前后变化（由非触发位变为触发位）
        :param data:
        :return:
        """

        now = timezone.now()  # 获取当前时间

        bladeName = data.get("bladeName")  # 叶片名称
        bladeType = data.get("bladeType")  # 叶片类型

        MachineBaseStatus = data.get("MachineBaseStatus", 0)  # 辅助判断
        MWheelStatus = data.get("MWheelStatus", 0)  # 测量轮状态，用以判断上下架
        CutAutoStatus = data.get("CutAutoStatus", 0)  # 切割
        DrillAutoStatus = data.get("DrillAutoStatus", 0)  # 钻孔， 测试孔
        MillAutoStatus = data.get("MillAutoStatus", 0)  # 铣磨

        # 获取各状态的第二个比特位
        # m_base_second_bit = self.get_second_bit(MachineBaseStatus)
        m_wheel_second_bit = self.get_second_bit(MWheelStatus, flag="MWheelStatus")
        cut_second_bit = self.get_second_bit(CutAutoStatus)
        drill_second_bit = self.get_second_bit(DrillAutoStatus)
        mill_second_bit = self.get_second_bit(MillAutoStatus)

        # 上一次的值列表
        prev_vals = [self.m_wheel_second_bit, self.cut_second_bit, self.drill_second_bit, self.mill_second_bit]
        # 当前的新值列表
        curr_vals = [m_wheel_second_bit, cut_second_bit, drill_second_bit, mill_second_bit]
        # 调用方法，只有变化时才记录
        self.log_if_changed(prev_vals, curr_vals)
        
        # 叶片上架下架的判断记录
        if self.m_wheel_second_bit != m_wheel_second_bit:
            self.taskLog.info(f"判断上下架: {self.m_wheel_second_bit} - {m_wheel_second_bit}")
            if str(m_wheel_second_bit) == "1":  # Bit 0 测量轮状态， 0 = 未接触叶片， 1 = 已接触叶片
                if bladeName and (bladeName != self.blade_name):
                    if self.blade_name:
                        self.leave_shelves(force_log=True)

                    self.taskLog.info(f"新叶片进入加工工序: {bladeName}")
                    self.blade_name = bladeName
                    self.blade_type = bladeType

                self.taskLog.info(f"工序-叶片上架: {bladeName}")
                # 上架
                # 检查是否存在未结束的日志记录（endTime为空）
                has_unfinished_log = BladePhaseLog.objects.filter(
                    bladeId=bladeName,
                    # bladeType=bladeType,
                    phase='上架/下架',
                    endTime__isnull=True  # 关键条件：endTime为空表示未结束
                ).exists()

                if has_unfinished_log:
                    # 存在未结束的记录，不创建新日志
                    self.taskLog.info(f"叶片 {bladeName} 存在未结束的上架日志，不创建新记录")
                else:
                    # 不存在未结束的记录（或所有记录已结束），创建新日志
                    blade_log = BladePhaseLog(
                        bladeId=bladeName,
                        bladeType=bladeType,
                        phase='上架/下架',
                        startTime=timezone.now()
                    )
                    blade_log.save()
                    self.taskLog.info(f"叶片 {bladeName} 上架日志创建成功")

                # 使用 get_or_create 尝试获取记录，若记录不存在则创建
                BladeRecord.objects.get_or_create(
                    bldname=bladeName,  # 查找条件：根据 bldname 查找记录
                    defaults={'bldtype': bladeType, 'dt': now, 'dtleave': now}  # 如果记录不存在，则使用默认值创建
                )
            else:
                self.taskLog.info(f"叶片下架: {bladeName}")
                self.leave_shelves()

            self.m_wheel_second_bit = m_wheel_second_bit
        self.blade_name = bladeName
        self.blade_type = bladeType
        # 切割工序的判断记录
        if str(self.cut_second_bit) != str(cut_second_bit):  # 如果数值产生变化，表面状态发生变化需要进行记录
            self.taskLog.info(f"判断切割: {self.cut_second_bit} - {cut_second_bit}")

            # Bit 1 使能状态， 0 = 未使能， 1 = 已使能
            if str(cut_second_bit) == "1":  # 由切割状态改变为非切割状态
                self.taskLog.info(f"工序-叶片{bladeName}进入切割程序")
                # 切割开始
                blade_log = BladePhaseLog(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase='切割',
                    startTime=timezone.now()
                )
                # 保存实例到数据库
                blade_log.save()
            else :  # 由非切割状态转为切割状态
                self.taskLog.info(f"工序-叶片{bladeName}结束切割程序")
                # 切割结束
                latest_log = BladePhaseLog.objects.filter(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase='切割',
                    endTime__isnull=True  # 查找 endTime 为 NULL 的记录
                ).order_by('-startTime').first()

                if latest_log:
                    # 如果找到了满足条件的记录，则更新 endTime
                    latest_log.endTime = timezone.now()
                    latest_log.save()
                else:
                    self.taskLog.error(f"{bladeName}更新切割结束时间失败，未查到正在进行的切割记录!")

            # else:
            #     self.taskLog.warning(f"叶片{bladeName}切割程序中的非处理逻辑")

            self.cut_second_bit = cut_second_bit

        # 铣磨工序的判断记录
        if str(self.mill_second_bit) != str(mill_second_bit):  # 状态改变可能需要进行记录
            self.taskLog.info(f"判断铣磨: {self.mill_second_bit} - {mill_second_bit}")

            # Bit 1 使能状态， 0 = 未使能， 1 = 已使能
            if str(mill_second_bit) == "1":  # 由非铣磨状态进入铣磨状态
                self.taskLog.info(f"工序-叶片{bladeName}进入铣磨程序")
                # 铣磨开始
                blade_log = BladePhaseLog(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase='铣磨',
                    startTime=timezone.now()
                )
                # 保存实例到数据库
                blade_log.save()
            else:  # 由铣磨状态退出
                self.taskLog.info(f"工序-叶片{bladeName}结束铣磨程序")
                # 铣磨结束
                latest_log = BladePhaseLog.objects.filter(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase='铣磨',
                    endTime__isnull=True  # 查找 endTime 为 NULL 的记录
                ).order_by('-startTime').first()

                if latest_log:
                    # 如果找到了满足条件的记录，则更新 endTime
                    latest_log.endTime = timezone.now()
                    latest_log.save()
                else:
                    self.taskLog.error(f"{bladeName}更新铣磨结束时间失败，未查到正在进行的铣磨记录!")
            # else:
            #     # 不处理
            #     self.taskLog.warning(f"叶片{bladeName}铣磨程序中的非处理逻辑")
            self.mill_second_bit = mill_second_bit

        # 测试孔以及钻孔工序的判断记录
        if str(self.drill_second_bit) != str(drill_second_bit):
            self.taskLog.info(f"判断测试孔以及钻孔: {self.drill_second_bit} - {drill_second_bit}")
            statusByte = format(MachineBaseStatus, '08b')
            self.taskLog.info(f"测试孔以及钻孔状态: {str(statusByte[-4])} - {str(statusByte[-7])}")
            # if str(statusByte[-4]) == "1":  # Bit 3 测试孔位
            if str(statusByte[-7]) == "1":  # 钻孔位
                phase = "钻孔"
            else:
                phase = "测试孔"

            # Bit 1 使能状态， 0 = 未使能， 1 = 已使能
            if str(drill_second_bit) == "1":  # 由非钻孔到钻孔
                self.taskLog.info(f"工序-叶片{bladeName}进入{phase}程序")
                # 铣磨开始
                blade_log = BladePhaseLog(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase=phase,
                    startTime=timezone.now()
                )
                # 保存实例到数据库
                blade_log.save()
            else:  # 由钻孔到非钻孔位
                self.taskLog.info(f"工序-叶片{bladeName}结束{phase}程序")
                # 铣磨结束
                latest_log = BladePhaseLog.objects.filter(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase=phase,
                    endTime__isnull=True  # 查找 endTime 为 NULL 的记录
                ).order_by('-startTime').first()

                if latest_log:
                    # 如果找到了满足条件的记录，则更新 endTime
                    latest_log.endTime = timezone.now()
                    latest_log.save()
                else:
                    self.taskLog.error(f"{bladeName}更新{phase}结束时间失败，未查到正在进行的{phase}记录!")
            # else:
            #     self.taskLog.warning(f"叶片{bladeName}{phase}孔程序中的非处理逻辑")
            self.drill_second_bit = drill_second_bit

    @staticmethod
    def _json_errors_to_raw_bytes(err_list):
        """
        将 [{'id':'1008','type':'Errors'}, ...] 还原成 40 个 byte 的列表
        规则：id 去掉前缀 '1' 后得到位号（1~214），对应 bit 置 1
        """
        bits = [0] * 320  # 40*8 = 320 bit
        for item in err_list:
            bit_id = int(item['id'])  # 1008
            bit_idx = bit_id - 1000  # 8
            if 1 <= bit_idx <= 214:
                bits[bit_idx - 1] = 1  # 转成 0-base

        # 每 8 位拼成一个 byte（小端，与 PLC 侧一致）
        bytes_40 = []
        for byte_n in range(40):
            byte_val = 0
            for bit_in_byte in range(8):
                if bits[byte_n * 8 + bit_in_byte]:
                    byte_val |= (1 << bit_in_byte)
            bytes_40.append(byte_val)
        return bytes_40

    def obtain_plc_data_regularly(self):
        try:
            # a = time.time()
            a_time = time.perf_counter()

            test = False
            if test:
                res_data = next_plc_json()
                res_data['errorBytes'] = self._json_errors_to_raw_bytes(res_data['errorBytes'])
            else:
                res_data = self.get_plc_data()

            # 还需要对各字段进行变化检查，有变化的要进行判断记录
            self.blade_process_stage(res_data)

            # 进行告警错误处理
            error_data = self.process_error(res_data)
            res_data["errorBytes"] = error_data
            data = json.dumps(res_data)
            self.plcLog.info(f"plc data: {data}")
            redis_client.set("reportData", data)

            # b = time.time()
            b_time = time.perf_counter()
            self.taskLog.debug(f"定时任务耗时：{b_time - a_time}")
            # print(f"定时任务耗时：{b_time-a_time}")
        except RuntimeError as e:
            self.taskLog.error(f"获取信息出错: {e}")


# 创建调度器并启动任务
def start_scheduler():
    scheduler = BackgroundScheduler()
    plc_obj = PLCHandler()
    # 添加一个每秒运行一次的任务
    scheduler.add_job(plc_obj.obtain_plc_data_regularly, IntervalTrigger(seconds=1), id='obtain_plc_data_regularly',
                      replace_existing=True, max_instances=1, coalesce=True)

    # 启动调度器
    scheduler.start()

