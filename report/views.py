# coding=utf-8
import asyncio
import base64
import json
import os
import time
import traceback
from datetime import datetime

import redis
from PyPDF2 import PdfReader
from asgiref.sync import sync_to_async
from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Image, Spacer, Frame, \
    PageTemplate

from rest_framework.decorators import api_view

from IIDS.settings import BASE_DIR
from his.hisModelsSerializer import BladeRecordSerializer, ErrMsgSerializer, UserLogSerializer, DMMSnapSerializer, \
    BladeSignImageSerializer, FlatnessReportSerializer
from his.models import BladeRecord, ErrMsg, UserLog, DMMSnap, BladeSignImage, BladeHoleParameter, BladeCheckVersion, \
    FlatnessReport
import io
from reportlab.pdfgen import canvas

from django.db.models import Count, Sum, F, DurationField, Case, When, ExpressionWrapper
from django.db.models.functions import Now

from utils.publicFunction import get_latest_check_version
from utils.translations import FlatnessReportT

redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)


SimSun_path = os.path.join(BASE_DIR, "statics", 'fonts', "simsun.ttc")
calibri_path = os.path.join(BASE_DIR, "statics", 'fonts', "calibri.ttf")
calibrib_path = os.path.join(BASE_DIR, "statics", 'fonts', "calibrib.ttf")


# 获取叶片加工时间信息
def get_blade_report_info(request):
    """
    叶片加工时间信息：
        叶片名称：blade_name
        开始时间：start_time
        结束时间：end_time
    :param request:
    :return:
    """
    bldtypeAll = BladeRecord.objects.all()
    bldAll = BladeRecordSerializer(instance=bldtypeAll, many=True)
    # 准备响应数据
    data = {
        'data': bldAll.data,
        'code': 200,
        'msg': "ok"

    }
    return JsonResponse(data)


# 查询叶片信息接口（过滤预览下载数据）
@csrf_exempt  # 禁用CSRF保护
def blade_report_query(request):
    ret_data = request.body.decode("utf_8")
    filter_data = json.loads(ret_data)
    print("-------------")
    print(filter_data)
    res_data = create_all_of_report_info(filter_data)
    # 准备响应数据
    data = {
        'data': res_data,
        'code': 200,
        'msg': "ok"

    }
    print("get the result!")
    # print(data)
    return JsonResponse(data)


# 图表页面-查询信息
def blade_report_chart_query(request):
    try:
        snap_info = DMMSnap.objects.all()
        serializer = DMMSnapSerializer(instance=snap_info, many=True)
        res_list = serializer.data
        print("------------------------------------------------")
        # print(res_list)
        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
            'data': res_list
        }
    except Exception as e:
        print(e)
        response_data = {
            'code': 400,
            'status': "error",
        }
        return JsonResponse(response_data)
    else:
        return JsonResponse(response_data, safe=False)



# 图表页面-用户登录查询信息
def report_user_logout_chart_query(request):
    try:
        # 获取所有用户的登录记录
        login_records = UserLog.objects.filter(loginout='i')

        # 统计每个用户的登录次数和总登录时长
        login_stats = (
            login_records
            .values('name')
            .annotate(
                login_count=Count('id'),  # 登录次数
                total_time=Sum(
                    ExpressionWrapper(
                        Case(
                            # 如果存在对应的登出记录，使用登出时间
                            When(
                                id__in=UserLog.objects.filter(name=F('name'), loginout='o', dt__gte=F('dt')).values(
                                    'id'),
                                then=F('dt') - F('dt')  # 计算方式
                            ),
                            # 否则使用当前时间
                            default=Now() - F('dt'),
                            output_field=DurationField()
                        ),
                        output_field=DurationField()
                    )
                )
            )
        )

        # 计算所有用户的总登录时间
        total_login_time = login_stats.aggregate(total=Sum('total_time'))['total']
        res_list = {"legend": list(), "series_data": list()}
        # 输出每个用户的登录时间和占比
        for stat in login_stats:
            percentage = round((stat['total_time'] / total_login_time) * 100, 2) if total_login_time else 0

            td = stat['total_time']
            total_seconds = int(td.total_seconds())
            days = total_seconds // 86400  # 每天86400秒
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            # seconds = total_seconds % 60

            # 格式化为字符串
            formatted_time = f"{days}天 {hours}小时 {minutes}分钟"

            res_list["legend"].append(stat['name'])
            res_list["series_data"].append({"name": stat['name'], "value": percentage, "count": stat['login_count'],
                                            "total_time": formatted_time })
        # print(res_list)
        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
            'data': res_list
        }
    except Exception as e:
        print(e)
        response_data = {
            'code': 400,
            'status': "error",
        }
        return JsonResponse(response_data)
    else:
        return JsonResponse(response_data, safe=False)


# 下载叶片加工时间信息
def download_blade_report_old(request):
    """
    叶片加工时间信息：
        叶片名称：blade_name
        开始时间：start_time
        结束时间：end_time
    :param request:
    :return:
    """
    # 查询数据
    data = BladeRecord.objects.all()

    # 创建一个 HttpResponse 对象，设置内容类型为 pdf
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="data.pdf"'

    buffer = io.BytesIO()
    # 创建 PDF
    pdfmetrics.registerFont(TTFont('SimSun', 'SimSun.TTF'))
    # 创建PDF页面的类, 指定输出到http响应对象而不是本地保存，设置大小为A4纸大小
    p = canvas.Canvas(response, pagesize=A4)
    # p = SimpleDocTemplate(response, pagesize=A4)

    width, height = A4

    p.setFont('SimSun', 10)
    # 使用中文字体
    # p.setFont("simsun", 8)  # 设置字体和字号
    # 在 PDF 中写入数据
    p.drawString(50, height - 100, "叶片加工时间信息:")
    y_position = height - 120
    for item in data:
        p.drawString(50, y_position, f"叶片名称：{item.bldname}， 开始时间：{item.dt}， 结束时间：{item.dt}")
        y_position -= 20  # 调整下一行文本的位置

    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response



# 上传各组件图片
@csrf_exempt  # 禁用CSRF保护
def blade_chart_image_upload(request):
    try:
        data = request.body.decode('utf-8')
        json_data = json.loads(data)
        print('898888888888')
        component_name = json_data.get("component_name")
        image_data = json_data.get("imageData")

        # 确保是 base64格式的字符串圖片字符串
        if isinstance(image_data, str) and image_data.startswith('data:image/png;base64,'):
            image_data = image_data.split(',')[1]  # 取出 Base64 数据
            image_data = base64.b64decode(image_data)  # 解码 Base64 数据

            # 將收到的圖片信息保存到本地
            img_path = os.path.join(BASE_DIR, "report", 'temporary_img', f"{component_name}.png")
            print("......", img_path)
            with open(img_path, 'wb') as f:
                f.write(image_data)

    except Exception as e:
        # traceback.print_exc()  # 这将打印完整的错误栈
        response_data = {
            "code": 400,
            "msg": "program error"
        }
        return JsonResponse(response_data)
    else:
        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
        }
        return JsonResponse(response_data)



# 上传叶片验收签名信息
@csrf_exempt  # 禁用CSRF保护
def blade_signature_upload(request):
    """
    叶片参数以及签名验收信息上传接口（查询最新版本号加一）
    :param request:
    :return:
    """
    try:
        data = request.body.decode('utf-8')
        json_data = json.loads(data)
        blade_name = json_data.get("bladeId")
        hole_image = json_data.get("image")
        table_info = json_data.get("tableInfo")  # 汇总表格信息
        # sign_info = json_data.get("signInfo")  # 签名图片信息

        # 查询最新版本编号
        blade_version = get_latest_check_version(blade_name) + 1

        # 将签名图片存入数据库
        print("將必要的數據信息存儲到數據庫", blade_version, blade_name)
        # 使用事务确保数据一致性
        with transaction.atomic():
            # 存储参数图片
            BladeSignImage.objects.create(
                bldname=blade_name,
                signRole="bladeHole",
                checkVersion=blade_version,
                signImg=hole_image
            )

            # # 存储签名图片
            # for sign_data in sign_info:
            #     sign_role = sign_data.get("name")
            #     sign_image = sign_data.get("signImg")
            #
            #     BladeSignImage.objects.create(
            #         bldname=blade_name,
            #         signRole=sign_role,
            #         checkVersion=blade_version,
            #         signImg=sign_image
            #     )

        # 批量更新或创建 孔参数质检信息
        hole_to_create = list()
        for item in table_info:
            record = BladeHoleParameter(
                bldname=blade_name,
                checkVersion=blade_version,
                hole_num=item['tag'],
                valueType=item['name'],
                input=item['input'] if item['input'] else None,
                res=item['res']
            )
            hole_to_create.append(record)

        # 使用事务确保数据一致性
        with transaction.atomic():
            try:
                # 批量创建新记录
                BladeHoleParameter.objects.bulk_create(hole_to_create)
            except Exception as e:
                print(e, "is error")


        # 在做数据存入数据库后要进行版本号更新
        BladeCheckVersion.objects.create(bladeId=blade_name, checkVersion=blade_version)
    except Exception as e:
        traceback.print_exc()  # 这将打印完整的错误栈
        response_data = {
            "code": 400,
            "msg": "program error"
        }
        return JsonResponse(response_data)
    else:
        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
        }
        return JsonResponse(response_data)


