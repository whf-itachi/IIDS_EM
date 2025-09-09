# -*- coding: utf-8 -*-
import json
import logging
import traceback
from datetime import datetime
import numpy as np

import redis
from django.db.models import Max
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from his.hisModelsSerializer import ErrMsgSerializer, UserLogSerializer, BladeRecordSerializer, DMMSnapSerializer, \
    BladeTypeCheckRuleSerializer, BladeSignImageSerializer, FlatnessReportSerializer
from his.models import ErrMsg, DMMSnap, UserLog, BladeRecord, BladeTypeCheckRule, BladeSignImage, FlatnessReport, \
    DMMSnapLog

from utils.publicFunction import convert_utc_time
from utils.translations import TRANSLATIONS

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
programLog = logging.getLogger('programLog')

def real(request):
    msgdict = ErrMsg.objects.all()
    template = get_template('real.html')
    html = template.render(locals())
    return HttpResponse(html)


# 查询设备上报最新信息
def old_real_data(request):
    """
    查询redis中的最新数据并返回：
    :param request:
    :return:
    """
    response_data = {
        'code': 200,
        'status': "ok",
    }
    try:
        msg = redis_client.get("reportData")
        msg = msg.decode('utf-8')
        data = json.loads(msg)
        res_list = create_device_detail_list(data)

        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
            'data': res_list
        }
    except Exception as e:
        # msg = str(e).encode("utf-8")
        return JsonResponse(response_data)
    else:
        return JsonResponse(response_data, safe=False)


# 查询设备上报最新信息
def real_data(request):
    """
    查询redis中的最新数据并返回：
    :param request:
    :return:
    """
    response_data = {
        'code': 200,
        'status': "ok",
    }
    try:
        msg = redis_client.get("reportData")
        msg = msg.decode('utf-8')
        res_list = json.loads(msg)
        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
            'data': res_list
        }
    except Exception as e:
        return JsonResponse(response_data)
    else:
        return JsonResponse(response_data, safe=False)


# 查询告警信息日志
@csrf_exempt  # post请求需要 禁用CSRF保护
@api_view(['POST'])  # 只能post请求
def alarm_log_data(request):
    try:
        # 获取请求数据
        data = request.body.decode('utf-8')
        json_data = json.loads(data)

        query_filter = dict()

        # 获取开始时间和结束时间（必传字段）
        start_time_str = json_data.get("startTime")
        end_time_str = json_data.get("endTime")

        # 获取可选字段（叶片名称和告警类型）
        blade_id = json_data.get("bladeName")
        alarm_type = json_data.get("alarmType")

        # 解析开始时间和结束时间，使用 fromisoformat 处理带有时区信息的时间
        if start_time_str:
            query_filter["dt__gte"] = convert_utc_time(start_time_str)
        if end_time_str:
            query_filter["dt__lte"] = convert_utc_time(end_time_str)

        # 如果有叶片名称，添加过滤条件
        if blade_id:
            query_filter['bladeName__icontains'] = blade_id

        # 如果有告警类型，添加过滤条件
        if alarm_type:
            query_filter['msgType__exact'] = alarm_type

        # 查询错误信息
        error_info = ErrMsg.objects.filter(**query_filter).order_by('-id')
        serializer = ErrMsgSerializer(instance=error_info, many=True)
        res_list = serializer.data

        # 构建响应数据
        response_data = {
            'code': 200,
            'status': "ok",
            'data': res_list
        }

        return JsonResponse(response_data, safe=False)

    except Exception as e:
        # traceback.print_exc(e)
        programLog.error(f"查询告警信息日志,报错：{e}")
        # 捕获异常并返回错误信息
        return JsonResponse({
            'code': 500,
            'status': "error",
            'message': f"服务器内部错误: {str(e)}"
        }, status=500)


