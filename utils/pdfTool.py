from reportlab.lib import colors
from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, Frame, PageTemplate
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.rl_config import defaultPageSize
from reportlab.lib.units import inch


PAGE_HEIGHT=defaultPageSize[1]; PAGE_WIDTH=defaultPageSize[0]
styles = getSampleStyleSheet()


# 创建一个自定义函数，用于在每页添加页头
def add_header(canvas, doc):
    # 设置页头的字体和大小
    header_font = 'SimHei'
    header_size = 12

    # 设置页头的文本和位置
    header_text = "这是页头"
    header_x = 72  # 距离页面左边距72点（1英寸）
    header_y = 750  # 距离页面顶部750点（接近页面顶部，根据页面大小和边距调整）
    header_height = 15  # 页头的高度

    # 在canvas上绘制页头文本
    canvas.setFont(header_font, header_size)
    canvas.drawString(header_x, header_y, header_text)

    # 可选：绘制一个矩形作为页头的背景（这里不绘制，但你可以根据需要添加）
    canvas.rect(header_x-10, header_y-header_height, len(header_text)*10+20, header_height)

    # Draw the frame border
    frame_x = 10  # Adjust based on your frame position
    frame_y = 10  # Bottom left corner of the frame
    frame_width = 500
    frame_height = PAGE_HEIGHT - 70

    # Draw the border
    canvas.setStrokeColorRGB(0, 0, 0)  # Black color for the border
    canvas.setLineWidth(1)  # Line width for the border
    canvas.rect(frame_x, frame_y, frame_width, frame_height)  # Draw the rectangle


#页眉页脚
def myLaterPages(canvas, doc):
    # 绘制页头
    add_header(canvas, doc)  # 添加这行

    # 绘制页脚
    canvas.saveState()

    canvas.setStrokeColorRGB(0.8, 0.8, 0.8)
    canvas.setFillColorRGB(0, 0, 0)
    canvas.line(15, 28,doc.width-15, 28)
    canvas.setFont('SimHei',8)
    str=f"XXX银行 | Page {doc.page}"
    textLen = stringWidth(str, 'SimHei', 8)

    canvas.drawCentredString(int((doc.width-textLen)/2),0.15 *inch, str)
    canvas.restoreState()

def solidHeaders(width):
    headers=[]
    h1_style = ParagraphStyle("header_style", fontName='SimHei', leading=20, fontSize=16, alignment=TA_CENTER)
    headers.append(Paragraph("交易明细",style=h1_style))

    h2_style = ParagraphStyle("header_style", fontName='SimHei', leading=13, fontSize=10, alignment=TA_LEFT)
    headers.append(Paragraph("尊敬的客户", style=h2_style))
    headers.append(Paragraph("十分感谢阁下对本公司的支持，请查阅如下表格核对您的本月账单。如有疑问请及时与我们联系，我们将竭诚为您服务，谢谢！", style=h2_style))
    headers.append(Spacer(width,6))
    h3_style = ParagraphStyle("header_style", fontName='SimHei', leading=13, fontSize=10, alignment=TA_LEFT)
    headers.append(Paragraph("账户: JU1234567 张三", style=h3_style))
    headers.append(Paragraph("交易日期：2022-05", style=h3_style))
    headers.append(Paragraph("本月交易明细：", style=h3_style))
    headers.append(Spacer(width,10))
    return headers

def solidFooters(width):
    footers=[]
    footers.append(Spacer(width, 4))
    h_style = ParagraphStyle("header_style", fontName='SimHei', leading=13, fontSize=10, alignment=TA_LEFT)
    footers.append(Paragraph("免责申明： 免责声明的详细内容免责声明的详细内容免责声明的详细内容免责声明的详细内容免责声明的详细内容免责声明的详细内容。", style=h_style))
    footers.append(Paragraph("您本月的入账流水总额:30297.00元", style=h_style))
    footers.append(Paragraph("您本月消费流水总额：30000.00元", style=h_style))
    footers.append(Spacer(width, 4))
    footers.append(Paragraph("本月结余：297.00元", style=h_style))
    footers.append(Spacer(width, 4))
    footers.append(Paragraph("结转上月余额：20000.00元", style=h_style))

    footers.append(Spacer(width, 4))
    h_summary_style = ParagraphStyle("header_style", fontName='SimHei', leading=13, fontSize=10 , alignment=TA_LEFT)
    footers.append(Paragraph("您当前账户余额：20297.00元", style=h_summary_style))
    return footers


# 生成消费测试数据
def tablesData_consume():
    datas=[
        ['交易时间','交易商户','交易金额','备注']
    ]


    datas+=[['2022-05-01 12:45:56','深圳坂田沃尔码','132.00','消费'] for i in range(100)]
    return datas



def datagrid(datadatas):
    cols_width = [100, 100, 100, 100]

    table = Table(datadatas, colWidths=cols_width, hAlign='LEFT')
    tablestyle = TableStyle(
        [('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # 单元格内容居中
         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # 单元格内容垂直居中
         ('LEFTPADDING', (0, 0), (-1, -1), 0),  # 左内边距
         ('RIGHTPADDING', (0, 0), (-1, -1), 0),  # 右内边距
         ('BOTTOMPADDING', (0, 0), (-1, -1), 0),  # 底内边距
         ('TOPPADDING', (0, 0), (-1, -1), 5),  # 顶内边距
         ('LEADING', (0, 0), (-1, -1), 12),  # 行间距
         ('FONTNAME', (0, 0), (-1, -1), 'SimHei'),  # 字体名称
         ('FONTSIZE', (0, 0), (-1, -1),8),  # 字体大小
         ('BACKGROUND', (0, 0), (-1, 0), Color(0.8, 0.8, 0.8)),  # 表头背景色
         ('GRID', (0, 0), (-1, -1), 0.25, Color(0, 0, 0))  # 网格线
         ]

    )
    table.setStyle(tablestyle)
    return table


#生成存款测试数据
def tablesData_deposit():
    datas = [
        ['交易时间', '交易商户', '交易金额', '备注']

    ]
    datas+=[['2022-05-01 12:45:56', '宜昌商业银行', '132.00', '存款'] for i in range(100)]

    return datas



def fillContent(width):
    h3_style = ParagraphStyle("header_style", fontName='SimHei', leading=12, fontSize=9, alignment=TA_LEFT)
    contents=solidHeaders(width)
    contents.append(Paragraph("消费:", style=h3_style))
    contents.append(Spacer(width, 4))
    contents.append(datagrid(tablesData_consume()))
    contents.append(Spacer(width, 4))

    contents.append(Paragraph("收入:", style=h3_style))
    contents.append(Spacer(width, 4))
    contents.append(datagrid(tablesData_deposit()))
    contents.append(Spacer(width, 4))
    contents.extend(solidFooters(width))
    return contents



def go():
    top_margin = 150  # Adjust this value as needed for header height
    bottom_margin = 30

    doc = SimpleDocTemplate("haha.pdf", pagesize=A4, leftMargin=10, rightMargin=0, topMargin=top_margin,
                            bottomMargin=bottom_margin)

    # Create a Frame object for page content
    # Adjust the frame height to account for the header
    frame = Frame(10, 10, 500, PAGE_HEIGHT - top_margin, id='normal_frame')

    page_template = PageTemplate(id='main', frames=[frame], onPage=add_header)
    doc.addPageTemplates([page_template])

    contents = fillContent(doc.width)
    doc.build(contents,onFirstPage=myLaterPages, onLaterPages=myLaterPages)


if __name__ == '__main__':
    pdfmetrics.registerFont(TTFont('SimHei', 'SimHei.TTF'))

    go()

