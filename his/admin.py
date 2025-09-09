# -*- coding: utf-8 -*-

from django.contrib import admin
from his import models


class UserLogAdmin(admin.ModelAdmin):
    list_display = ('name', 'login_time', 'logout_time')  # 直接显示字段
    ordering = ['login_time']  # 按登录时间排序


class ErrMsgAdmin(admin.ModelAdmin):
    list_display = ('id', 'bladeName', 'msgType', 'msgText', 'snapId', 'dt')
    search_fields = ('msgText',)
    ordering = ('id',)


class MsgLogAdmin(admin.ModelAdmin):
    list_display = ('dt', 'comego', 'errMsg',)
    search_fields = ('errMsg',)
    ordering = ('-dt',)


class BldRecordAdmin(admin.ModelAdmin):
    list_display = ('bldname', 'bldtype', 'dt', 'dtleave',)
    search_fields = ('bldname',)
    ordering = ('-dt',)


class BldStatusAdmin(admin.ModelAdmin):
    list_display = ('bldrecord', 'status', 'dt',)
    search_fields = ('bldrecord',)
    ordering = ('-bldrecord',)


class DMMSnapAdmin(admin.ModelAdmin):
    list_display = ('dt', 'username', 'bldMode', 'program', 'prgStep', 'bldonSaddle', 'armPos', 'armSpeed', \
                    'cutFeedPos', 'cutSpindlePower', 'millFeedPos', 'millSpindlePower', 'radial1FeedPos',
                    'radial1SpindlePower', 'axial1FeedPos', 'axial1SpindlePower',)
    search_fields = ('bldStatus',)
    ordering = ('-dt',)


class PowerStatAdmin(admin.ModelAdmin):
    list_display = (
    'bldrecord', 'unit', 'dt', 'duration', 'spindlePowerMax', 'spindlePowerAvg', 'feedPowerMax', 'feedPowerAvg',)
    search_fields = ('unit',)
    ordering = ('-dt',)


class BladePhaseLogAdmin(admin.ModelAdmin):
    list_display = ('bladeId', 'bladeType', 'phase', 'startTime', 'endTime',)
    search_fields = ('bladeId', 'phase')
    ordering = ('-id',)


class AllBladePhaseStatisticAdmin(admin.ModelAdmin):
    list_display = ('bladeId', "bladeType","AutoCut","AutoMill","TestDrill","AutoDrill","AllTime","created_at")
    search_fields = ('bladeId', 'bladeType')
    ordering = ('-id',)

class BladeTypeCheckRuleAdmin(admin.ModelAdmin):
    list_display = ("bladeType","IDValue","IDUpper","IDLower","SFValue","SFUpper","SFLower","ODValue","ODUpper",
                    "ODLower","BCDValue","BCDUpper","BCDLower")
    search_fields = ('bladeType',)
    ordering = ('-id',)


class BladeCheckVersionAdmin(admin.ModelAdmin):
    list_display = ("bladeId","checkVersion","created_at")
    search_fields = ('bladeId',)
    ordering = ('-id',)


class BladeSignImageAdmin(admin.ModelAdmin):
    list_display = ("bldname","signRole", "checkVersion", "created_at", "updated_at")
    search_fields = ('bldname',)
    ordering = ('-id',)


class FlatnessReportAdmin(admin.ModelAdmin):
    list_display = ("bladeId","holeAngle", "flatness", "created_at")
    search_fields = ('bladeId',)
    ordering = ('-id',)


admin.site.register(models.UserLog, UserLogAdmin)
admin.site.register(models.ErrMsg, ErrMsgAdmin)
admin.site.register(models.MsgLog, MsgLogAdmin)
admin.site.register(models.BladeRecord, BldRecordAdmin)
admin.site.register(models.BladeStatus, BldStatusAdmin)
admin.site.register(models.DMMSnap, DMMSnapAdmin)
admin.site.register(models.PowerStat, PowerStatAdmin)

admin.site.register(models.BladePhaseLog, BladePhaseLogAdmin)
admin.site.register(models.AllBladePhaseStatistic, AllBladePhaseStatisticAdmin)
admin.site.register(models.BladeTypeCheckRule, BladeTypeCheckRuleAdmin)
admin.site.register(models.BladeCheckVersion, BladeCheckVersionAdmin)
admin.site.register(models.BladeSignImage, BladeSignImageAdmin)
admin.site.register(models.FlatnessReport, FlatnessReportAdmin)