# 查询快照日志
@api_view(['GET'])
def real_snapshot_data(request, snap_id):
    try:
        # 根据id查询DMMSnapLog
        snapshot_log = DMMSnapLog.objects.get(id=snap_id)
        # 获取快照字符串
        snap_str = snapshot_log.snapStr
        # 尝试将快照字符串转换为JSON
        snap_data = json.loads(snap_str)

        # 移除 errorBytes 字段
        if 'errorBytes' in snap_data:
            del snap_data['errorBytes']

        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
            'data': snap_data
        }
    except Exception as e:
        # msg = str(e).encode("utf-8")
        response_data = {
            'code': 400,
            'status': "error",
        }
        return JsonResponse(response_data)
    else:
        return JsonResponse(response_data, safe=False)


# 查询登录日志(废弃)
@api_view(['GET'])
def old_real_user_log_data(request):
    try:
        error_info = UserLog.objects.all().order_by("-id")
        serializer = UserLogSerializer(instance=error_info, many=True)
        res_list = serializer.data
        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
            'data': res_list
        }
    except Exception as e:
        # msg = str(e).encode("utf-8")
        response_data = {
            'code': 400,
            'status': "error",
        }
        return JsonResponse(response_data)
    else:
        return JsonResponse(response_data, safe=False)

# 查询用户登录日志
@api_view(['GET'])
def real_user_log_data(request):
    try:
        # 获取查询参数中的开始时间和结束时间
        start_time_str = request.GET.get('start_time')
        end_time_str = request.GET.get('end_time')
        print("得到时间范围参数：", start_time_str, end_time_str)

        # 如果传入了开始和结束时间，进行处理
        if start_time_str and end_time_str:
            try:
                # 将时间字符串转换为 datetime 对象
                start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
                end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')

                # 将其转换为 timezone-aware datetime
                start_time = timezone.make_aware(start_time)
                end_time = timezone.make_aware(end_time)

                # 使用过滤条件查询登录和登出时间都在该范围内的记录
                user_logs = UserLog.objects.filter(
                    logout_time__gte=start_time,
                    login_time__lte=end_time
                ).order_by("-id")

            except ValueError:
                return JsonResponse({
                    'code': 400,
                    'status': 'error',
                    'message': 'Invalid time format. Please use YYYY-MM-DD HH:MM:SS.'
                })
        else:
            # 如果没有传入时间范围，则查询所有记录
            user_logs = UserLog.objects.all().order_by("-id")

        # 序列化数据
        serializer = UserLogSerializer(instance=user_logs, many=True)
        res_list = serializer.data

        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
            'data': res_list
        }

    except Exception as e:
        response_data = {
            'code': 400,
            'status': "error",
            'message': str(e)
        }

    return JsonResponse(response_data, safe=False)


# 查询叶片日志
@csrf_exempt  # post请求需要 禁用CSRF保护
@api_view(['POST'])  # 只能post请求
def real_blade_log_data(request):
    try:
        # 获取请求数据
        data = request.body.decode('utf-8')
        json_data = json.loads(data)

        query_filter = dict()

        # 获取开始时间和结束时间（必传字段）
        start_time_str = json_data.get("startTime")
        end_time_str = json_data.get("endTime")

        # 获取可选字段（叶片名称和告警类型）
        blade_name = json_data.get("bladeName")
        blade_type = json_data.get("bladeType")

        # 解析开始时间和结束时间，使用 fromisoformat 处理带有时区信息的时间
        if start_time_str:
            query_filter["dt__gte"] = convert_utc_time(start_time_str)
        if end_time_str:
            query_filter["dt__lte"] = convert_utc_time(end_time_str)

        # 如果有叶片名称，添加过滤条件
        if blade_name:
            query_filter['bldname'] = blade_name

        # 如果有告警类型，添加过滤条件
        if blade_type:
            query_filter['bldtype'] = blade_type

        # 查询错误信息
        error_info = BladeRecord.objects.filter(**query_filter).order_by('-id')
        serializer = BladeRecordSerializer(instance=error_info, many=True)
        res_list = serializer.data

        # 构建响应数据
        response_data = {
            'code': 200,
            'status': "ok",
            'data': res_list
        }

        return JsonResponse(response_data, safe=False)

    except Exception as e:
        # 捕获异常并返回错误信息
        return JsonResponse({
            'code': 500,
            'status': "error",
            'message': f"服务器内部错误: {str(e)}"
        }, status=500)