# 上传用户登录统计信息
@csrf_exempt  # 禁用CSRF保护
def user_login_chart_upload(request):
    try:
        data = request.body.decode('utf-8')
        json_data = json.loads(data)
        image_data = json_data.get("image")

        # 确保是 base64格式的字符串圖片字符串
        if isinstance(image_data, str) and image_data.startswith('data:image/png;base64,'):
            image_data = image_data.split(',')[1]  # 取出 Base64 数据
            image_data = base64.b64decode(image_data)  # 解码 Base64 数据
            print(image_data)
            # 將收到的圖片信息保存到本地
            img_path = os.path.join(BASE_DIR, "report", 'temporary_img', "user_login_chart.png")
            with open(img_path, 'wb') as f:
                f.write(image_data)

    except Exception as e:
        # traceback.print_exc()  # 这将打印完整的错误栈
        response_data = {
            "code": 400,
            "msg": "program error"
        }
        return JsonResponse(response_data)
    else:
        # 准备响应数据
        response_data = {
            'code': 200,
            'status': "ok",
        }
        return JsonResponse(response_data)


# 报告下载接口
@csrf_exempt  # 禁用CSRF保护
def download_blade_report(request):
    print("download ...")
    # 查询数据
    buffer = io.BytesIO()
    response = HttpResponse(content_type='application/pdf')

    # 获取当前日期和时间，格式化为字符串
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"Report_{timestamp}.pdf"
    print(filename)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # 注册字体
    pdfmetrics.registerFont(TTFont('SimSun', 'SimSun.TTF'))

    # 创建文档
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    # 定义页面模板
    frame = Frame(1.5 * cm, 3 * cm, 18 * cm, 24 * cm, id='normal')
    # 这里的onPage只对首页有效
    template = PageTemplate(id='template', frames=frame, onPage=add_header_footer)
    doc.addPageTemplates(template)

    elements = []

    # 第一页内容
    first_page_data = create_first_page_content(elements)
    # 操作员登录日志
    add_operator_table(elements)
    # elements.append(PageBreak())

    # 插入各组件图片
    add_blade_component_image(elements)
    # 插入簽名頁图片
    add_blade_hole_image(elements)
    add_signature_image(elements)

    # 插入用户登录统计图片
    add_user_login_chart_image(elements)
    # 告警消息日志
    add_warning_log_table(elements)
    # 叶片日志
    add_blade_log_table(elements)
    # 状态快照
    add_snapshot_table(elements)

    # 添加尾页说明
    normal_style = ParagraphStyle(name='Normal', fontName='SimSun', fontSize=12)
    elements.append(Paragraph("尾页说明内容。", normal_style))


    # 计算总页数
    total_pages = len(elements) // 2 + 1  # 根据元素数量估算总页数
    first_page_data[3][1] = str(total_pages)  # 填充总页数到表格中
    # 重新创建表格 填入 总页数
    a_table = Table(first_page_data, colWidths=[80, 200])

    style = TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
        ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
        ('GRID', (0, 0), (-1, -1), 0, colors.white)
    ])
    a_table.setStyle(style)


    elements[1] = a_table  # 更新元素列表中的表格

    # 构建文档，此处如果不指定onLaterPages，那么add_header_footer只有第一页生效
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response


