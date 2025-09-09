# -*- coding: utf-8 -*-

from django.db import models
from django.utils import timezone


# user log
class UserLog(models.Model):
    name = models.CharField(max_length=50, null=False, verbose_name='姓名')
    login_time = models.DateTimeField(null=True, blank=True, verbose_name='登录时间')
    logout_time = models.DateTimeField(null=True, blank=True, verbose_name='登出时间')

    def __str__(self):
        return f"{self.name} : 登录时间: {self.login_time.strftime('%Y-%m-%d %H:%M:%S') if self.login_time else '未登录'}, 登出时间: {self.logout_time.strftime('%Y-%m-%d %H:%M:%S') if self.logout_time else '未登出'}"


# Error message
class ErrMsg(models.Model):
    bladeName = models.CharField(max_length=50, default='default_blade_name', verbose_name="叶片名称")
    msgType = models.CharField(max_length=10, verbose_name='警告类型')
    msgText = models.CharField(max_length=40, verbose_name='警告内容')
    snapId = models.IntegerField(null=True, verbose_name="快照id")
    dt = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    def  __str__(self):
        return str(self.bladeName) + " : " + self.msgText


# Error message log
class MsgLog(models.Model):
    errMsg = models.ForeignKey(ErrMsg, on_delete=models.CASCADE, verbose_name='消息文本')
    comego = models.CharField(max_length=1, verbose_name='到来/离开')  # 'c' for come, 'g' for go
    dt = models.DateTimeField(default=timezone.now, verbose_name='时间')

    def  __str__(self):
        return self.errMsg.msgText + " : " + self.dt.strftime('%Y-%m-%d %H:%M:%S')


# class blade type and blade name
class BladeRecord(models.Model):
    bldtype = models.CharField(max_length=16, verbose_name='叶片类型')
    bldname = models.CharField(max_length=16, unique=True, verbose_name='叶片名字')
    dt = models.DateTimeField(default=timezone.now, verbose_name='上架时间')
    dtleave = models.DateTimeField(default=timezone.now, verbose_name='离架时间')

    def  __str__(self):
        return self.bldname


# blade hole position parameter
class BladeHoleParameter(models.Model):
    bldname = models.CharField(max_length=16, verbose_name='叶片名字')
    hole_num = models.CharField(max_length=16, verbose_name='孔号')
    valueType = models.CharField(max_length=16, verbose_name='值类型')
    checkVersion = models.IntegerField(default=1, verbose_name="验收版本号")
    input = models.FloatField(null=True, blank=True, verbose_name='输入值')
    res = models.CharField(max_length=16, null=True, verbose_name='校验结果')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')  # 自动记录创建时间
    updated_at = models.DateTimeField(auto_now=True, verbose_name='修改时间')  # 自动记录修改时间
    def  __str__(self):
        return f"{self.bldname}-{self.hole_num}"


class BladeSignImage(models.Model):
    bldname = models.CharField(max_length=16, verbose_name="叶片名字")
    signRole = models.CharField(max_length=24, verbose_name="签名角色")
    checkVersion = models.IntegerField(default=1, verbose_name='验收版本')
    signImg = models.TextField(verbose_name="图片文件")  # 使用 TextField 来存储 Base64 字符串
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')  # 自动记录创建时间
    updated_at = models.DateTimeField(auto_now=True, verbose_name='修改时间')  # 自动记录修改时间

    class Meta:
        unique_together = ('bldname', 'signRole', 'checkVersion')

    def __str__(self):
            return f"{self.bldname}-{self.signRole}--{self.checkVersion}"


# Power statistic for the cutting/milling/drilling and arm
class PowerStat(models.Model):
    dt = models.DateTimeField(default=timezone.now, verbose_name='时间')
    bldrecord = models.ForeignKey(BladeRecord, on_delete=models.CASCADE, verbose_name='叶片')
    unit = models.CharField(max_length=2, verbose_name='状态')  # 'C1', 'M1', 'A1', 'A2', 'A3', 'R1', 'R2', 'R3', 'Ar'
    duration = models.FloatField(verbose_name='时长', null=True, blank=True)
    spindlePowerMax = models.FloatField(verbose_name='刀具最大功率')
    spindlePowerAvg = models.FloatField(verbose_name='刀具平均功率')
    feedPowerMax = models.FloatField(verbose_name='进给最大功率', null=True, blank=True)
    feedPowerAvg = models.FloatField(verbose_name='进给平均功率', null=True, blank=True)

    def  __str__(self):
        return self.unit + " : " + self.dt.strftime('%Y-%m-%d %H:%M:%S')


