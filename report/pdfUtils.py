from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer, Frame, \
    PageTemplate

import io


def download_blade_report(request):
    buffer = io.BytesIO()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="multi_page_document.pdf"'

    # 注册字体
    pdfmetrics.registerFont(TTFont('SimHei', 'SimHei.TTF'))

    # 创建文档
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    # 添加页面模板
    frame = Frame(0.5 * inch, 1.5 * inch, 7 * inch, 9 * inch, id='normal')
    doc.addPageTemplates([PageTemplate(id='template', frames=frame, onPage=add_header_footer)])

    elements = []
    styles = getSampleStyleSheet()

    # 设置样式
    normal_style = ParagraphStyle(name='Normal', fontName='SimHei', fontSize=12)

    # 添加首页说明
    elements.append(Paragraph("首页说明内容：这是一个关于多页 PDF 的示例。", normal_style))
    elements.append(PageBreak())

    # 添加表格
    data = [["姓名", "年龄", "城市"],
            ["张三", "25", "北京"],
            ["李四", "30", "上海"],
            ["王五", "22", "广州"],
            ["赵六", "28", "深圳"],
            ["钱七", "24", "杭州"],
            ["孙八", "26", "成都"],
            ["周九", "29", "武汉"]]

    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'SimHei'),
        ('FONTNAME', (0, 1), (-1, -1), 'SimHei'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    elements.append(PageBreak())

    # 添加说明段落
    for i in range(3):  # 添加多页内容
        elements.append(Paragraph(f"这是第 {i + 1} 页的说明段落。", normal_style))
        elements.append(PageBreak())

    # 添加尾页说明
    elements.append(Paragraph("尾页说明内容：感谢您阅读此文档。", normal_style))

    # 构建文档
    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)

    return response


def add_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("SimHei", 10)

    # 页眉
    canvas.drawString(1 * inch, 11 * inch, "文档页眉：多页 PDF 示例")
    canvas.drawString(5 * inch, 11 * inch, "右侧页眉内容")

    # 画横线
    canvas.setLineWidth(0.5)
    canvas.line(0.5 * inch, 10.8 * inch, 6.5 * inch, 10.8 * inch)

    # 页脚
    canvas.drawString(1 * inch, 0.5 * inch, f"页码 {doc.page}")
    canvas.drawString(5 * inch, 0.5 * inch, "右侧页脚内容")
    canvas.restoreState()