# 单叶片报告下载接口(已经废弃)
@csrf_exempt  # post请求需要 禁用CSRF保护
@api_view(['POST'])  # 只能post请求
def old_download_single_blade_report(request):
    lang = request.META.get('HTTP_ACCEPT_LANGUAGE', 'zh')  # 默认值为 'zh'
    print("语言状态为: ", lang)

    data = request.body.decode('utf-8')
    json_data = json.loads(data)
    blade_id = json_data.get("blade_id")  # 获取到叶片id

    # 读取数据库中叶片版本相关的图片信息
    print("blade_id is :", blade_id)
    image_record = BladeSignImage.objects.filter(bldname=blade_id)
    # 序列化查询结果
    serializer = BladeSignImageSerializer(image_record, many=True)
    image_base64_list = [item['signImg'] for item in serializer.data]

    image_list = list()
    image_list.append("single_blade_chart")
    for index, ibl in enumerate(image_base64_list):
        save_image_to_local(f"sign_{index}", ibl)
        image_list.append(f"sign_{index}")

    # 查询数据
    buffer = io.BytesIO()
    response = HttpResponse(content_type='application/pdf')

    # 获取当前日期和时间，格式化为字符串
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"SignalBladeReport_{timestamp}.pdf"
    response['Content-Type'] = 'application/pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # 注册字体
    pdfmetrics.registerFont(TTFont('SimSun', SimSun_path))
    pdfmetrics.registerFont(TTFont('calibri', calibri_path))
    pdfmetrics.registerFont(TTFont('calibrib', calibrib_path))

    # 创建文档
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    # 定义页面模板
    frame = Frame(1.5 * cm, 3 * cm, 18 * cm, 24 * cm, id='normal')
    # 这里的onPage只对首页有效
    template = PageTemplate(id='template', frames=frame, onPage=add_header_footer)
    doc.addPageTemplates(template)

    elements = []
    page_content = {
        "report_name": ["REPORT", "on", "SINGLE BLADE"],
        "report_table": [
                    ["Company Name:", "Senvion Wind Technology Pvt Ltd"],
                    ["Serie Nr. :", "AGT_7979C/12_2"],
                    ["Batch Quantity:", "1"],
                    ["Total page:", ""],
                    ["Printing Time:", ""]
                ]
    }
    # 第一页内容
    create_first_page_content(elements, page_content=page_content)
    # 插入组件图片
    add_single_blade_component_image(elements, image_list)
    # 添加尾页说明
    normal_style = ParagraphStyle(name='Normal', fontName='SimSun', fontSize=12)
    elements.append(Paragraph("尾页说明内容。", normal_style))

    # 构建文档，此处如果不指定onLaterPages，那么add_header_footer只有第一页生效
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

    pdf = buffer.getvalue()
    buffer.close()

    # 打开生成的 PDF，并读取页数
    pdf_reader = PdfReader(io.BytesIO(pdf))
    total_pages = len(pdf_reader.pages)

    # --------- 以上为了获取页数 ---------

    # 重新创建文档并构建内容（保留第一页和其他内容）
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    doc.addPageTemplates(template)
    # 重新构建文档内容
    elements = []
    page_content = {
        "report_name": ["REPORT", "on", "SINGLE BLADE"],
        "report_table": [
            ["Company Name:", "Senvion Wind Technology Pvt Ltd"],
            ["BladeID:", blade_id],
            ["Serie Nr. :", "AGT_7979C/12_2"],
            ["Batch Quantity:", "1"],
            ["Total page:", total_pages],
            ["Printing date：", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
    }
    # 第一页内容
    create_first_page_content(elements, page_content=page_content)
    # 插入组件图片
    add_single_blade_component_image(elements, image_list)
    # 添加尾页说明
    normal_style = ParagraphStyle(name='Normal', fontName='SimSun', fontSize=12)
    elements.append(Paragraph("尾页说明内容。", normal_style))

    # 构建文档
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

    # 返回 PDF 数据
    response.write(buffer.getvalue())

    # 在这里添加清除本地图片逻辑
    try:
        for i_name in image_list:
            file_path = os.path.join(BASE_DIR, "report", 'temporary_img', f"{i_name}.png")

            os.remove(file_path)
            print(f"文件 {file_path} 删除成功！")
    except FileNotFoundError:
        print(f"文件 {file_path} 未找到！")
    except PermissionError:
        print(f"没有权限删除文件 {file_path}！")
    except Exception as e:
        print(f"删除文件时发生错误: {e}")
    finally:
        return response



# 异步保存图片到本地
async def async_save_image(image_base64, image_name):
    # 使用 asyncio.to_thread 将同步操作异步化
    await asyncio.to_thread(save_image_to_local, image_name, image_base64)

# 异步执行数据库查询
@sync_to_async
def get_image_data(blade_id):
    # 获取图片数据
    image_record = BladeSignImage.objects.filter(bldname=blade_id)
    serializer = BladeSignImageSerializer(image_record, many=True)
    return [item['signImg'] for item in serializer.data]

# 异步保存图片到本地
async def async_add_component_image(elements, image_info):
    # 使用 asyncio.to_thread 将同步操作异步化
    await asyncio.to_thread(add_component_image, elements, image_info)

# 获取单个叶片组件图片信息
def add_component_image(elements, image_info):
    image_path = os.path.join(BASE_DIR, "report", 'temporary_img', f"{image_info}.png")
    # 调用方法将本地的签名版本图片输入到pdf
    add_local_image_to_elements(elements, image_path)


# 单叶片报告下载接口(异步操作优化版--未调到最优)
@csrf_exempt
async def download_single_blade_report(request):
    # 解析请求数据
    data = request.body.decode('utf-8')
    json_data = json.loads(data)
    blade_id = json_data.get("blade_id")  # 获取叶片id
    component_image_list = json_data.get("image_list")  # 获取到组件图片名称
    if component_image_list:
        image_list = component_image_list
    else:
        # 异步获取图片数据
        image_base64_list = await get_image_data(blade_id)

        image_list = ["bladePhaseTable"]  # 只需存储图片名称，不要存储异步任务
        tasks = []  # 存储所有异步任务

        # 异步保存图片
        for index, ibl in enumerate(image_base64_list):
            task = async_save_image(ibl, f"sign_{index}")  # 获取任务
            tasks.append(task)  # 添加任务到任务列表中
            image_list.append(f"sign_{index}")

        # 等待所有图片保存任务完成
        await asyncio.gather(*tasks)

    # 使用 sync_to_async 包装生成 PDF 的同步操作
    a = time.time()
    pdf_content = await generate_pdf(blade_id, image_list)
    b = time.time()
    print(b -a , " generate pdf times")
    # 返回 PDF 数据
    response = HttpResponse(pdf_content, content_type='application/pdf')
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"SignalBladeReport_{timestamp}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


# 生成 PDF 的同步函数
async def generate_pdf(blade_id, image_list):
    # 查询数据
    buffer = io.BytesIO()

    # 注册字体
    pdfmetrics.registerFont(TTFont('SimSun', SimSun_path))
    pdfmetrics.registerFont(TTFont('calibri', calibri_path))
    pdfmetrics.registerFont(TTFont('calibrib', calibrib_path))

    # 创建文档
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    # 定义页面模板
    frame = Frame(1.5 * cm, 3 * cm, 18 * cm, 24 * cm, id='normal')
    # 这里的onPage只对首页有效
    template = PageTemplate(id='template', frames=frame, onPage=add_header_footer)
    doc.addPageTemplates(template)

    elements = []
    page_content = {
        "report_name": ["REPORT", "on", "SINGLE BLADE"],
        "report_table": [
            ["Company Name:", "Senvion Wind Technology Pvt Ltd"],
            ["Serie Nr. :", "AGT_7979C/12_2"],
            ["Batch Quantity:", "1"],
            ["Total page:", ""],
            ["Printing Time:", ""]
        ]
    }
    # 第一页内容
    create_first_page_content(elements, page_content=page_content)
    # 插入组件图片
    # add_single_blade_component_image(elements, image_list)
    tasks = []
    for image_info in image_list:
        add_task = async_add_component_image(elements, image_info)
        tasks.append(add_task)
    await asyncio.gather(*tasks)

    # 添加尾页说明
    normal_style = ParagraphStyle(name='Normal', fontName='SimSun', fontSize=12)

    # 构建文档，此处如果不指定onLaterPages，那么add_header_footer只有第一页生效
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

    pdf = buffer.getvalue()
    buffer.close()

    # 打开生成的 PDF，并读取页数
    pdf_reader = PdfReader(io.BytesIO(pdf))
    total_pages = len(pdf_reader.pages)
    # --------- 以上为了获取页数 ---------

    # 重新创建文档并构建内容（保留第一页和其他内容）
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    doc.addPageTemplates(template)
    # 重新构建文档内容
    elements = []
    page_content = {
        "report_name": ["REPORT", "on", "SINGLE BLADE"],
        "report_table": [
            ["Company Name:", "Senvion Wind Technology Pvt Ltd"],
            ["BladeID:", blade_id],
            ["Serie Nr. :", "AGT_7979C/12_2"],
            ["Batch Quantity:", "1"],
            ["Total page:", total_pages],
            ["Printing date：", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
    }
    # 第一页内容
    create_first_page_content(elements, page_content=page_content)
    # 插入组件图片
    add_single_blade_component_image(elements, image_list)

    # 构建文档
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

    pdf = buffer.getvalue()
    buffer.close()
    # 在这里添加清除本地图片逻辑
    try:
        for i_name in image_list:
            file_path = os.path.join(BASE_DIR, "report", 'temporary_img', f"{i_name}.png")

            os.remove(file_path)
            print(f"文件 {file_path} 删除成功！")
    except FileNotFoundError:
        print(f"文件 {file_path} 未找到！")
    except PermissionError:
        print(f"没有权限删除文件 {file_path}！")
    except Exception as e:
        print(f"删除文件时发生错误: {e}")

    return pdf






# 叶片类型报告下载接口
@csrf_exempt  # post请求需要 禁用CSRF保护
@api_view(['POST'])  # 只能post请求
def download_blade_type_report(request):
    data = request.body.decode('utf-8')
    json_data = json.loads(data)
    blade_type = json_data.get("bladeType")
    start_time_str = json_data.get("startTime")
    end_time_str = json_data.get("endTime")

    start_time_obj = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
    end_time_obj = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
    start_time_str = start_time_obj.strftime('%Y-%m-%d %H:%M:%S')
    end_time_str = end_time_obj.strftime('%Y-%m-%d %H:%M:%S')

    # 设置 response 和 buffer
    buffer = io.BytesIO()
    response = HttpResponse(content_type='application/pdf')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"SignalBladeReport_{timestamp}.pdf"
    response['Content-Type'] = 'application/pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # 注册字体
    pdfmetrics.registerFont(TTFont('SimSun', SimSun_path))
    pdfmetrics.registerFont(TTFont('calibri', calibri_path))
    pdfmetrics.registerFont(TTFont('calibrib', calibrib_path))

    # 创建文档
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    # 定义页面模板
    frame = Frame(1.5 * cm, 3 * cm, 18 * cm, 24 * cm, id='normal')
    template = PageTemplate(id='template', frames=frame, onPage=add_header_footer)
    doc.addPageTemplates(template)

    elements = []
    create_first_page_content(elements)
    # 插入图片
    image_list = ["bladeTypePhaseStatistic"]
    add_single_blade_component_image(elements, image_list)
    # 插入尾页说明
    normal_style = ParagraphStyle(name='Normal', fontName='SimSun', fontSize=12)
    elements.append(Paragraph("尾页说明内容。", normal_style))
    # 初次构建文档（先填充占位符）
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    # 获取生成的 PDF 数据
    pdf = buffer.getvalue()
    buffer.close()

    # 打开生成的 PDF，并读取页数
    pdf_reader = PdfReader(io.BytesIO(pdf))
    total_pages = len(pdf_reader.pages)

    # 重新创建文档并构建内容（保留第一页和其他内容）
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    doc.addPageTemplates(template)

    # 重新构建文档内容
    elements = []
    # 第一页内容
    page_content = {
        "report_name": ["REPORT", "on", "BLADE TYPE"],
        "report_table": [
            ["Company Name:", "Senvion Wind Technology Pvt Ltd"],
            ["Blade Type: ", blade_type],
            ["Serie Nr. :", "AGT_7979C/12_2"],
            ["Batch Quantity:", "1"],
            ["Total page:", total_pages],
            ["Time range: ", f"{start_time_str} - {end_time_str}"],
            ["Printing date：", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
    }

    # 更新第一页内容并插入
    create_first_page_content(elements, page_content=page_content)

    # 插入图片和尾页说明
    add_single_blade_component_image(elements, image_list)
    # elements.append(Paragraph("尾页说明内容。", normal_style))

    # 构建文档
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)

    # 返回 PDF 数据
    response.write(buffer.getvalue())
    return response


# 平整度报告下载接口
@csrf_exempt  # post请求需要 禁用CSRF保护
@api_view(['POST'])  # 只能post请求
def download_flatness_report(request):
    lang = request.META.get('HTTP_ACCEPT_LANGUAGE', 'zh')  # 默认值为 'zh'
    data = request.body.decode('utf-8')
    json_data = json.loads(data)
    print("........:", json_data)
    image_list = json_data.get("images")
    blade_id = json_data.get("blade_id", '')
    # 查询数据
    buffer = io.BytesIO()
    response = HttpResponse(content_type='application/pdf')

    # 获取当前日期和时间，格式化为字符串
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"SignalBladeReport_{timestamp}.pdf"
    response['Content-Type'] = 'application/pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # 注册字体
    pdfmetrics.registerFont(TTFont('SimSun', SimSun_path))
    pdfmetrics.registerFont(TTFont('calibri', calibri_path))
    pdfmetrics.registerFont(TTFont('calibrib', calibrib_path))

    # 创建文档
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    # 定义页面模板
    frame = Frame(1.5 * cm, 3 * cm, 18 * cm, 24 * cm, id='normal')
    # 这里的onPage只对首页有效
    template = PageTemplate(id='template', frames=frame, onPage=add_header_footer)
    doc.addPageTemplates(template)

    elements = []
    # 第一页内容
    create_first_page_content(elements)
    # 页面平整度表格
    add_flatness_table(elements, blade_id)
    # 插入组件图片
    add_single_blade_component_image(elements, image_list)

    # 添加尾页说明
    # normal_style = ParagraphStyle(name='Normal', fontName=font_str, fontSize=12)
    # elements.append(Paragraph("尾页说明内容。", normal_style))

    # 构建文档，此处如果不指定onLaterPages，那么add_header_footer只有第一页生效
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    # 获取生成的 PDF 数据
    pdf = buffer.getvalue()
    buffer.close()
    # 打开生成的 PDF，并读取页数
    pdf_reader = PdfReader(io.BytesIO(pdf))
    total_pages = len(pdf_reader.pages)

    # -------------------- 以上是为了获取页数 ---------

    # 重新创建文档并构建内容（保留第一页和其他内容）
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    doc.addPageTemplates(template)
    # 重新构建文档内容
    elements = []

    # 更新第一页内容并插入
    page_content = {
        "report_name": ["REPORT", "on", "Flatness"],
        "report_table": [
            ["Company Name:", "Senvion Wind Technology Pvt Ltd"],
            ["BladeID:", blade_id],
            ["Serie Nr. :", "AGT_7979C/12_2"],
            ["Batch Quantity:", "1"],
            ["Total page:", total_pages],
            ["Printing date：", datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        ]
    }
    create_first_page_content(elements, page_content=page_content)

    # 页面平整度表格
    add_flatness_table(elements, blade_id, lang=lang)

    # 插入组件图片
    add_single_blade_component_image(elements, image_list)

    # 添加尾页说明
    normal_style = ParagraphStyle(name='Normal', fontName='SimSun', fontSize=12)
    elements.append(Paragraph("尾页说明内容。", normal_style))

    # 构建文档
    doc.build(elements, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    # 返回 PDF 数据
    response.write(buffer.getvalue())

    # 在这里添加清除本地图片逻辑
    try:
        for i_name in image_list:
            file_path = os.path.join(BASE_DIR, "report", 'temporary_img', f"{i_name}.png")

            os.remove(file_path)
            print(f"文件 {file_path} 删除成功！")
    except FileNotFoundError:
        print(f"文件 {file_path} 未找到！")
    except PermissionError:
        print(f"没有权限删除文件 {file_path}！")
    except Exception as e:
        print(f"删除文件时发生错误: {e}")
    finally:
        return response


def discard_add_header_footer(c, doc):
    c.saveState()

    # c.setFillColor(colors.lightgrey)  # 选择您想要的填充颜色
    # c.rect(1.5 * cm, 3 * cm, 18 * cm, 24 * cm, fill=0)  # 确保填充整个 Frame 的大小

    # 设置页眉
    c.setFont("Helvetica-Bold", 18)  # 使用内置的 Helvetica 加粗字体
    c.setFillColor(colors.lightblue)
    c.drawString(1.5 * cm, 28 * cm, "SIMATIC BATCH", )
    c.setFont("SimSun", 18)
    c.drawString(17 * cm, 28 * cm, "生产报表")

    # 画页头横线
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.black)  # Set the line color to blue
    c.line(1.5 * cm, 27.5 * cm, 19.5 * cm, 27.5 * cm)

    # 页脚
    c.setFont("SimSun", 8)
    c.setFillColor(colors.lightblue)
    c.drawString(18.5 * cm, 1.5 * cm, f"page {doc.page}")

    # 画页底横线
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.black)  # Set the line color to blue
    c.line(1.5 * cm, 2 * cm, 19.5 * cm, 2 * cm)

    c.restoreState()


def add_header_footer(c, doc):
    c.saveState()

    # c.setFillColor(lightgrey)
    # c.rect(1.5 * cm, 3 * cm, 18 * cm, 24 * cm, fill=1)

    # 设置图片路径
    image_path = os.path.join(BASE_DIR, "statics", 'image', "haitch.png")
    image_width = 2 * cm  # 图片宽度
    image_height = 2 * cm  # 图片高度
    c.drawImage(image_path, 1.5 * cm, 27.2 * cm, width=image_width, height=image_height)

    gray_color = colors.Color(0.5, 0.5, 0.5)  # 创建一个中等灰色的颜色
    # 设置中文字体为 SimSun
    c.setFont("SimSun", 10)  # 使用 SimSun 字体，设置大小为 10
    chinese_text = "以质为本、诚信为人、顾客至上、不断创新"
    # 计算中文文本的宽度
    text_width_chinese = c.stringWidth(chinese_text, "SimSun", 10)
    # 设置文本的右对齐位置
    right_margin = 19.5 * cm  # 右边距
    x_position_chinese = right_margin - text_width_chinese  # 右对齐
    c.setFillColor(gray_color)
    c.drawString(x_position_chinese, 27.8 * cm, chinese_text)  # 第一行中文

    # 设置英文文字的字体为 Helvetica
    c.setFont("calibri", 10)  # 设置英文的字体和大小
    english_text = "Quality & Integrity Oriented, Customer first, Continuous Innovation"
    # 计算英文文本的宽度
    text_width_english = c.stringWidth(english_text, "Helvetica", 10)
    # 设置英文文本的右对齐位置
    x_position_english = right_margin - text_width_english  # 右对齐
    c.drawString(x_position_english, 27.3 * cm, english_text)  # 第二行英文

    # 画页头横线
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.black)  # 设置线条颜色
    c.line(1.5 * cm, 27 * cm, 19.5 * cm, 27 * cm)

    # 页脚
    c.setFont("calibri", 8)

    # 左侧：公司名称
    c.setFillColor(colors.black)  # 设置颜色为 lightblue
    c.drawString(1.5 * cm, 1.5 * cm, "HAITCH Co., Ltd.")  # 左侧文字

    # 中间：页码
    c.setFillColor(colors.black)  # 设置页码颜色为黑色
    page_number_text = f"page {doc.page}"
    page_number_width = c.stringWidth(page_number_text, "calibri", 8)
    center_x = 10 * cm - page_number_width / 2  # 计算页面中间位置
    c.drawString(center_x, 1.5 * cm, page_number_text)  # 中间页码

    # 右侧：当前日期
    c.setFillColor(colors.black)  # 设置日期的颜色为黑色
    current_date = datetime.now().strftime("%d.%m.%Y")  # 获取当前日期
    date_width = c.stringWidth(current_date, "calibri", 8)
    c.drawString(19.5 * cm - date_width, 1.5 * cm, current_date)  # 右侧日期

    # 画页底横线
    c.setLineWidth(0.5)
    c.setStrokeColor(colors.black)
    c.line(1.5 * cm, 2 * cm, 19.5 * cm, 2 * cm)

    c.restoreState()


# 获取报告响应数据
def create_all_of_report_info(filter_data):
    # todo:根据filter_data中的信息进行过滤查询
    print(filter_data, ' : filter data')
    blade_name = filter_data.get("bladeName")
    blade_type = filter_data.get("bladeType")
    start_time = filter_data.get("startTime")
    end_time = filter_data.get("endTime")
    operator = filter_data.get("operator")
    input_text = filter_data.get("inputText")

    # 查询数据库对象
    err_obj = ErrMsg.objects.all()
    blade_record_obj = BladeRecord.objects.all()
    user_log_obj = UserLog.objects.all()
    snap_obj = DMMSnap.objects.all()

    # 过滤查询
    if blade_name:
        blade_record_obj = blade_record_obj.filter(bldname=filter_data.get("bladeName"))
        snap_obj = snap_obj.select_related('bldrecord').filter(bldrecord__bldname=blade_name)
    if blade_type:
        blade_record_obj = blade_record_obj.filter(bldtype=blade_type)
        snap_obj = snap_obj.select_related('bldrecord').filter(bldrecord__bldtype=blade_type)
    if start_time:
        err_obj = err_obj.filter(msgdt__gt=start_time)
        user_log_obj = user_log_obj.filter(dt__gt=start_time)
        snap_obj = snap_obj.filter(dt__gt=start_time)

    if end_time:
        err_obj = err_obj.filter(msgdt__lt=end_time)
        user_log_obj = user_log_obj.filter(dt__lt=end_time)
        snap_obj = snap_obj.filter(dt__lt=end_time)

    if operator:
        user_log_obj = user_log_obj.filter(name=operator)
        snap_obj = snap_obj.filter(username=operator)

    if input_text:
        err_obj = err_obj.filter(msgtext__icontains=input_text)

    # 告警信息
    error_data = ErrMsgSerializer(instance=err_obj, many=True)
    # 叶片记录
    blade_record_data = BladeRecordSerializer(instance=blade_record_obj, many=True)
    # 操作者信息
    operator_data = UserLogSerializer(instance=user_log_obj, many=True)
    # 快照信息
    snapshot_data = DMMSnapSerializer(instance=snap_obj, many=True)

    res_dict = {
        "errorData": error_data.data,
        "bladeRecordData": blade_record_data.data,
        "operatorData": operator_data.data,
        "snapshotData": snapshot_data.data
    }

    # 将查询到的数据存入redis中，下载报告直接读取
    res_str = json.dumps(res_dict)
    redis_client.set("filter_report_data", res_str)

    return res_dict


# 构造封面说明信息表格
def create_cover_table(first_page_data):
    a_table = Table(first_page_data, colWidths=[100, 200])

    # 设置表格样式
    a_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  # 内容左对齐
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),  # 第一列（包括表头）水平居中
        ('FONTNAME', (0, 0), (-1, 0), 'calibri'),  # 字体设置
        ('FONTNAME', (0, 1), (-1, -1), 'calibri'),  # 字体设置
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),  # 设置网格线可见且为黑色
    ]))

    # 交替行背景色：每隔一行设置背景颜色
    for i in range(1, len(first_page_data)):
        if i % 2 == 1:
            a_table.setStyle(TableStyle([
                ('BACKGROUND', (0, i), (-1, i), colors.lightgrey)  # 奇数行设置灰色背景
            ]))

    return  a_table