# Blade status table
class BladeStatus(models.Model):
    bldrecord = models.ForeignKey(BladeRecord, on_delete=models.CASCADE, verbose_name='叶片')
    status = models.CharField(max_length=1,
                              verbose_name='状态')  # '1' for on saddle, '2' for auto cutting, '3' for auto milling, '4' for drilling, '5' for not on saddle
    dt = models.DateTimeField(default=timezone.now, verbose_name='进入时间')
    dtleave = models.DateTimeField(default=timezone.now, verbose_name='离开时间')
    duration = models.FloatField(verbose_name='时长', null=True, blank=True)

    def __str__(self):
        return self.bldrecord.bldname + " : " + \
            {'1': "On Saddle", '2': "Cutting", '3': "Milling", '4': "Drilling", '5': "Off Saddle",
             '7': "Leave Cutting", '8': "Leave Milling", '9': "Leave Drilling", }[self.status]


class DMMSnap(models.Model):
    dt = models.DateTimeField(default=timezone.now, verbose_name='时间')
    username = models.CharField(max_length=10, null=True, verbose_name='姓名')
    # user = models.ForeignKey(UserLog, on_delete = models.CASCADE, verbose_name='操作员')
    # bldStatus = models.ForeignKey(BladeStatus, on_delete = models.CASCADE, verbose_name='叶片状态')

    bldrecord = models.ForeignKey(BladeRecord, on_delete=models.CASCADE, verbose_name='叶片名字')
    bldMode = models.IntegerField(verbose_name='模式码')  # see the detailed description in the plc code
    program = models.IntegerField(verbose_name='程序号')
    prgStep = models.IntegerField(verbose_name='执行步')
    # axialUsing = models.IntegerField(verbose_name='轴单元号')

    bldonSaddle = models.BooleanField(verbose_name='叶片上架')
    doorClosed = models.BooleanField(verbose_name='门关闭')
    powerOn = models.BooleanField(verbose_name='驱动上电')

    saddleMoveDir = models.IntegerField(
        verbose_name='支架运动方向')  # 0 for staying， 1 for  moving forwarding, 2 for moving backwarding
    posSaddleExist = models.BooleanField(verbose_name='有支架定位', default=False)
    posSaddlePos = models.FloatField(verbose_name='支架位置', null=True, blank=True)

    armPos = models.FloatField(verbose_name='大臂位置')
    armSpeed = models.FloatField(verbose_name='大臂速度')
    armTarget = models.FloatField(verbose_name='大臂目标')
    armPower = models.FloatField(verbose_name='大臂功率', null=True, blank=True)

    cutUnitExist = models.BooleanField(verbose_name='有切割单元', default=True)
    cutFeedPos = models.FloatField(verbose_name='切割单元位置', null=True, blank=True)
    cutFeedSpeed = models.FloatField(verbose_name='切割单元速度', null=True, blank=True)
    cutFeedTarget = models.FloatField(verbose_name='切割单元目标', null=True, blank=True)
    cutFeedPower = models.FloatField(verbose_name='切割单元进给功率', null=True, blank=True)
    cutSpindleSpeed = models.FloatField(verbose_name='切割刀具速度', null=True, blank=True)
    cutSpindlePower = models.FloatField(verbose_name='切割刀具功率', null=True, blank=True)

    millUnitExist = models.BooleanField(verbose_name='有铣磨单元', default=True)
    millFeedPos = models.FloatField(verbose_name='铣磨单元位置')
    millFeedSpeed = models.FloatField(verbose_name='铣磨单元速度')
    millFeedTarget = models.FloatField(verbose_name='铣磨单元目标')
    millFeedPower = models.FloatField(verbose_name='铣磨单元进给功率', null=True, blank=True)
    millSpindleSpeed = models.FloatField(verbose_name='铣磨刀具速度')
    millSpindlePower = models.FloatField(verbose_name='铣磨刀具功率')

    axial1UnitExist = models.BooleanField(verbose_name='有轴1单元', default=True)
    axial1FeedPos = models.FloatField(verbose_name='轴1单元位置')
    axial1FeedSpeed = models.FloatField(verbose_name='轴1单元速度')
    axial1FeedTarget = models.FloatField(verbose_name='轴1单元目标')
    axial1FeedPower = models.FloatField(verbose_name='轴1单元进给功率', null=True, blank=True)
    axial1SpindleSpeed = models.FloatField(verbose_name='轴1刀具速度')
    axial1SpindlePower = models.FloatField(verbose_name='轴1刀具功率')

    radial1UnitExist = models.BooleanField(verbose_name='有径1单元', default=True)
    radial1FeedPos = models.FloatField(verbose_name='径1单元位置')
    radial1FeedSpeed = models.FloatField(verbose_name='径1单元速度')
    radial1FeedTarget = models.FloatField(verbose_name='径1单元目标')
    radial1FeedPower = models.FloatField(verbose_name='径1单元进给功率', null=True, blank=True)
    radial1SpindleSpeed = models.FloatField(verbose_name='径1刀具速度')
    radial1SpindlePower = models.FloatField(verbose_name='径1刀具功率')

    axial2UnitExist = models.BooleanField(verbose_name='有轴2单元', default=False)
    axial2FeedPos = models.FloatField(verbose_name='轴2单元位置', null=True, blank=True)
    axial2FeedSpeed = models.FloatField(verbose_name='轴2单元速度', null=True, blank=True)
    axial2FeedTarget = models.FloatField(verbose_name='轴2单元目标', null=True, blank=True)
    axial2FeedPower = models.FloatField(verbose_name='轴2单元进给功率', null=True, blank=True)
    axial2SpindleSpeed = models.FloatField(verbose_name='轴2刀具速度', null=True, blank=True)
    axial2SpindlePower = models.FloatField(verbose_name='轴2刀具功率', null=True, blank=True)

    axial3UnitExist = models.BooleanField(verbose_name='有轴3单元', default=False)
    axial3FeedPos = models.FloatField(verbose_name='轴3单元位置', null=True, blank=True)
    axial3FeedSpeed = models.FloatField(verbose_name='轴3单元速度', null=True, blank=True)
    axial3FeedTarget = models.FloatField(verbose_name='轴3单元目标', null=True, blank=True)
    axial3FeedPower = models.FloatField(verbose_name='轴3单元进给功率', null=True, blank=True)
    axial3SpindleSpeed = models.FloatField(verbose_name='轴3刀具速度', null=True, blank=True)
    axial3SpindlePower = models.FloatField(verbose_name='轴3刀具功率', null=True, blank=True)

    radial2UnitExist = models.BooleanField(verbose_name='有径2单元', default=False)
    radial2FeedPos = models.FloatField(verbose_name='径2单元位置', null=True, blank=True)
    radial2FeedSpeed = models.FloatField(verbose_name='径2单元速度', null=True, blank=True)
    radial2FeedTarget = models.FloatField(verbose_name='径2单元目标', null=True, blank=True)
    radial2FeedPower = models.FloatField(verbose_name='径2单元进给功率', null=True, blank=True)
    radial2SpindleSpeed = models.FloatField(verbose_name='径2刀具速度', null=True, blank=True)
    radial2SpindlePower = models.FloatField(verbose_name='径2刀具功率', null=True, blank=True)

    mill2UnitExist = models.BooleanField(verbose_name='有铣磨2#单元', default=False)
    mill2FeedPos = models.FloatField(verbose_name='铣磨2#单元位置', null=True, blank=True)
    mill2FeedSpeed = models.FloatField(verbose_name='铣磨2#单元速度', null=True, blank=True)
    mill2FeedTarget = models.FloatField(verbose_name='铣磨2#单元目标', null=True, blank=True)
    mill2FeedPower = models.FloatField(verbose_name='铣磨2#单元进给功率', null=True, blank=True)

    scannerExist = models.BooleanField(verbose_name='有扫描仪', default=False)
    scannerOn = models.BooleanField(verbose_name='扫描仪工作', default=False)
    scannerData = models.FloatField(verbose_name='扫描数据', null=True, blank=True)

    mWheelExist = models.BooleanField(verbose_name='有测量轮', default=False)
    mWheelOn = models.BooleanField(verbose_name='测量轮接触叶片', default=False)
    mWShakeValue = models.FloatField(verbose_name='晃动值', null=True, blank=True)

    clampExist = models.BooleanField(verbose_name='有叶片夹具', default=False)
    clampClosed = models.BooleanField(verbose_name='夹具闭合', default=False)  # 0 for open, 1 for closed
    clampMoveDir = models.IntegerField(verbose_name='夹具运动方向', null=True,
                                       blank=True)  # 0 for staying， 1 for closing, 2 for moving opening

    roofExist = models.BooleanField(verbose_name='有顶棚开关', default=False)
    roofClosed = models.FloatField(verbose_name='顶棚关闭', null=True, blank=True)  # 0 for open, 1 for closed
    roofMoveDir = models.IntegerField(verbose_name='顶棚运动方向', null=True,
                                      blank=True)  # 0 for staying， 1 for closing, 2 for moving opening

    autoAjustExist = models.BooleanField(verbose_name='有自动对中', default=False)
    xAjustPos = models.FloatField(verbose_name='支架x轴位置', null=True, blank=True)
    zAjustPos = models.FloatField(verbose_name='支架z轴位置', null=True, blank=True)
    xAjustMoveDir = models.IntegerField(verbose_name='支架x轴运动方向', null=True,
                                        blank=True)  # 0 for staying， 1 for lefting, 2 for moving righting
    zAjustMoveDir = models.IntegerField(verbose_name='支架z轴运动方向', null=True,
                                        blank=True)  # 0 for staying， 1 for uping, 2 for moving downing

    def __str__(self):
        return self.bldrecord.bldname


