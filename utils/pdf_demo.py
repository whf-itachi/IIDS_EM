from reportlab.lib.colors import Color
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.rl_config import defaultPageSize
from reportlab.lib.units import inch
PAGE_HEIGHT=defaultPageSize[1]; PAGE_WIDTH=defaultPageSize[0]
styles = getSampleStyleSheet()
#页眉页脚
def myLaterPages(canvas, doc):
    canvas.saveState()
    im = Image("../statics/header.png", height=60, width=200)
    im.drawOn(canvas, 20, 780)
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
        [('ALIGN', (0, 0), (-1, -1), 'CENTER'),
         ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
         ('LEFTPADDING', (0, 0), (-1, -1), 0),
         ('RIGHTPADDING', (0, 0), (-1, -1), 0),
         ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
         ('TOPPADDING', (0, 0), (-1, -1), 5),
         ('LEADING', (0, 0), (-1, -1), 12),
         ('FONTNAME', (0, 0), (-1, -1), 'SimHei'),
         ('FONTSIZE', (0, 0), (-1, -1),8),
         ('BACKGROUND', (0, 0), (-1, 0), Color(0.8, 0.8, 0.8)),
         ('GRID', (0, 0), (-1, -1), 0.25, Color(0, 0, 0))
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
    doc = SimpleDocTemplate("haha.pdf",pagesize=A4,leftMargin=10,rightMargin=0,topMargin=50,bottomMargin=30)
    contents = fillContent(doc.width)
    doc.build(contents,onFirstPage=myLaterPages, onLaterPages=myLaterPages)


if __name__ == '__main__':
    pdfmetrics.registerFont(TTFont('SimHei', 'SimHei.TTF'))

    # pdfmetrics.registerFont(TTFont('msyh', 'msyh.ttf'))
    # pdfmetrics.registerFont(TTFont('bold', 'static/font/BOLD.TTF'))
    # pdfmetrics.registerFont(TTFont('regular', 'static/font/REGULAR.TTF'))
    # pdfmetrics.registerFont(TTFont('微软雅黑', 'msyh.ttf'))
    # pdfmetrics.registerFont(TTFont('bold', 'static/font/BOLD.TTF'))
    # pdfmetrics.registerFont(TTFont('regular', 'static/font/REGULAR.TTF'))

    go()