def create_first_page_content(elements, page_content=None):
    if page_content:
        report_name = page_content.get("report_name")
        report_table = page_content.get("report_table")
    else:
        report_name = ''
        report_table = [["打印日期：", ""]]

    elements.append(Spacer(1, 50))  # 1英寸的宽度，24点的垂直间距

    # 客户logo
    image_path = os.path.join(BASE_DIR, "statics", 'image', "agent_logo.png")
    img = Image(image_path, width=350, height=100)
    elements.append(img)

    elements.append(Spacer(1, 50))  # 1英寸的宽度，24点的垂直间距
    # 添加报告名称
    # title_style = ParagraphStyle(name='TitleStyle', fontName='SimSun', fontSize=36, alignment=1, blod=True)  # alignment=1 表示居中
    title_style = ParagraphStyle(name='TitleStyle', fontName='calibrib', fontSize=36, alignment=1, blod=True)  # alignment=1 表示居中

    if not report_name:
        report_name = ["", "Report", ""]
    for report_text in report_name:
        title = Paragraph(report_text, title_style)
        elements.append(title)
        elements.append(Spacer(1, 50))

    elements.append(Spacer(1, 100))  # 1英寸的宽度，24点的垂直间距

    a_data = report_table

    a_table = create_cover_table(a_data)
    elements.append(a_table)

    elements.append(PageBreak())

    return a_data