class DMMSnapLog(models.Model):
    snapStr =  models.CharField(max_length=3000, verbose_name='快照字符串')
    dt = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')


# 叶片加工各工序时间表
class BladePhaseLog(models.Model):
    bladeId = models.CharField(max_length=40, verbose_name='叶片ID')
    bladeType = models.CharField(max_length=40, verbose_name='叶片类型')
    phase = models.CharField(max_length=40, verbose_name='加工工序')
    startTime = models.DateTimeField(default=timezone.now, verbose_name='开始时间')
    endTime = models.DateTimeField(null=True, verbose_name='结束时间')

    def  __str__(self):
        return str(self.bladeId) + " : " + self.phase


# 各类叶片加工各工序统计表
class AllBladePhaseStatistic(models.Model):
    bladeId = models.CharField(unique=True, max_length=40, verbose_name='叶片ID') # 按叶片名称进行统计
    bladeType = models.CharField(max_length=40, verbose_name='叶片类型')
    AutoCut = models.FloatField(default=0, verbose_name='切割时间')
    AutoMill = models.FloatField(default=0, verbose_name='研磨时间')
    TestDrill = models.FloatField(default=0, verbose_name='测试孔时间')
    AutoDrill = models.FloatField(default=0, verbose_name='钻孔时间')
    AllTime = models.FloatField(default=0, verbose_name='加工时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')  # 自动记录创建时间

    def  __str__(self):
        return str(self.bladeId) + " : " + self.bladeType


