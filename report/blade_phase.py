# coding=utf-8
import json
import redis

from django.db.models import Avg
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view

from his.hisModelsSerializer import BladePhaseLogSerializer, AllBladePhaseStatisticSerializer, BladeRecordSerializer, \
    BladeSignImageSerializer, BladeHoleParameterSerializer
from his.models import BladePhaseLog, AllBladePhaseStatistic, BladeRecord, BladeHoleParameter, BladeSignImage
from utils.publicFunction import get_latest_check_version, convert_utc_time
from utils.translations import BladeReportT

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)


# 获取叶片所有加工阶段日志
@api_view(['GET'])  # 只允许 GET 请求
def get_blade_phase_log(request, blade_id):
    """
        获取叶片加工各时间段日志信息：
        :param blade_id:  叶片ID（页脚叶片名称）
        :param request:
        :return:
        """
    lang = request.META.get('HTTP_ACCEPT_LANGUAGE', 'zh')  # 默认值为 'zh'
    phase_data = BladePhaseLog.objects.filter(bladeId=blade_id)
    # 如果没有找到任何记录
    if not phase_data.exists():
        return JsonResponse({'message': 'No records found for this bladeId.'}, status=404)

    # 序列化查询结果
    serializer = BladePhaseLogSerializer(phase_data, many=True)
    # print(serializer.data)

    # 动态转换 phase 字段内容
    translated_data = []
    trans_dict = BladeReportT.get(lang, {})
    for record in serializer.data:
        phase = record.get('phase')  # 假设 phase 是记录中的字段
        translated_phase = trans_dict.get(phase, phase)  # 如果映射中没有找到，保留原值
        record['phase'] = translated_phase
        translated_data.append(record)

    # print(translated_data)
    # 准备响应数据
    data = {
        'data': translated_data,
        'code': 200,
        'msg': "ok"

    }
    return JsonResponse(data)


# 获取叶片各工序的统计数据
@api_view(['GET'])  # 只允许 GET 请求
def get_blade_statistic_data(request, blade_id):
    """
        获取叶片各工序的统计数据以及该类叶片各工序的平均值：
        :param blade_id:  叶片ID（页脚叶片名称）
        :param request:
        :return:
        """
    # 查找指定叶片的工序加工时间
    blade = AllBladePhaseStatistic.objects.get(bladeId=blade_id)
    print("获取到加工时间：", blade)
    # 查找指定叶片类型的所有叶片工序加工时间，并计算各工序的平均值

    blade_type = blade.bladeType
    blade_type_avg = AllBladePhaseStatistic.objects.filter(bladeType=blade_type).aggregate(
        avg_auto_cut=Avg('AutoCut'),
        avg_auto_mill=Avg('AutoMill'),
        avg_test_drill=Avg('TestDrill'),
        avg_auto_drill=Avg('AutoDrill'),
        # avg_all_time=Avg('AllTime')
    )
    type_avg_time = AllBladePhaseStatistic.objects.filter(bladeType=blade_type).aggregate(
        avg_all_time=Avg('AllTime')
    )['avg_all_time']
    # 保留两位小数
    blade_type_avg = {key: round(value, 2) if value is not None else None for key, value in blade_type_avg.items()}

    # 返回结果，去掉id和类型字段
    blade_data = {
        # "blade_id": blade.bladeId,
        # "blade_type": blade.bladeType,
        "auto_cut": blade.AutoCut,
        "auto_mill": blade.AutoMill,
        "test_drill": blade.TestDrill,
        "auto_drill": blade.AutoDrill,
        # "all_time": blade.AllTime,
    }

    blade_max = max(blade_data.values())
    average_max = max(blade_type_avg.values())

    result = {
        "blade_log": blade_data,
        "average_data": blade_type_avg,
        "max_value": max(blade_max, average_max),
        "all_time": blade.AllTime,
        "type_avg_time": round(type_avg_time, 2)
    }

    print(result)
    # 准备响应数据
    data = {
        'data': result,
        'code': 200,
        'msg': "ok"

    }
    return JsonResponse(data)