def add_operator_table(elements):
    # 获取redis中的缓存数据
    msg = redis_client.get("filter_report_data")
    msg = msg.decode('utf-8')
    report_data = json.loads(msg)

    operator_data = report_data.get("operatorData")
    if not operator_data:
        return
    # 添加一个Spacer对象作为页面顶部的边距（可选）
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距

    # 定义段落样式
    normal_style = getSampleStyleSheet()  # 获取预定义的样式集
    pag_style = normal_style['BodyText']  # 选择一个基础样式作为起点
    pag_style.fontName = 'SimSun'  # 设置字体
    pag_style.fontSize = 12  # 设置字体大小
    pag_style.spaceBefore = 12  # 设置段前间距
    pag_style.spaceAfter = 12  # 设置段后间距
    pag_style.textColor = colors.darkblue  # 设置文字颜色
    pag_style.leftIndent = -10  # 段落左侧缩进，控制段落文本与左边缘的距离。

    elements.append(Paragraph("操作员登录/登出记录:", pag_style))


    a_data = [["ID", "账号名", "登录/登出", "时间"]]
    for info in operator_data:
        a_data.append([info.get("id"), info.get("name"), info.get("loginout"), info.get("dt")])

    a_table = Table(a_data, colWidths=[80, 80, 100, 200])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        # ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        # ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
        ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    a_table.setStyle(style)

    elements.append(a_table)
    a_table.repeatRows = 1  # 设定需要重复的行数（表头行数）
    # 添加一个Spacer对象
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距
    # elements.append(PageBreak())


# 原版一排显示（作废）
def discard_add_flatness_table(elements, blade_id):
    # 从数据库获取数据
    flatness_data = FlatnessReport.objects.filter(bladeId=blade_id).values('holeAngle', 'flatness')
    print(flatness_data)
    # 序列化查询结果
    serializer = FlatnessReportSerializer(flatness_data, many=True)
    if not serializer:
        return
    # 添加一个Spacer对象作为页面顶部的边距（可选）
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距

    # 定义段落样式
    normal_style = getSampleStyleSheet()  # 获取预定义的样式集
    pag_style = normal_style['BodyText']  # 选择一个基础样式作为起点
    pag_style.fontName = 'SimSun'  # 设置字体
    pag_style.fontSize = 12  # 设置字体大小
    pag_style.spaceBefore = 12  # 设置段前间距
    pag_style.spaceAfter = 12  # 设置段后间距
    pag_style.textColor = colors.darkblue  # 设置文字颜色
    pag_style.leftIndent = -10  # 段落左侧缩进，控制段落文本与左边缘的距离。

    elements.append(Paragraph("各角度孔平整度数据表:", pag_style))


    a_data = [["角度", "平整度"]]
    for info in serializer.data:
        print("...", info)
        a_data.append([info.get("holeAngle"), info.get("flatness")])

    a_table = Table(a_data, colWidths=[80, 80])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        # ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        # ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
        ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    a_table.setStyle(style)

    elements.append(a_table)
    a_table.repeatRows = 1  # 设定需要重复的行数（表头行数）
    # 添加一个Spacer对象
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距
    # elements.append(PageBreak())