# 查询快照日志(废弃)
def real_snapshot_log_data(request):
    try:
        error_info = DMMSnap.objects.all()
        serializer = DMMSnapSerializer(instance=error_info, many=True)
        res_list = serializer.data
        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
            'data': res_list
        }
    except Exception as e:
        # msg = str(e).encode("utf-8")
        response_data = {
            'code': 400,
            'status': "error",
        }
        return JsonResponse(response_data)
    else:
        return JsonResponse(response_data, safe=False)


# 查询所有叶片类型校验规则
@api_view(['GET'])  # 只允许 GET 请求
def get_all_blade_check_rules(request):
    """
    查询所有叶片类型的校验规则：
    :param request:
    :return:
    """
    try:
        # 查询所有 BladeTypeCheckRule 数据
        blade_type_check_rules = BladeTypeCheckRule.objects.all()

        # 序列化查询结果
        serializer = BladeTypeCheckRuleSerializer(blade_type_check_rules, many=True)

        # 准备响应数据
        data = {
            'data': serializer.data,
            'code': 200,
            'msg': "ok"
        }
    except Exception as e:
        # 捕获异常并返回错误信息
        data = {
            'data': None,
            'code': 500,
            'msg': f"An error occurred: {str(e)}"
        }
        return JsonResponse(data, status=500)

    return JsonResponse(data)


# 新增 叶片类型校验规则
@api_view(['POST'])
def create_blade_type_check_rule(request):
    """
    创建新的叶片类型校验规则
    """
    serializer = BladeTypeCheckRuleSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET', 'PUT', 'DELETE'])
