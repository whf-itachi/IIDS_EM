# scheduler.py
import json
import logging

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


class PLCHandler:
    def __init__(self):
        """
        初始化PLC处理类。
        """
        self.plc = None
        self.plcLog = logging.getLogger('plcLog')
        self.taskLog = logging.getLogger('taskLog')
        self.create_connect()

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
            # print("Raw data:", data_bcd)

            # 解析数据并返回
            res_data = self.parse_struct(data_bcd)
            self.plcLog.info(res_data)
        except Exception as e:
            self.plcLog.error(f"Get Plc error: {e}")
            raise RuntimeError("Failed to get PLC data.") from e
        else:
            return res_data

    @staticmethod
    def monitor_error_alarm(binary_list):
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
        redis_client.set("alarm_monitoring_list", new_list_json)
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
        self.taskLog.info(f"快照存储： 快照ID-->{snap_log.id}， 快照内容-->{snap_str}")

        return snap_log.id

    def process_error(self, res_data):
        blade_name = res_data.get("bladeName", '')
        error_list = res_data.get("errorBytes", list())
        # 监控是否有关键错误发生，有进行快照存
        monitor_flag, monitor_changed_list, all_changed_list, all_error_list = self.monitor_error_alarm(error_list)

        self.taskLog.info(f"告警监控: {monitor_flag}, {monitor_changed_list}, {all_changed_list}, {all_error_list}")
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
                        self.taskLog.info(f"告警消息存储:{blade_name},{msg_type},{msg_text},{snap_id}")
                        error = ErrMsg(bladeName=blade_name, msgType=msg_type, msgText=msg_text, snapId=snap_id)
                    else:
                        self.taskLog.info(f"告警消息存储:{blade_name},{msg_type},{msg_text}")
                        error = ErrMsg(bladeName=blade_name, msgType=msg_type, msgText=msg_text)
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

    def get_str_from_redis(self, redis_key):
        redis_data = redis_client.get(redis_key)
        if redis_data:
            return int(redis_data.decode())
        else:
            return redis_data

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

            self.taskLog.info(f"工序: {record['phase']}，总加工时间: {total_hours}")
            res_dic[record['phase']] = total_hours

        return res_dic

    # 对各加工阶段进行判断记录
    def blade_process_stage(self, data):
        """
        判断各阶段并进行记录，判断依据是数据前后变化（由非触发位变为触发位）
        :param data:
        :return:
        """
        self.taskLog.info(f"工序判断记录: {data}")
        now = timezone.now()  # 获取当前时间

        bladeName = data.get("bladeName")  # 叶片名称
        bladeType = data.get("bladeType")  # 叶片类型
        MachineBaseStatus = data.get("MachineBaseStatus")  # 辅助判断
        MWheelStatus = data.get("MWheelStatus")  # 测量轮状态，用以判断上下架
        CutAutoStatus = data.get("CutAutoStatus")  # 切割
        DrillAutoStatus = data.get("DrillAutoStatus")  # 钻孔， 测试孔
        MillAutoStatus = data.get("MillAutoStatus")  # 铣磨

        # 叶片上架下架的判断记录
        old_MWheelStatus = self.get_str_from_redis("MWheelStatus")

        if bool(old_MWheelStatus) != bool(MWheelStatus):
            # 如果数值产生变化，表面状态发生变化需要进行记录
            MWheelStatusByte = format(MWheelStatus, '08b')
            if str(MWheelStatusByte[-1]) == "1":  # Bit 0 测量轮状态， 0 = 未接触叶片， 1 = 已接触叶片
                self.taskLog.info(f"叶片上架: {bladeName}")
                # 上架
                blade_log = BladePhaseLog(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase='上架/下架',
                    startTime=timezone.now()
                )
                # 保存实例到数据库
                blade_log.save()

                # 使用 get_or_create 尝试获取记录，若记录不存在则创建
                BladeRecord.objects.get_or_create(
                    bldname=bladeName,  # 查找条件：根据 bldname 查找记录
                    defaults={'bldtype': bladeType, 'dt': now, 'dtleave': now}  # 如果记录不存在，则使用默认值创建
                )
            else:
                self.taskLog.info(f"叶片下架: {bladeName}")
                # 下架
                latest_log = BladePhaseLog.objects.filter(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase='上架/下架',
                    endTime__isnull=True  # 查找 endTime 为 NULL 的记录
                ).order_by('-startTime').first()

                if latest_log:
                    # 如果找到了满足条件的记录，则更新 endTime
                    latest_log.endTime = timezone.now()
                    latest_log.save()

                    # 查找指定 bldname 的记录
                    blade = BladeRecord.objects.get(bldname=bladeName)
                    now = timezone.now()  # 获取当前时间
                    # 更新 dtleave 字段
                    blade.dtleave = now
                    blade.save()  # 保存更新后的记录

                    res_dict = self.get_blade_phase_statistic(bladeName)
                    # 创建新的统计记录
                    new_record = AllBladePhaseStatistic.objects.create(
                        bladeId=bladeName,
                        bladeType=bladeType,
                        AutoCut=res_dict.get("切割", 0),
                        AutoMill=res_dict.get("铣磨", 0),
                        TestDrill=res_dict.get("测试孔", 0),
                        AutoDrill=res_dict.get("钻孔", 0),
                        AllTime=res_dict.get("上架/下架", 0)
                    )
                    if new_record:
                        self.taskLog.info("叶片下架，创建统计记录成功")
                    else:
                        self.taskLog.info("叶片下架，创建统计记录失败")
                else:
                    self.taskLog.error(f"{bladeName}更新下架时间失败，未查到上架记录!")

            redis_client.set("MWheelStatus", MWheelStatus)

        # 切割工序的判断记录
        old_CutAutoStatus = self.get_str_from_redis("CutAutoStatus")
        if str(old_CutAutoStatus) != str(CutAutoStatus):  # 如果数值产生变化，表面状态发生变化需要进行记录
            # Bit 1 使能状态， 0 = 未使能， 1 = 已使能
            if str(old_CutAutoStatus) == "2":  # 由切割状态改变为非切割状态
                self.taskLog.info(f"叶片{bladeName}进入切割程序")
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
            elif str(CutAutoStatus) == "2":  # 由非切割状态转为切割状态
                self.taskLog.info(f"叶片{bladeName}结束切割程序")
                # 切割开始
                blade_log = BladePhaseLog(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase='切割',
                    startTime=timezone.now()
                )
                # 保存实例到数据库
                blade_log.save()
            else:
                self.taskLog.warning(f"叶片{bladeName}切割程序中的非处理逻辑")
                # 其他的情况暂时不做处理
                pass

            redis_client.set("CutAutoStatus", CutAutoStatus)

        # 铣磨工序的判断记录
        old_MillAutoStatus = self.get_str_from_redis("MillAutoStatus")
        if str(old_MillAutoStatus) != str(MillAutoStatus):  # 状态改变可能需要进行记录
            # Bit 1 使能状态， 0 = 未使能， 1 = 已使能
            if str(MillAutoStatus) == "2":  # 由非铣磨状态进入铣磨状态
                self.taskLog.info(f"叶片{bladeName}进入铣磨程序")
                # 铣磨开始
                blade_log = BladePhaseLog(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase='铣磨',
                    startTime=timezone.now()
                )
                # 保存实例到数据库
                blade_log.save()
            elif str(old_MillAutoStatus) == "2":  # 由铣磨状态退出
                self.taskLog.info(f"叶片{bladeName}结束铣磨程序")
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
            else:
                # 不处理
                self.taskLog.warning(f"叶片{bladeName}铣磨程序中的非处理逻辑")

            redis_client.set("MillAutoStatus", MillAutoStatus)

        # 测试孔以及钻孔工序的判断记录
        old_DrillAutoStatus = self.get_str_from_redis("DrillAutoStatus")
        if str(old_DrillAutoStatus) != str(DrillAutoStatus):
            statusByte = format(MachineBaseStatus, '08b')
            phase = ''
            if str(statusByte[-3]) == "1":  # Bit 3 测试孔位
                phase = "测试孔"
            elif str(statusByte[-6]) == "1":  # 钻孔位
                phase = "钻孔"
            else:
                # 错误状态
                self.taskLog.error(
                    f"钻孔/测试孔 程序错误: DrillAutoStatus={DrillAutoStatus}, MachineBaseStatus={MachineBaseStatus}")

            # Bit 1 使能状态， 0 = 未使能， 1 = 已使能
            if str(DrillAutoStatus) == "2" and phase:  # 由非钻孔到钻孔
                self.taskLog.info(f"叶片{bladeName}进入{phase}程序")
                # 铣磨开始
                blade_log = BladePhaseLog(
                    bladeId=bladeName,
                    bladeType=bladeType,
                    phase=phase,
                    startTime=timezone.now()
                )
                # 保存实例到数据库
                blade_log.save()
            elif str(old_DrillAutoStatus) == "2" and phase:  # 由钻孔到非钻孔位
                self.taskLog.info(f"叶片{bladeName}结束{phase}程序")
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
            else:
                self.taskLog.warning(f"叶片{bladeName}{phase}孔程序中的非处理逻辑")

            redis_client.set("DrillAutoStatus", DrillAutoStatus)

    def obtain_plc_data_regularly(self):
        try:
            # a = time.time()
            a_time = time.perf_counter()

            test = True
            if test:
                # res_data = {'ver': 17, 'plcDt': '2024-12-06T08:17:17.659000', 'userName': 'whf_test',
                #             'errorBytes': [223, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 32, 0, 0, 0, 0, 0, 0, 0,
                #                            64, 1, 0, 8, 0, 65, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                #             'bladeName': 'new_test_blade', 'bladeType': 'TestType', 'bladeLength': 0.0,
                #             'bladeDiameter': 0.0, 'bladeHoles': 0, 'PowerStatus': 0, 'DoorsStatus': 1,
                #             'MachineBaseStatus': 0, 'ModeStatus': 24576,
                #             'MWheelStatus': 0, 'CutProgNum': 1, 'CutProgStep': 1,
                #             'CutAutoStatus': 0, 'MillProgNum': 1, 'MillProgStep': 1,
                #             'MillAutoStatus': 0, 'DrillProgNum': 1, 'DrillProgStep': 1,
                #             'DrillAutoStatus': 0, 'armStatus': 0,
                #             'armPositionTarg': 2.4224246552783113e-41, 'armPositionAct': 0.0,
                #             'armPositionMot': 2.410934007870848e-41, 'armSpeed': -9.111328712252538e-33}
                #

                res_data = {"ver": 17, "plcDt": "2025-02-18T02:36:09.267000", "userName": "",
                            "errorBytes": [0, 123, 0, 0, 0, 0, 0, 0, 5, 0, 0, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                            "bladeName": "", "bladeType": "",
                            "bladeLength": 0.0, "bladeDiameter": 0.0, "bladeHoles": 0, "PowerStatus": 1,
                            "DoorsStatus": 1, "MachineBaseStatus": 127,
                            "ModeStatus": 1, "MWheelStatus": 3, "CutProgNum": 1, "CutProgStep": 1, "CutAutoStatus": 0,
                            "MillProgNum": 1, "MillProgStep": 1,
                            "MillAutoStatus": 0, "DrillProgNum": 1, "DrillProgStep": 1, "DrillAutoStatus": 0,
                            "armStatus": 2, "armPositionTarg": 1.0,
                            "armPositionAct": 2.0429999828338623, "armPositionMot": 2.0429999828338623,
                            "armSpeed": 0.019816609099507332, "cutStatus": 0,
                            "cutFeedTarget": 149.8000030517578, "cutFeedPosition": 150.0, "cutFeedSpeed": 0.0,
                            "cutSpindleSpeed": 0.0, "cutSpindlePower": 0.0,
                            "millStatus": 0, "millFeedTarget": 149.8000030517578, "millFeedPosition": 149.9969940185547,
                            "millFeedSpeed": 0.0,
                            "millSpindleSpeed": 0.0, "millSpindlePower": 0.0, "radial1Status": 0,
                            "radial1FeedTarget": 299.79998779296875,
                            "radial1FeedPosition": 299.9949951171875, "radial1FeedSpeed": 0.0,
                            "radial1SpindleSpeed": 0.0, "radial1SpindlePower": 0.0,
                            "radial2Status": 0, "radial2FeedTarget": 299.79998779296875,
                            "radial2FeedPosition": 299.9949951171875, "radial2FeedSpeed": 0.0,
                            "radial2SpindleSpeed": 0.0, "radial2SpindlePower": 0.0, "axial1Status": 0,
                            "axial1FeedTarget": 79.80000305175781,
                            "axial1FeedPosition": 80.00199890136719, "axial1FeedSpeed": 0.0, "axial1SpindleSpeed": 0.0,
                            "axial1SpindlePower": 0.0,
                            "axial2Status": 0, "axial2FeedTarget": 79.80000305175781,
                            "axial2FeedPosition": 79.98999786376953, "axial2FeedSpeed": 0.0,
                            "axial2SpindleSpeed": 0.0, "axial2SpindlePower": 0.0, "axial3Status": 0,
                            "axial3FeedTarget": 0.0, "axial3FeedPosition": 0.0,
                            "axial3FeedSpeed": 0.0, "axial3SpindleSpeed": 0.0, "axial3SpindlePower": 0.0,
                            "mill2Status": 0, "mill2FeedTarget": 0.0,
                            "mill2FeedPosition": 0.0, "mill2FeedSpeed": 0.0, "machineBaseStatus_1": 0,
                            "machineBaseTarget": -650.0,
                            "machineBasePosition": -650.0, "machineBaseSpeed": 0.0, "clampXStatus": 0,
                            "clampXTarget": 79.80000305175781,
                            "clampXPosition": 60.034000396728516, "clampXSpeed": 0.0, "clampYStatus": 0,
                            "clampYTarget": 79.80000305175781,
                            "clampYPosition": 79.9990005493164, "clampYSpeed": 0.0}
            else:
                res_data = self.get_plc_data()

            # 进行告警错误处理
            error_data = self.process_error(res_data)
            # print(error_data)
            res_data["errorBytes"] = error_data
            data = json.dumps(res_data)
            self.plcLog.info(f"plc data: {data}")
            # print(data, "------------------")
            # data = res_data
            redis_client.set("reportData", data)

            # 还需要对各字段进行变化检查，有变化的要进行判断记录
            self.blade_process_stage(res_data)

            # b = time.time()
            b_time = time.perf_counter()
            self.taskLog.debug(f"定时任务耗时：{b_time - a_time}")
            # print(f"定时任务耗时：{b_time-a_time}")
        except RuntimeError as e:
            self.taskLog.error(f"获取信息出错: {e}")
        else:
            self.taskLog.info(f"else 获取到信息： {res_data}")


# 创建调度器并启动任务
def start_scheduler():
    scheduler = BackgroundScheduler()
    plc_obj = PLCHandler()
    # 添加一个每秒运行一次的任务
    scheduler.add_job(plc_obj.obtain_plc_data_regularly, IntervalTrigger(seconds=1), id='obtain_plc_data_regularly',
                      replace_existing=True, max_instances=1, coalesce=True)

    # 启动调度器
    scheduler.start()