# 三列并排显示
def add_flatness_table1(elements, blade_id):
    # 从数据库获取数据
    flatness_data = FlatnessReport.objects.filter(bladeId=blade_id).values('holeAngle', 'flatness')
    print(flatness_data)

    # 序列化查询结果
    serializer = FlatnessReportSerializer(flatness_data, many=True)
    if not serializer:
        return

    # 添加一个Spacer对象作为页面顶部的边距（可选）
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距

    # 定义段落样式
    normal_style = getSampleStyleSheet()  # 获取预定义的样式集
    pag_style = normal_style['BodyText']  # 选择一个基础样式作为起点
    pag_style.fontName = 'SimSun'  # 设置字体
    pag_style.fontSize = 12  # 设置字体大小
    pag_style.spaceBefore = 12  # 设置段前间距
    pag_style.spaceAfter = 12  # 设置段后间距
    pag_style.textColor = colors.darkblue  # 设置文字颜色
    pag_style.leftIndent = -10  # 段落左侧缩进，控制段落文本与左边缘的距离。

    elements.append(Paragraph("各角度孔平整度数据表:", pag_style))

    # 分组数据，按列展示，每列10项数据
    columns = 3  # 定义列数
    rows_per_column = len(serializer.data) // columns + (1 if len(serializer.data) % columns != 0 else 0)

    a_data = []

    # 表头行：每列显示"角度"和"平整度"
    header_row = ['角度', '平整度', '角度', '平整度', '角度', '平整度']
    a_data.append(header_row)

    # 为了每列从数据中提取相应的部分
    for row in range(rows_per_column):
        row_data = []
        for col in range(columns):  # 每列包含多个数据项，列数为3
            index = row + col * rows_per_column
            if index < len(serializer.data):
                info = serializer.data[index]
                # 在每一列中加入"角度"和"平整度"
                row_data.append(info.get('holeAngle'))  # 显示角度
                row_data.append(info.get('flatness'))  # 显示平整度
            else:
                row_data.append("")  # 如果数据不足，填充空值
                row_data.append("")  # 填充空白的平整度单元格
        a_data.append(row_data)

    # 设置表格列宽，确保表头和内容列宽一致
    col_widths = [70, 70, 70, 70, 70, 70]  # 所有列宽度一致
    a_table = Table(a_data, colWidths=col_widths)  # 使用统一的列宽

    # 设置表格样式
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # 设置表头背景色
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # 设置表头文字颜色
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 水平居中
        ('VERTALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # 表头垂直居中
        ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),  # 表头字体
        ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),  # 表体字体
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # 统一字体大小，防止表头过大
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),  # 表头底部间距
        ('TOPPADDING', (0, 1), (-1, -1), 6),  # 表体顶部间距，确保一致
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # 设置网格线
    ])
    a_table.setStyle(style)

    elements.append(a_table)
    a_table.repeatRows = 1  # 设定需要重复的行数（表头行数）

    # 添加一个Spacer对象
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距
    # elements.append(PageBreak())  # 可以根据需要添加分页


# 三排添加间隔
def add_flatness_table(elements, blade_id, lang="zh"):
    if lang == "zh":
        font_str = "SimSun"
    else:
        font_str = "calibri"
    # 从数据库获取数据
    flatness_data = FlatnessReport.objects.filter(bladeId=blade_id).values('holeAngle', 'flatness')

    # 序列化查询结果
    serializer = FlatnessReportSerializer(flatness_data, many=True)
    if not serializer:
        return

    # 添加一个Spacer对象作为页面顶部的边距（可选）
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距

    # 定义段落样式
    normal_style = getSampleStyleSheet()  # 获取预定义的样式集
    pag_style = normal_style['BodyText']  # 选择一个基础样式作为起点
    pag_style.fontName = font_str  # 设置字体
    pag_style.fontSize = 12  # 设置字体大小
    pag_style.spaceBefore = 12  # 设置段前间距
    pag_style.spaceAfter = 12  # 设置段后间距
    pag_style.textColor = colors.darkblue  # 设置文字颜色
    pag_style.leftIndent = -10  # 段落左侧缩进，控制段落文本与左边缘的距离。

    ts = FlatnessReportT.get(lang, FlatnessReportT['zh'])

    elements.append(Paragraph(ts["flatness_table"], pag_style))
    # 表头行：每两列显示"角度"和"平整度"，并在后面插入一个空白列作为间隔
    header_row = [ts["angle"], ts["flatness"], '', ts["angle"], ts["flatness"], '', ts["angle"], ts["flatness"]]

    # 初始化表格数据
    a_data = [header_row]

    # 填充数据，按顺序每次加入“角度”和“平整度”，然后插入空白列
    for i in range(0, len(serializer.data), 3):  # 每3个数据作为一组
        row_data = []

        # 第一组：角度、平整度、空白列
        if i < len(serializer.data):
            row_data.append(serializer.data[i].get('holeAngle'))  # 角度
            row_data.append(serializer.data[i].get('flatness'))  # 平整度
            row_data.append("")  # 空白列作为间隔

        # 第二组：角度、平整度、空白列
        if i + 1 < len(serializer.data):
            row_data.append(serializer.data[i + 1].get('holeAngle'))  # 角度
            row_data.append(serializer.data[i + 1].get('flatness'))  # 平整度
            row_data.append("")  # 空白列作为间隔

        # 第三组：角度、平整度、空白列
        if i + 2 < len(serializer.data):
            row_data.append(serializer.data[i + 2].get('holeAngle'))  # 角度
            row_data.append(serializer.data[i + 2].get('flatness'))  # 平整度

        a_data.append(row_data)

    # 设置表格列宽，确保表头和内容列宽一致，并留出空白间隔
    col_widths = [70, 70, 10, 70, 70, 10, 70, 70]  # 设置空白列宽度较小，10px，确保它不占用太多空间

    a_table = Table(a_data, colWidths=col_widths)  # 使用统一的列宽

    # 设置表格样式
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),  # 设置表头背景色
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),  # 设置表头文字颜色
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 水平居中
        ('VERTALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # 表头垂直居中
        ('FONTNAME', (0, 0), (-1, 0), font_str),  # 表头字体
        ('FONTNAME', (0, 1), (-1, -1), font_str),  # 表体字体
        ('FONTSIZE', (0, 0), (-1, -1), 10),  # 统一字体大小，防止表头过大
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),  # 表头底部间距
        ('TOPPADDING', (0, 1), (-1, -1), 6),  # 表体顶部间距，确保一致
        ('GRID', (0, 0), (-1, -1), 1, colors.black),  # 设置网格线

        # 隐藏空白列的上下边框
        ('LINEABOVE', (2, 1), (2, -1), 0, colors.white),  # 隐藏空白列的上边框
        ('LINEBELOW', (2, 1), (2, -1), 0, colors.white),  # 隐藏空白列的下边框
        ('LINEABOVE', (5, 1), (5, -1), 0, colors.white),  # 隐藏第二个空白列的上边框
        ('LINEBELOW', (5, 1), (5, -1), 0, colors.white),  # 隐藏第二个空白列的下边框

        # 隐藏空白列的表头背景色和边框
        ('BACKGROUND', (2, 0), (2, 0), colors.white),  # 隐藏第3列（索引从0开始）的表头背景色
        ('LINEABOVE', (2, 0), (2, 0), 0, colors.white),  # 隐藏第3列的表头上边框
        ('LINEBELOW', (2, 0), (2, 0), 0, colors.white),  # 隐藏第3列的表头下边框

        ('BACKGROUND', (5, 0), (5, 0), colors.white),  # 隐藏第6列（索引从0开始）的表头背景色
        ('LINEABOVE', (5, 0), (5, 0), 0, colors.white),  # 隐藏第6列的表头上边框
        ('LINEBELOW', (5, 0), (5, 0), 0, colors.white),  # 隐藏第6列的表头下边框
    ])

    a_table.setStyle(style)

    elements.append(a_table)
    a_table.repeatRows = 1  # 设定需要重复的行数（表头行数）

    # 添加一个Spacer对象
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距
    # elements.append(PageBreak())  # 可以根据需要添加分页


