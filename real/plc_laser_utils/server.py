#!/usr/bin/python
# -*- coding: UTF-8 -*-
"""
plc和激光设备连接并获取和分析数据
"""
import csv
import json
import logging
import time
import threading
import traceback

import numpy as np
import redis

from opcua import Client, ua

from data_analysis.new_flatness_analysis.flatness_holes_1 import LaserDataProcessor
from .SR7LinkLib import *

LASER_IP = (192, 168, 1, 41)

LASER_ID = 0
LASER_WIDTH = 160.0
LASER_POINT_DISTANCE = 2.0      # 点激光的间距

z_offset = 300.0
X_Range = np.arange(-160.0 + 0.1/2.0, 160.0, 0.1)
Start_index, End_index = 1600 - int(LASER_WIDTH / 2 / 0.1) , 1600 + int(LASER_WIDTH / 2 / 0.1)
Space =int(LASER_POINT_DISTANCE / 0.1)

# plc config
PLCUA_IP = '192.168.1.1'
PLCUA_PORT = '4840'


laserLog = logging.getLogger('laserLog')


class PlcLaserServer:
    def __init__(self):
        self.MIN_Z = 0  # z值最小值
        self.MAX_Z = 0  # z值最大值
        self.original_ctl = 0
        self.time_interval = 3  # 默认3秒间隔
        self.cli = None
        self.plc_dict = dict()
        self.r = redis.StrictRedis(host='localhost', port=6379, db=1)  # redis实例
        # 在实例化时自动尝试连接
        self.plc_connect()

    # plc连接函数
    def plc_connect(self):
        try:
            self.cli = Client("opc.tcp://{}:{}".format(PLCUA_IP, PLCUA_PORT))
            self.cli.session_timeout = 30000
            self.cli.connect()
        except Exception as e:
            laserLog.error(f"plc_laser Error connecting to PLC:{e}")
            # raise ERROR('error connect plc')  # todo：这里抛出异常后需要退出或者重试连接操作


    # plc获取数据
    def plc_get_data(self):
        try:
            act_pos = self.cli.get_node('ns=3;s="IDB_Arm"."Act_Postion"')
            act_pos_motor = self.cli.get_node('ns=3;s="IDB_Arm"."Act_Position_Motor"')
            scanner_ctrl = self.cli.get_node('ns=3;s="GDB_Scanner"."ScannerCtrl"')

            self.plc_dict["ScannerCtl"] = scanner_ctrl.get_value()
            self.plc_dict["act_pos"] = act_pos.get_value()
            self.plc_dict["act_pos_motor"] = act_pos_motor.get_value()

        except Exception as e:
            laserLog.error(f"获取plc数据失败: {e}")


    # plc断开连接
    def plc_disconnect(self):
        if self.cli:
            self.cli.disconnect()


    # 连接激光设备
    @staticmethod  # 静态方法，不需要访问类实例
    def connect_laser():
        try:
            rc = SR7IF_EthernetOpen(LASER_ID, LASER_IP)
            if rc != SR7IF_RETURN_CODE.OK:
                # raise Exception(f"Error: Open failed, return value is: {rc}")
                return False
            else:
                SR7IF_SetSetting_Batch(LASER_ID, 0x0)
                return True
        except Exception as e:
            laserLog.error(f"plc_laser Error connecting to Laser:{e}")
            return False


    # 断开激光设备
    @staticmethod
    def disconnect_laser():
        try:
            rc = SR7IF_SetSetting_Batch(LASER_ID, 0x1)
            if rc != SR7IF_RETURN_CODE.OK:
                laserLog.error(f"断开激光设备失败，rc={rc}")
                # raise Exception(f"Error: Batch Setting, return value is: {rc}")
                return False
            else:
                SR7IF_CommClose(LASER_ID)
                laserLog.info(f"断开激光设备成功，rc={rc}")
                return True
        except Exception as e:
            laserLog.error(f"plc_laser Error disconnecting to Laser:{e}")
            return False


    # 获取激光设备的数据
    @staticmethod
    def get_actual_profile():
        try:
            data_size = SR7IF_ProfileDataWidth(LASER_ID)
            rc, profile_data, encoder_data = SR7IF_GetSingleProfile(LASER_ID, data_size, 1)

            # 转换为 NumPy 数组以便处理
            if rc == SR7IF_RETURN_CODE.OK and profile_data:
                profile_data_array = np.frombuffer(profile_data, dtype=np.int32)  # 转为 NumPy 数组
                return rc, profile_data_array
            else:
                laserLog.error(f"Error fetching profile data, return code: {rc}")
                return rc, None
        except Exception as e:
            laserLog.error(f"Error fetching Laser data:{e}")
            return None, None


    # 将获取的数据进行平滑处理
    @staticmethod
    def convert_profile_2_values(profile_data):
        try:
            z = np.frombuffer(profile_data, dtype=np.int32).astype(np.float64)
            z = (z[Start_index - 1: End_index] + z[Start_index: End_index + 1]) / 2.0
            # z = z_offset - z[::Space] * Z_RESOLUTION
            z = z_offset - z[::] * Z_RESOLUTION

            return z.tolist()
        except Exception as e:
            laserLog.error(f"Error converting profile data:{e}")
            return []



    # 将获取到数据直接写入csv文件
    @staticmethod
    def write_to_csv(data, filename="new_laser_data.csv"):
        try:
            with open(filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(data)
        except Exception as e:
            laserLog.error(f"Error writing to CSV:{e}")


    # 将激光数据和PLC数据写入 Redis
    def write_to_redis(self,laser_data):
        try:
            # 转换激光数据为列表
            if isinstance(laser_data, np.ndarray):
                laser_data = laser_data.tolist()
            elif isinstance(laser_data, (list, tuple)):
                # 是列表
                laser_data = list(laser_data)  # 确保为列表
            elif isinstance(laser_data, (bytes, bytearray)):
                laser_data = np.frombuffer(laser_data, dtype=np.int32).tolist()
            else:
                raise ValueError(f"Unsupported data type for 'data': {type(laser_data)}")

            timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
            # print(laser_data, type(laser_data))

            scan_data = {
                "timestamp": timestamp,
                "ScannerCtl": self.plc_dict.get("ScannerCtl"),
                "act_pos": self.plc_dict.get("act_pos"),
                "act_pos_motor": self.plc_dict.get("act_pos_motor"),
                "laser_data": laser_data
            }

            # 将数据转换为 JSON 字符串
            scan_data_json = json.dumps(scan_data)

            # 将扫描数据存入 Redis 列表（假设列表名为 'scan_data'）
            self.r.rpush('scan_data', scan_data_json)
        except Exception as e:
            laserLog.error(f"Error writing to Redis:{e}")


    # 程序结束后将redis中的数据写入csv文件
    def write_from_redis_to_csv(self):
        laserLog.info("开始从redis中读取数据到csv文件")
        csv_path = os.path.join(BASE_DIR, "data_analysis", 'hole_calculate', "laser_data.csv")
        try:
            with open(csv_path, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(["timestamp", "ScannerCtl", "act_pos", "act_pos_motor", "laser_data"])

                while True:
                    data = self.r.lpop('scan_data')
                    if data:
                        # 将 bytes 数据转换为字符串
                        data_str = data.decode('utf-8')

                        # 如果数据是 JSON 格式，使用 json.loads 将字符串转换为 Python 对象
                        # 你也可以选择使用 eval()，但 eval 在处理不信任的输入时有安全风险
                        data_dict = json.loads(data_str)

                        # 将数据写入 CSV 文件
                        writer.writerow([data_dict.get("timestamp", ''),
                                         data_dict.get("ScannerCtl", ''),
                                         data_dict.get("act_pos", ''),
                                         data_dict.get("act_pos_motor", ''),
                                         data_dict.get("laser_data", '')])
                    else:
                        break

            processor = LaserDataProcessor(csv_path, radius=1400, in_angle=31.09)
            processor.run(num_holes=250, start_angle=100)
        except Exception as e:
            laserLog.error(f"Error reading from Redis or writing to CSV:{e}")


    # 连接激光设备后需要执行的逻辑
    def after_connect_laser(self):
        try:
            laserLog.info("扫描准备开始，连接激光设备")
            # 扫描准备开始，连接激光设备
            laser_flag = self.connect_laser()
            cli_node = self.cli.get_node('ns=3;s="GDB_Scanner"."ScannerStatus"')
            if laser_flag:
                # 记录连接状态为1
                cli_node.set_value(ua.DataValue(ua.Variant(1, ua.VariantType.Int16)))
                laserLog.info("连接激光设备成功，设置ScannerStatus为1")
                self.time_interval = 0.1  # 200毫秒读取一次数据
            else:
                # 连接失败写入状态0
                cli_node.set_value(ua.DataValue(ua.Variant(0, ua.VariantType.Int16)))
                # 写入错误日志，连接激光设备失败
                laserLog.info("连接激光设备失败，设置ScannerStatus为0")
        except Exception as e:
            laserLog.error(f"连接激光设备后执行程序出错:{e}")


    # 激光设备运行中需要处理的逻辑
    def running_laser(self):
        try:
            # 激光设备运行中，做数据处理
            rc, profile_data = self.get_actual_profile()
            print("持续运行 时间:", time.time(), np.max(profile_data), np.min(profile_data))
            # 平滑处理
            profile_data = self.convert_profile_2_values(profile_data)
            if profile_data:
                # 过滤 profile_data，仅保留在 [140, 500] 范围内的值
                # filtered_data = profile_data[(profile_data >= 100) & (profile_data <= 600)]
                filtered_data = [i for i in profile_data if 100<=i<=600]

                if np.max(filtered_data) > self.MAX_Z:
                    # laserLog.info("最大值变动，最新值为：", np.max(profile_data))
                    MAX_Z = np.max(filtered_data)
                    max_node = self.cli.get_node('ns=3;s="GDB_Scanner"."MaxValue"')
                    max_node.set_value(ua.DataValue(ua.Variant(MAX_Z, ua.VariantType.Float)))

                if np.min(filtered_data) < self.MIN_Z:
                    # laserLog.info("最小值变动，最新值为：", np.min(profile_data))
                    MIN_Z = np.min(filtered_data)
                    max_node = self.cli.get_node('ns=3;s="GDB_Scanner"."MinValue"')
                    max_node.set_value(ua.DataValue(ua.Variant(MIN_Z, ua.VariantType.Float)))
            try:
                # 数据存入redis中
                self.write_to_redis(profile_data)
            except Exception as e:
                laserLog.error(f"存入数据报错:{e}")

        except Exception as e:
            laserLog.error(f"激光设备运行报错:{e}")


    # 关闭激光设备后需要执行的逻辑
    def after_disconnect_laser(self):
        try:
            # 重置最大最小值
            self.MIN_Z = 0  # z值最小值
            self.MAX_Z = 0  # z值最大值

            laserLog.info("描结束，断开激光设备")
            # 扫描结束，断开激光设备
            disconnect_flag = self.disconnect_laser()
            if disconnect_flag:
                cli_node = self.cli.get_node('ns=3;s="GDB_Scanner"."ScannerStatus"')
                cli_node.set_value(ua.DataValue(ua.Variant(0, ua.VariantType.Int16)))
                laserLog.info("设置ScannerStatus为0")
            else:
                # 记录断开激光设备失败
                laserLog.error("断开激光设备失败")
            # 扫描结束后的处理
            self.write_from_redis_to_csv()
            self.time_interval = 5
            # # 获取完数据后清空redis
            # self.r.delete('scan_data')
        except Exception as e:
            laserLog.error(f"关闭激光设备后执行程序报错:{e}")

    # 运行入口
    def runserver(self):
        self.original_ctl = 0  # 初始运行状态从0开始
        # plc需要一直运行
        while True:
            time.sleep(self.time_interval)
            try:
                # 获取plc数据
                self.plc_get_data()
                scanner_ctl = self.plc_dict.get("ScannerCtl")
                if self.original_ctl and scanner_ctl == 0:  # 由 1或11 变 0
                    self.after_disconnect_laser()
                elif scanner_ctl == 1 and self.original_ctl == 0:  # 由 0 变 1
                    self.after_connect_laser()
                elif self.original_ctl and scanner_ctl==11:  # 持续运行， ctl为11才需要读取数据做处理
                    self.running_laser()
                else:
                    # 持续关闭状态，不做处理
                    laserLog.info("持续关闭或者暂停状态，不做处理")

                self.original_ctl = scanner_ctl
                # time.sleep(self.time_interval)
                # await asyncio.sleep(self.time_interval)
            except Exception as e:
                laserLog.error(f"plc和laser循环处理逻辑出错: {e}")


# 测试用
def stop_laser_scan_plc(cli):
    print("Stopping laser scan...")
    # disconnect_laser()
    # write_from_redis_to_csv()

    cli_node = cli.get_node('ns=3;s="GDB_Scanner"."ScannerCtrl"')  # Int16
    cli_node.set_value(ua.DataValue(ua.Variant(0, ua.VariantType.Int16)))

    # global stop_event
    # stop_event.set()
    print("Laser scan stopped and data written to CSV.")


# 测试用
def count_func(cli):
    cli_node = cli.get_node('ns=3;s="GDB_Scanner"."ScannerCtrl"')  # Int16
    cli_node.set_value(ua.DataValue(ua.Variant(1, ua.VariantType.Int16)))


# 定时器，做测试开关plc的ctl状态
def test_timer(cli):
    # stop_event = threading.Event()
    timer = threading.Timer(10, stop_laser_scan_plc, (cli,))
    timer.start()

    timer2 = threading.Timer(2, count_func, (cli,))
    timer2.start()


if __name__ == '__main__':
    try:
        pl_obj = PlcLaserServer()
        pl_obj.runserver()
    except Exception as e:
        print("循环体中报错:", e)
        traceback.print_exc()
    finally:
        print("程序结束...")