def blade_type_check_rule_operate(request, blade_type):
    try:
        blade_rule = BladeTypeCheckRule.objects.get(bladeType=blade_type)
    except BladeTypeCheckRule.DoesNotExist:
        return Response({"error": "未找到该叶片类型的校验规则"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # 获取逻辑
        serializer = BladeTypeCheckRuleSerializer(blade_rule)
        return Response(serializer.data, status=status.HTTP_200_OK)
    elif request.method == 'PUT':
        # 更新逻辑
        serializer = BladeTypeCheckRuleSerializer(blade_rule, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        # 删除逻辑
        blade_rule.delete()
        return Response({"message": "删除成功"}, status=status.HTTP_200_OK)


# 根据叶片id查询叶片类型校验规则
@api_view(['GET'])  # 只允许 GET 请求
def get_blade_check_rule_by_id(request, blade_id):
    """
        根据叶片id查询叶片类型校验规则：
        :param blade_id:  叶片ID（页脚叶片名称）
        :param request:
        :return:
        """
    try:
        # 根据传入叶片id 获取 BladeRecord 对象
        blade_record = BladeRecord.objects.get(bldname=blade_id)
        bldtype = blade_record.bldtype
        # 根据查询到的类型 查询 BladeTypeCheckRule 数据
        blade_type_check_rule = BladeTypeCheckRule.objects.get(bladeType=bldtype)
        # 输出校验规则的值
        # 序列化查询结果
        serializer = BladeTypeCheckRuleSerializer(blade_type_check_rule)
    except BladeRecord.DoesNotExist:
        return JsonResponse({"data": '', "code": 400, "msg": f"BladeRecord with id {blade_id} not found."})
    except BladeTypeCheckRule.DoesNotExist:
        return JsonResponse({"data": '', "code": 400, "msg": f"BladeTypeCheckRule for bladeType {bldtype} not found."})
    else:
        # 准备响应数据
        data = {
            'data': serializer.data,
            'code': 200,
            'msg': "ok"
        }
        return JsonResponse(data)


# 根据叶片id查询其孔的平面度数据
@api_view(['GET'])  # 只允许 GET 请求
def get_blade_hole_flatness_by_id(request, blade_id):
    """
        根据叶片id查询其孔的平面度数据：
        :param blade_id:  叶片ID（页脚叶片名称）
        :param request:
        :return:
        """
    try:
        lang = request.META.get('HTTP_ACCEPT_LANGUAGE', 'zh')  # 默认值为 'zh'

        flatness_info = FlatnessReport.objects.filter(bladeId=blade_id).values('holeAngle', 'flatness')

        # 序列化查询结果
        serializer = FlatnessReportSerializer(flatness_info, many=True)

        flatness_data = [i.get("flatness") for i in serializer.data]

        # 输出结果
        peak_to_peak = round(np.max(flatness_data) - np.min(flatness_data), 2)  # 计算峰-峰值
        std_dev = round(np.std(flatness_data), 2)  # 计算标准偏差
        rms = round(np.sqrt(np.mean(np.square(flatness_data))), 2)  # 计算平面度 RMS
        max_value = round(np.max(flatness_data), 2)
        min_value = round(np.min(flatness_data), 2)

        ts = TRANSLATIONS.get(lang, TRANSLATIONS['zh'])

        result = {
            "flatness_info": serializer.data,
            "statistic": {
                "peak_to_peak": {"name": ts['peak_to_peak'], "value": peak_to_peak},
                "std_dev": {"name": ts['std_dev'], "value": std_dev},
                "rms": {"name": ts['rms'], "value": rms},
                "max_value": {"name": ts['max_value'], "value": max_value},
                "min_value": {"name": ts['min_value'], "value": min_value}
            }
        }
    except FlatnessReport.DoesNotExist:
        return JsonResponse({"data": '', "code": 400, "msg": f"{blade_id} not found."})
    else:
        # 准备响应数据
        data = {
            'data': result,
            'code': 200,
            'msg': "ok"
        }
        return JsonResponse(data)


# 查询各版本叶片参数签名图片
@api_view(['GET'])  # 只允许 GET 请求
def get_blade_hole_signature_images(request, blade_id):
    """
        根据叶片id查询叶片各版本质检签名结果图片：
        :param blade_id:  叶片ID（页脚叶片名称）
        :param request:
        :return:
        """
    try:
        # 根据传入叶片id 获取 BladeRecord 对象
        image_record = BladeSignImage.objects.filter(bldname=blade_id)

        # 序列化查询结果
        serializer = BladeSignImageSerializer(image_record, many=True)
        image_base64_list = [item['signImg'] for item in serializer.data]
    except BladeRecord.DoesNotExist:
        return JsonResponse({"data": '', "code": 400, "msg": f"BladeRecord with id {blade_id} not found."})
    else:
        # 准备响应数据
        data = {
            'data': image_base64_list,
            'code': 200,
            'msg': "ok"
        }
        return JsonResponse(data)



# 设备上报数据接口
@csrf_exempt  # 禁用CSRF保护
def reported_data(request):
    try:
        data = request.body.decode("utf_8")
        # 将数据存入redis
        redis_client.set("reportData", data)
        data = json.loads(data)

        snap_flag = False  # 如果為真需要進行快照保存

        # 对告警信息做处理
        addressid = ErrMsg.objects.aggregate(Max('addressid'))
        addressid_max = addressid.get("addressid__max") if addressid.get("addressid__max") else 1
        addressid_max += 1
        if "错误" in data.get("errorBytes"):
            # 创建 Book 对象并保存
            err_msg_obj = ErrMsg(addressid=addressid_max, msgtype="e", msgtext=data.get("errorBytes", "省略..."))
            err_msg_obj.save()
            # 一旦产生错误告警，需要存入快照
            snap_flag = True
        if "警告" in data.get("errorBytes"):
            err_msg_obj = ErrMsg(addressid=addressid_max, msgtype="w", msgtext=data.get("errorBytes", "省略..."))
            err_msg_obj.save()

        # 人员变动检查

        # 叶片变动检查


        # 如果为真进行快照存储操作
        if snap_flag:
            snap_record(data)

    except Exception as e:
        traceback.print_exc()  # 这将打印完整的错误栈
        response_data = {
            "code": 400,
            "msg": f"error is {e}"
        }
        return JsonResponse(response_data)
    # 准备响应数据
    response_data = {
        'code': 200,
        'status': "ok",
    }

    return JsonResponse(response_data)


# 保存当前快照
def snap_record(data):
    # 2024-08-25 17:35:58.000000
    date_string = data['dt']
    # 转换字符串为 datetime 对象
    dt_object = datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
    # 如果你的 Django 项目启用了时区支持，并且需要将 naive datetime 转换为 aware datetime
    dt_aware = timezone.make_aware(dt_object)  # 使用 timezone.make_aware() 将其转换为带有时区的对象

    snap = DMMSnap(dt=dt_aware)
    snap.bldrecord_id = data["bldrecord_id"]
    snap.username = data['username']

    snap.bldMode = data['bldMode']

    snap.program = data['program']
    snap.prgStep = data['prgStep']
    
    snap.bldonSaddle = data['bldonSaddle']
    snap.doorClosed = data['doorClosed']
    snap.powerOn = data['powerOn']
    
    snap.saddleMoveDir = data['saddleMoveDir']
    snap.posSaddleExist = data['posSaddleExist']
    snap.posSaddlePos = data['posSaddlePos']

    snap.armPos = data['armPos']
    snap.armSpeed = data['armSpeed']
    snap.armTarget = data['armTarget']
    snap.armPower = data['armPower']

    snap.cutUnitExist = True
    snap.cutFeedPos = data['cutFeedPos']
    snap.cutFeedSpeed = data['cutFeedSpeed']
    snap.cutFeedTarget = data['cutFeedTarget']
    snap.cutFeedPower = data['cutFeedPower']
    snap.cutSpindleSpeed = data['cutSpindleSpeed']
    snap.cutSpindlePower = data['cutSpindlePower']

    snap.millUnitExist = True
    snap.millFeedPos = data['millFeedPos']
    snap.millFeedSpeed = data['millFeedSpeed']
    snap.millFeedTarget = data['millFeedTarget']
    snap.millFeedPower = data['millFeedPower']
    snap.millSpindleSpeed = data['millSpindleSpeed']
    snap.millSpindlePower = data['millSpindlePower']

    snap.axial1UnitExist = True
    snap.axial1FeedPos = data['axial1FeedPos']
    snap.axial1FeedSpeed = data['axial1FeedSpeed']
    snap.axial1FeedTarget = data['axial1FeedTarget']
    snap.axial1FeedPower = data['axial1FeedPower']
    snap.axial1SpindleSpeed = data['axial1SpindleSpeed']
    snap.axial1SpindlePower = data['axial1SpindlePower']

    snap.radial1UnitExist = True
    snap.radial1FeedPos = data['radial1FeedPos']
    snap.radial1FeedSpeed = data['radial1FeedSpeed']
    snap.radial1FeedTarget = data['radial1FeedTarget']
    snap.radial1FeedPower = data['radial1FeedPower']
    snap.radial1SpindleSpeed = data['radial1SpindleSpeed']
    snap.radial1SpindlePower = data['radial1SpindlePower']

    snap.axial2UnitExist = True
    snap.axial2FeedPos = data['axial2FeedPos']
    snap.axial2FeedSpeed = data['axial2FeedSpeed']
    snap.axial2FeedTarget = data['axial2FeedTarget']
    snap.axial2FeedPower = data['axial2FeedPower']
    snap.axial2SpindleSpeed = data['axial2SpindleSpeed']
    snap.axial2SpindlePower = data['axial2SpindlePower']

    snap.axial3UnitExist = True
    snap.axial3FeedPos = data['axial3FeedPos']
    snap.axial3FeedSpeed = data['axial3FeedSpeed']
    snap.axial3FeedTarget = data['axial3FeedTarget']
    snap.axial3FeedPower = data['axial3FeedPower']
    snap.axial3SpindleSpeed = data['axial3SpindleSpeed']
    snap.axial3SpindlePower = data['axial3SpindlePower']

    snap.radial2UnitExist = True
    snap.radial2FeedPos = data['radial2FeedPos']
    snap.radial2FeedSpeed = data['radial2FeedSpeed']
    snap.radial2FeedTarget = data['radial2FeedTarget']
    snap.radial2FeedPower = data['radial2FeedPower']
    snap.radial2SpindleSpeed = data['radial2SpindleSpeed']
    snap.radial2SpindlePower = data['radial2SpindlePower']

    snap.mill2UnitExist = True
    snap.mill2FeedPos = data['mill2FeedPos']
    snap.mill2FeedSpeed = data['mill2FeedSpeed']
    snap.mill2FeedTarget = data['mill2FeedTarget']
    snap.mill2FeedPower = data['mill2FeedPower']
    
    snap.scannerExist = True
    snap.scannerOn = data['scannerOn']
    snap.scannerData = data['scannerData']
    
    snap.mWheelExist = True
    snap.mWheelOn = True if data['mWheelOn'] == 1 else False
    snap.mWShakeValue = data['mWShakeValue']
    
    snap.clampExist = True
    snap.clampClosed = True if data['clampClosed'] == 1 else False
    snap.clampMoveDir = 0
    
    snap.roofExist = True
    snap.roofClosed = True if data['roofClosed'] == 1 else False
    snap.roofMoveDir = 0
    
    snap.autoAjustExist = False
    snap.xAjustPos = 0.0
    snap.zAjustPos = 0.0
    snap.xAjustMoveDir = 0
    snap.zAjustMoveDir = 0
    
    snap.save()


# 根据设备上报数据组织为前端需求格式
def create_device_detail_list(data):

    # 操作员、叶片信息
    A = {
        "header": "操作员、叶片信息",
        "data": [{
            "title": '更新时间',
            "content": data.get("dt")
        }, {
            "title": '操作员',
            "content":  data.get("username")
        }, {
            "title": '叶片名称',
            "content":  data.get("bladeName")
        }, {
            "title": '叶片型号',
            "content":  data.get("bladeType")
        }],
    }
    # 程序
    B = {
        "header": "程序",
        "data": [{
            "title": '模式',
            "content": data.get("bldMode")
        }, {
            "title": '程序号',
            "content": data.get("program")
        }, {
            "title": '步骤',
            "content": data.get("prgStep")
        }],
    }
    # 门，驱动电源
    C = {
        "header": "门、驱动电源",
        "data": [{
            "title": '门',
            "content": data.get("doorClosed")
        }, {
            "title": '驱动电源',
            "content": data.get("powerOn")
        }],
    }
    # 大臂
    D = {
        "header": "大臂",
        "data": [{
            "title": '当前位置',
            "content": data.get("armPos")
        }, {
            "title": '速度',
            "content": data.get("armSpeed")
        }, {
            "title": '目标位置',
            "content": data.get("armTarget")
        }, {
            "title": '功率',
            "content": data.get("armPower")
        }],
    }
    # 晃动监测
    E = {
        "header": "晃动监测",
        "data": [{
            "title": '测量轮',
            "content": data.get("mWheelExist")
        }, {
            "title": '轴向晃动',
            "content": data.get("mWShakeValue")
        }],
    }
    # 支架、叶片夹具、顶棚
    F = {
        "header": "支架、叶片夹具、顶棚",
        "data": [{
            "title": '支架位置',
            "content": data.get("clampMoveDir")
        }, {
            "title": '支架运动',
            "content": data.get("clampClosed")
        }, {
            "title": '夹具状态',
            "content": data.get("clampExist")
        }, {
            "title": '顶棚',
            "content": data.get("roofClosed")
        }],
    }
    # 切割单元
    G = {
        "header": "切割单元",
        "data": [{
            "title": '进给位置',
            "content": data.get("cutFeedPos")
        }, {
            "title": '进给速度',
            "content": data.get("cutFeedSpeed")
        }, {
            "title": '刀具功率',
            "content": data.get("cutFeedPower")
        }, {
            "title": '旋转速度',
            "content": data.get("cutSpindleSpeed")
        }],
    }
    # 铣磨单元
    H = {
        "header": "铣磨单元",
        "data": [{
            "title": '进给位置',
            "content": data.get("millFeedPos")
        }, {
            "title": '进给速度',
            "content": data.get("millFeedSpeed")
        }, {
            "title": '刀具功率',
            "content": data.get("millFeedPower")
        }, {
            "title": '旋转速度',
            "content": data.get("millSpindleSpeed")
        }],
    }
    # 轴向单元1
    I = {
        "header": "轴向单元1",
        "data": [{
            "title": '进给位置',
            "content": data.get("axial1FeedPos")
        }, {
            "title": '进给速度',
            "content": data.get("axial1FeedSpeed")
        }, {
            "title": '刀具功率',
            "content": data.get("axial1FeedPower")
        }, {
            "title": '旋转速度',
            "content": data.get("axial1SpindleSpeed")
        }],
    }
    # 径向单元
    J = {
        "header": "径向单元",
        "data": [{
            "title": '进给位置',
            "content": data.get("radial1FeedPos")
        }, {
            "title": '进给速度',
            "content": data.get("radial1FeedSpeed")
        }, {
            "title": '刀具功率',
            "content": data.get("radial1FeedPower")
        }, {
            "title": '旋转速度',
            "content": data.get("radial1SpindleSpeed")
        }],
    }
    # 轴向单元2
    K = {
        "header": "轴向单元2",
        "data": [{
            "title": '进给位置',
            "content": data.get("axial2FeedPos")
        }, {
            "title": '进给速度',
            "content": data.get("axial2FeedSpeed")
        }, {
            "title": '刀具功率',
            "content": data.get("axial2FeedPower")
        }, {
            "title": '旋转速度',
            "content": data.get("axial2SpindleSpeed")
        }],
    }
    # 径向单元2
    L = {
        "header": "径向单元2",
        "data": [{
            "title": '进给位置',
            "content": data.get("radial2FeedPos")
        }, {
            "title": '进给速度',
            "content": data.get("radial2FeedSpeed")
        }, {
            "title": '刀具功率',
            "content": data.get("radial2FeedPower")
        }, {
            "title": '旋转速度',
            "content": data.get("radial2SpindleSpeed")
        }],
    }
    # 轴向单元3
    M = {
        "header": "轴向单元3",
        "data": [{
            "title": '进给位置',
            "content": data.get("axial3FeedPos")
        }, {
            "title": '进给速度',
            "content": data.get("axial3FeedSpeed")
        }, {
            "title": '刀具功率',
            "content": data.get("axial3FeedPower")
        }, {
            "title": '旋转速度',
            "content": data.get("axial3SpindleSpeed")
        }],
    }
    # 铣磨单元2、平面扫描
    N = {
        "header": "铣磨单元2、平面扫描",
        "data": [{
            "title": '进给位置',
            "content": data.get("mill2FeedPos")
        }, {
            "title": '进给速度',
            "content": data.get("mill2FeedSpeed")
        }, {
            "title": '扫描仪',
            "content": data.get("scannerOn")
        }, {
            "title": '当前扫描',
            "content": data.get("scannerData")
        }],
    }
    res_list = [A, B, C, D, E, F, J, H, I, G, K, L, M, N]

    return res_list