def add_warning_log_table(elements):
    # 获取redis中的缓存数据
    msg = redis_client.get("filter_report_data")
    msg = msg.decode('utf-8')
    report_data = json.loads(msg)

    error_data = report_data.get("errorData")
    if not error_data:
        return
    # 添加一个Spacer对象作为页面顶部的边距（可选）
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距

    # 定义段落样式
    normal_style = getSampleStyleSheet()  # 获取预定义的样式集
    pag_style = normal_style['BodyText']  # 选择一个基础样式作为起点
    pag_style.fontName = 'SimSun'  # 设置字体
    pag_style.fontSize = 12  # 设置字体大小
    pag_style.spaceBefore = 12  # 设置段前间距
    pag_style.spaceAfter = 12  # 设置段后间距
    pag_style.textColor = colors.darkblue  # 设置文字颜色
    pag_style.leftIndent = -10  # 段落左侧缩进，控制段落文本与左边缘的距离。

    elements.append(Paragraph("告警信息记录:", pag_style))

    a_data = [["ID", "地址编号", "告警类型", "告警时间", "告警信息"]]
    for info in error_data:
        info_list = [
            info.get("errorid"),
            info.get("addressid"),
            info.get("msgtype"),
            info.get("msgdt"),
            info.get("msgtext")
        ]
        a_data.append(info_list)

    a_table = Table(a_data, colWidths=[30, 60, 50, 200, 150])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        # ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        # ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        # ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
        ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
        # ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    a_table.setStyle(style)

    elements.append(a_table)
    a_table.repeatRows = 1  # 设定需要重复的行数（表头行数）
    # 添加一个Spacer对象
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距
    # elements.append(PageBreak())


def add_blade_log_table(elements):
    # 获取redis中的缓存数据
    msg = redis_client.get("filter_report_data")
    msg = msg.decode('utf-8')
    report_data = json.loads(msg)

    blade_record_data = report_data.get("bladeRecordData")
    if not blade_record_data:
        return
    # 添加一个Spacer对象作为页面顶部的边距（可选）
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距

    # 定义段落样式
    normal_style = getSampleStyleSheet()  # 获取预定义的样式集
    pag_style = normal_style['BodyText']  # 选择一个基础样式作为起点
    pag_style.fontName = 'SimSun'  # 设置字体
    pag_style.fontSize = 12  # 设置字体大小
    pag_style.spaceBefore = 12  # 设置段前间距
    pag_style.spaceAfter = 12  # 设置段后间距
    pag_style.textColor = colors.darkblue  # 设置文字颜色
    pag_style.leftIndent = -10  # 段落左侧缩进，控制段落文本与左边缘的距离。

    elements.append(Paragraph("叶片上架记录:", pag_style))

    a_data = [["ID", "叶片名称", "叶片类型", "上架时间", "下架时间"]]
    for info in blade_record_data:
        info_list = [
            info.get("id"),
            info.get("bldname"),
            info.get("bldtype"),
            info.get("dt"),
            info.get("dtleave")
        ]
        a_data.append(info_list)

    a_table = Table(a_data, colWidths=[20, 50, 50, 200, 150])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        # ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        # ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        # ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
        ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
        # ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        # ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    a_table.setStyle(style)

    elements.append(a_table)
    a_table.repeatRows = 1  # 设定需要重复的行数（表头行数）
    # 添加一个Spacer对象
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距
    # elements.append(PageBreak())


# 横向排版
def add_snapshot_table(elements):
    # 获取redis中的缓存数据
    msg = redis_client.get("filter_report_data")
    msg = msg.decode('utf-8')
    report_data = json.loads(msg)

    blade_record_data = report_data.get("snapshotData")
    if not blade_record_data:
        return
    # 添加一个Spacer对象作为页面顶部的边距（可选）
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距

    # 定义段落样式
    normal_style = getSampleStyleSheet()  # 获取预定义的样式集
    pag_style = normal_style['BodyText']  # 选择一个基础样式作为起点
    pag_style.fontName = 'SimSun'  # 设置字体
    pag_style.fontSize = 12  # 设置字体大小
    pag_style.spaceBefore = 12  # 设置段前间距
    pag_style.spaceAfter = 12  # 设置段后间距
    pag_style.textColor = colors.darkblue  # 设置文字颜色
    pag_style.leftIndent = -10  # 段落左侧缩进，控制段落文本与左边缘的距离。

    elements.append(Paragraph("快照日志记录:", pag_style))

    # 增加定义一个表头样式
    normal_style = normal_style['Normal']
    paragraph_style = ParagraphStyle(name='MyStyle', parent=normal_style, fontSize=12)

    a_data = [["ID", "时间", "操作员", Paragraph("bldMode"), Paragraph("bldrecord"),
               Paragraph("program"),
               Paragraph("prgStep"), Paragraph("saddleMoveDir", paragraph_style),
               Paragraph("posSaddleExist"),Paragraph("posSaddlePos")]]
    for info in blade_record_data:
        info_list = [
            info.get("id"),
            info.get("dt"),
            info.get("username"),
            info.get("bldMode"),
            info.get("bldrecord"),
            info.get("program"),
            info.get("prgStep"),
            info.get("saddleMoveDir"),
            info.get("posSaddleExist"),
            info.get("posSaddlePos")
        ]
        a_data.append(info_list)
    col_list = [20, 140, 40, 40, 40, 40, 40, 60, 50, 50]
    a_table = Table(a_data, colWidths=col_list)
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),  # 表头垂直居中
        ('FONTNAME', (0, 0), (-1, 0), 'SimSun'),
        ('FONTNAME', (0, 1), (-1, -1), 'SimSun'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ])
    a_table.setStyle(style)

    elements.append(a_table)
    a_table.repeatRows = 1  # 设定需要重复的行数（表头行数）
    # 添加一个Spacer对象
    elements.append(Spacer(1, 10))  # 1英寸的宽度，24点的垂直间距
    # elements.append(PageBreak())


def add_blade_component_image(elements):
    component_list = ["bladePhaseTable", "bladeTypePhaseStatistic"]
    for component in component_list:
        image_path = os.path.join(BASE_DIR, "report", 'temporary_img', f"{component}.png")

        print(f"Image path: {image_path}")

        if os.path.exists(image_path):
            img = Image(image_path)
            img.hAlign = 'CENTER'  # 设置图片水平居中
            # 获取框架的最大尺寸
            max_width = 18 * cm
            max_height = 24 * cm

            # 计算实际图片宽高
            img_width = img.imageWidth
            img_height = img.imageHeight

            print(f"Original image size: {img_width} x {img_height}")

            # 计算缩放比例
            width_ratio = max_width / img_width
            height_ratio = max_height / img_height
            scaling_factor = min(width_ratio, height_ratio)

            # 根据缩放比例调整图片尺寸
            img.width = img_width * scaling_factor
            img.height = img_height * scaling_factor
            img.drawWidth = img_width * scaling_factor
            img.drawHeight = img_height * scaling_factor

            print(f"Adjusted image size: {img.width} x {img.height}")
            elements.append(img)  # 将图片添加到元素列表
        else:
            print("Image not found!")


def add_blade_hole_image(elements):
    image_path = os.path.join(BASE_DIR, "report", 'temporary_img', "check_sign.png")

    print(f"Image path: {image_path}")

    if os.path.exists(image_path):
        img = Image(image_path)
        img.hAlign = 'CENTER'  # 设置图片水平居中
        # 获取框架的最大尺寸
        max_width = 18 * cm
        max_height = 24 * cm

        # 计算实际图片宽高
        img_width = img.imageWidth
        img_height = img.imageHeight

        print(f"Original image size: {img_width} x {img_height}")

        # 计算缩放比例
        width_ratio = max_width / img_width
        height_ratio = max_height / img_height
        scaling_factor = min(width_ratio, height_ratio)

        # 根据缩放比例调整图片尺寸
        img.width = img_width * scaling_factor
        img.height = img_height * scaling_factor
        img.drawWidth = img_width * scaling_factor
        img.drawHeight = img_height * scaling_factor

        print(f"Adjusted image size: {img.width} x {img.height}")

        elements.append(img)  # 将图片添加到元素列表

        return img
    else:
        print("Image not found!")