# 各类叶片的校验规则
class BladeTypeCheckRule(models.Model):
    bladeType = models.CharField(unique=True, max_length=40, verbose_name='叶片类型')  # 唯一字段
    IDValue = models.FloatField(default=0, verbose_name='id值')
    IDUpper = models.FloatField(default=0, verbose_name='id大值')
    IDLower = models.FloatField(default=0, verbose_name='id小值')
    SFValue = models.FloatField(default=0, verbose_name='sf值')
    SFUpper = models.FloatField(default=0, verbose_name='sf大值')
    SFLower = models.FloatField(default=0, verbose_name='sf小值')
    ODValue = models.FloatField(default=0, verbose_name='od值')
    ODUpper = models.FloatField(default=0, verbose_name='od大值')
    ODLower = models.FloatField(default=0, verbose_name='od小值')
    BCDValue = models.FloatField(default=0, verbose_name='bcd值')
    BCDUpper = models.FloatField(default=0, verbose_name='bcd大值')
    BCDLower = models.FloatField(default=0, verbose_name='bcd小值')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')  # 自动记录创建时间
    updated_at = models.DateTimeField(auto_now=True, verbose_name='修改时间')  # 自动记录修改时间

    def  __str__(self):
        return str(self.bladeType)


# 叶片验收版本记录表
class BladeCheckVersion(models.Model):
    bladeId = models.CharField(max_length=40, verbose_name='叶片ID')
    checkVersion = models.IntegerField(default=1, verbose_name='验收版本')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')  # 自动记录创建时间

    def  __str__(self):
        return str(self.bladeId) + " : " + str(self.checkVersion)


# 平整度报告记录表
class FlatnessReport(models.Model):
    bladeId = models.CharField(max_length=40, verbose_name='叶片ID')  # 叶片名称
    holeAngle = models.FloatField(default=0, verbose_name='角度')  # 孔角度
    flatness = models.FloatField(default=0, verbose_name='区域平整度')  # 该角度孔的区域平整度
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    def  __str__(self):
        return str(self.bladeId) + " : " + str(self.holeAngle)