# 根据叶片名称获取类型
@api_view(['GET'])  # 只允许 GET 请求
def get_blade_type_by_name(request, blade_id):
    """
    根据叶片名称获取对应的叶片类型（返回一条记录的 bldtype 字段）
    :param blade_id: 叶片的名称或ID
    :param request: 请求对象
    :return: 返回叶片的 bldtype 字段
    """
    print(blade_id, "...............")

    try:
        # 获取对应 blade_id 的单条 BladeRecord 数据
        phase_data = BladeRecord.objects.get(bldname=blade_id)
    except BladeRecord.DoesNotExist:
        # 如果没有找到记录，返回 404 错误
        return JsonResponse({"data": '', "code": 400, "msg": f"BladeRecord with id {blade_id} not found."})

    # 序列化查询结果，只返回 bldtype 字段
    # serializer = BladeRecordSerializer(phase_data, context={'fields': ['bldtype']})
    serializer = BladeRecordSerializer(phase_data)
    print(serializer.data)

    # 准备响应数据
    data = {
        'data': serializer.data,
        'code': 200,
        'msg': "ok"
    }
    return JsonResponse(data)


# 获取某一类叶片加工时间统计数据
@csrf_exempt  # post请求需要 禁用CSRF保护
@api_view(['POST'])
def get_blade_type_phase_statistic(request):
    """
        获取某时间段叶片加工统计数据：
        :param
            blade_type:  叶片类型
            startTime:  开始时间
            endTime:  结束时间
        :param request:
        :return:
        """
    try:
        data = request.body.decode('utf-8')
        json_data = json.loads(data)
        # print(json_data, ' is json data get_blade_type_phase_statistic')
        blade_type = json_data.get("bladeType")
        start_time_str = json_data.get("startTime")
        end_time_str = json_data.get("endTime")

        phase_data = AllBladePhaseStatistic.objects.filter(
            bladeType=blade_type,
            created_at__range=[convert_utc_time(start_time_str), convert_utc_time(end_time_str)],  # 假设有 created_at 字段
        )
        # 如果没有找到任何记录
        if not phase_data.exists():
            return JsonResponse({'message': 'No records found for this bladeType.'}, status=404)

        # 序列化查询结果
        serializer = AllBladePhaseStatisticSerializer(phase_data, many=True)
        # 准备响应数据
        data = {
            'data': serializer.data,
            'code': 200,
            'msg': "ok"

        }
        return JsonResponse(data)
    except Exception as e:
        # print("??????????:", e)
        return JsonResponse({"msg": "error"}, status=400)


# 查询叶片验收签名信息
@api_view(['GET'])
def blade_signature_query(request, blade_id):
    # 查询hole参数
    try:
        # 查询最新版本编号
        blade_version = get_latest_check_version(blade_id)

        # 查询
        phase_data = BladeHoleParameter.objects.filter(bldname=blade_id, checkVersion=blade_version)
    except BladeHoleParameter.DoesNotExist:
        # 如果没有找到记录，返回 404 错误
        return JsonResponse({'message': 'No record found for this bladeName.'}, status=404)
    hole_serializer = BladeHoleParameterSerializer(phase_data, many=True)
    hole_parameter = hole_serializer.data
    print(hole_parameter)

    # 查询签名
    try:
        sign_data = BladeSignImage.objects.filter(bldname=blade_id)
    except BladeSignImage.DoesNotExist:
        # 如果没有找到记录，返回 404 错误
        return JsonResponse({'message': 'No record found for this bladeName.'}, status=404)

    sign_serializer = BladeSignImageSerializer(sign_data, many=True)
    sign_image = sign_serializer.data

    # 准备响应数据
    data = {
        'data': {"hole_info": hole_parameter, "sign_image": sign_image},
        'code': 200,
        'msg': "ok"
    }
    return JsonResponse(data)