def old_add_signature_image(elements):
    normal_style = ParagraphStyle(name='Normal', fontName='SimSun', fontSize=12)
    elements.append(Paragraph("操作员签名: ", normal_style))
    image_path = os.path.join(BASE_DIR, "report", 'temporary_img', "operator_sign_image.png")

    print(f"Image path: {image_path}")

    if os.path.exists(image_path):
        img = Image(image_path)
        img.hAlign = 'LEFT'  # 设置图片水平居中
        # 获取框架的最大尺寸
        max_width = 6 * cm
        max_height = 8 * cm

        # 计算实际图片宽高
        img_width = img.imageWidth
        img_height = img.imageHeight

        print(f"Original image size: {img_width} x {img_height}")

        # 计算缩放比例
        width_ratio = max_width / img_width
        height_ratio = max_height / img_height
        scaling_factor = min(width_ratio, height_ratio)

        # 根据缩放比例调整图片尺寸
        img.width = img_width * scaling_factor
        img.height = img_height * scaling_factor
        img.drawWidth = img_width * scaling_factor
        img.drawHeight = img_height * scaling_factor

        print(f"Adjusted image size: {img.width} x {img.height}")

        elements.append(img)  # 将图片添加到元素列表

        # return img
    else:
        print("Image not found!")

    normal_style = ParagraphStyle(name='Normal', fontName='SimSun', fontSize=12)
    elements.append(Paragraph("质检员签名: ", normal_style))
    image_path = os.path.join(BASE_DIR, "report", 'temporary_img', "inspector_sign_image.png")

    print(f"Image path: {image_path}")

    if os.path.exists(image_path):
        img = Image(image_path)
        img.hAlign = 'LEFT'  # 设置图片水平居中
        # 获取框架的最大尺寸
        max_width = 6 * cm
        max_height = 8 * cm

        # 计算实际图片宽高
        img_width = img.imageWidth
        img_height = img.imageHeight

        print(f"Original image size: {img_width} x {img_height}")

        # 计算缩放比例
        width_ratio = max_width / img_width
        height_ratio = max_height / img_height
        scaling_factor = min(width_ratio, height_ratio)

        # 根据缩放比例调整图片尺寸
        img.width = img_width * scaling_factor
        img.height = img_height * scaling_factor
        img.drawWidth = img_width * scaling_factor
        img.drawHeight = img_height * scaling_factor

        print(f"Adjusted image size: {img.width} x {img.height}")

        elements.append(img)  # 将图片添加到元素列表

        # return img
    else:
        print("Image not found!")


def add_signature_image(elements):
    # 创建一个ParagraphStyle并指定字体为 SimSun
    normal_style = ParagraphStyle(name='Normal', fontName='SimSun', fontSize=12)

    # 创建一个列表，包含操作员签名和质检员签名
    signature_data = [
        [Paragraph("操作员签名:", normal_style), Spacer(1, 5), Paragraph("质检员签名:", normal_style)],  # 文字之间的间距
        [get_image_element("operator_sign_image.png"), Spacer(1, 20), get_image_element("inspector_sign_image.png")]
        # 图片之间的间距
    ]

    # 创建一个表格，调整列宽来确保签名和图片在同一行
    table = Table(signature_data, colWidths=[5 * cm, 5 * cm, 5 * cm], rowHeights=[1 * cm, 3 * cm])

    # 设置表格样式
    table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 对齐表格中的内容
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # 垂直居中
        # ('LINEABOVE', (0, 0), (-1, 0), 1, colors.black),  # 上边框
        # ('LINEBELOW', (0, -1), (-1, -1), 1, colors.black),  # 下边框
        # ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),  # 内部网格
        # ('LINEBEFORE', (0, 0), (-1, -1), 0.5, colors.black),  # 左边框
        # ('LINEAFTER', (0, 0), (-1, -1), 0.5, colors.black)  # 右边框
    ]))

    # 添加标题
    # elements.append(Paragraph("操作员签名和质检员签名", normal_style))  # 添加表头
    elements.append(Spacer(1, 12))  # 添加间距
    elements.append(table)  # 将表格添加到元素列表


def get_image_element(image_name):
    # 设置图片路径
    image_path = os.path.join(BASE_DIR, "report", 'temporary_img', image_name)
    print(f"Image path: {image_path}")

    if os.path.exists(image_path):
        img = Image(image_path)
        img.hAlign = 'CENTER'  # 设置图片水平居中

        # 获取框架的最大尺寸
        max_width = 6 * cm
        max_height = 8 * cm

        # 计算实际图片宽高
        img_width = img.imageWidth
        img_height = img.imageHeight
        print(f"Original image size: {img_width} x {img_height}")

        # 计算缩放比例
        width_ratio = max_width / img_width
        height_ratio = max_height / img_height
        scaling_factor = min(width_ratio, height_ratio)

        # 根据缩放比例调整图片尺寸
        img.width = img_width * scaling_factor
        img.height = img_height * scaling_factor
        img.drawWidth = img_width * scaling_factor
        img.drawHeight = img_height * scaling_factor

        print(f"Adjusted image size: {img.width} x {img.height}")

        return img
    else:
        print("Image not found!")
        return None


def add_user_login_chart_image(elements):
    image_path = os.path.join(BASE_DIR, "report", 'temporary_img', "user_login_chart.png")

    print(f"Image path: {image_path}")

    if os.path.exists(image_path):
        img = Image(image_path)
        img.hAlign = 'CENTER'  # 设置图片水平居中
        # 获取框架的最大尺寸
        max_width = 9 * cm
        max_height = 12 * cm

        # 计算实际图片宽高
        img_width = img.imageWidth
        img_height = img.imageHeight

        print(f"Original image size: {img_width} x {img_height}")

        # 计算缩放比例
        width_ratio = max_width / img_width
        height_ratio = max_height / img_height
        scaling_factor = min(width_ratio, height_ratio)

        # 根据缩放比例调整图片尺寸
        img.width = img_width * scaling_factor
        img.height = img_height * scaling_factor
        img.drawWidth = img_width * scaling_factor
        img.drawHeight = img_height * scaling_factor

        print(f"Adjusted image size: {img.width} x {img.height}")

        elements.append(img)  # 将图片添加到元素列表

        return img
    else:
        print("Image not found!")


# 获取单个叶片组件图片信息
def add_single_blade_component_image(elements, image_list):
    for i in image_list:
        image_path = os.path.join(BASE_DIR, "report", 'temporary_img', f"{i}.png")
        # 调用方法将本地的签名版本图片输入到pdf
        add_local_image_to_elements(elements, image_path)



def add_local_image_to_elements(elements, image_path):
    print("..将本地的图片添加到elements中 : ", image_path)
    if os.path.exists(image_path):
        img = Image(image_path)
        img.hAlign = 'CENTER'  # 设置图片水平居中
        # 获取框架的最大尺寸
        max_width = 18 * cm
        max_height = 24 * cm

        # 计算实际图片宽高
        img_width = img.imageWidth
        img_height = img.imageHeight

        # 计算缩放比例
        width_ratio = max_width / img_width
        height_ratio = max_height / img_height
        scaling_factor = min(width_ratio, height_ratio)

        # 根据缩放比例调整图片尺寸
        img.width = img_width * scaling_factor
        img.height = img_height * scaling_factor
        img.drawWidth = img_width * scaling_factor
        img.drawHeight = img_height * scaling_factor

        elements.append(img)  # 将图片添加到元素列表
    else:
        print(image_path, " local Image not found!")

# 将base64的图片字符串转换为图片保存到本地
def save_image_to_local(image_name, image_str):
    print("开始将读取到的数据库图片转存本地: ", image_name)

    # 确保是 base64格式的字符串圖片字符串
    if isinstance(image_str, str) and image_str.startswith('data:image/png;base64,'):
        image_data = image_str.split(',')[1]  # 取出 Base64 数据
        image_data = base64.b64decode(image_data)  # 解码 Base64 数据
        # 將收到的圖片信息保存到本地
        img_path = os.path.join(BASE_DIR, "report", 'temporary_img', f"{image_name}.png")
        with open(img_path, 'wb') as f:
            f.write(image_data)