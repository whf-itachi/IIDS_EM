from datetime import datetime

import pytz

from IIDS.settings import TIME_ZONE
from his.models import BladeCheckVersion


# 获取叶片最新的版本号
def get_latest_check_version(blade_id, default_version=1):
    """
    一次质检签名为一版本
    :param blade_id:
    :param default_version:
    :return:
    """
    # 首先查询是否有记录，按 created_at 降序排列，获取最新的一条记录
    blade_check_version = BladeCheckVersion.objects.filter(bladeId=blade_id).order_by('-created_at').first()

    if blade_check_version:
        # 如果有记录，返回最新记录的 checkVersion
        return blade_check_version.checkVersion
    else:
        # 如果没有记录，创建一个新的记录
        blade_check_version = BladeCheckVersion.objects.create(
            bladeId=blade_id, checkVersion=default_version
        )
        return blade_check_version.checkVersion


# 统一格式化前端时间参数，格式化为数据库的UTC时间
def convert_utc_time(time_str):
    # 将 UTC 时间转换为设置时间
    beijing_zone = pytz.timezone(TIME_ZONE)
    # 解析开始时间和结束时间，使用 fromisoformat 处理带有时区信息的时间
    time_utc = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    time_utc = time_utc.astimezone(beijing_zone)

    return time_utc
