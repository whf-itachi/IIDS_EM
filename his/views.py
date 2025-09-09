# -*- coding: utf-8 -*-

from django.http import HttpResponse, Http404, JsonResponse
from django.template.loader import get_template
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from his.hisModelsSerializer import UserLogSerializer
from his.models import UserLog, ErrMsg, MsgLog, BladeRecord, PowerStat, BladeStatus, DMMSnap
from datetime import datetime, timedelta

PAGE_AMOUNT = 5  # 每页显示最多条数
PAGE_LIMIT = 5


class FormData():
    def __init__(self, href="?"):
        self.operator = ""
        self.startdate = ""
        self.starttime = ""
        self.enddate = ""
        self.endtime = ""
        self.msgid = "0"
        self.msgstatus = "0"
        self.msgtxt = ""
        self.bldtype = ""
        self.bldname = ""
        self.href = href

    def build_userhis_ref(self):
        href = ("?startdate=%s&starttime=%s&enddate=%s&endtime=%s&operator=%s" %
                (self.startdate, self.starttime, self.enddate, self.endtime, self.operator))
        return href

    def build_msghis_ref(self):
        href = "?startdate=%s&starttime=%s&enddate=%s&endtime=%s&msgid=%s&msgstatus=%s&msgtxt=%s" % (
            self.startdate,
            self.starttime, self.enddate, self.endtime, self.msgid, self.msgstatus, self.msgtxt)
        return href

    def build_bldhis_ref(self):
        href = "?startdate=%s&starttime=%s&enddate=%s&endtime=%s&bldtype=%s&bldname=%s" % (self.startdate,
                                                                                           self.starttime,
                                                                                           self.enddate,
                                                                                           self.endtime,
                                                                                           self.bldtype,
                                                                                           self.bldname)
        return href

    def build_snaphis_ref(self):
        href = "?startdate=%s&starttime=%s&enddate=%s&endtime=%s" % (self.startdate,
                                                                     self.starttime, self.enddate, self.endtime)
        return href


def userhis(request):
    '''
        user logon archive search 
    '''
    print("get here!")
    ulogsAll = UserLog.objects.all()
    # count = ulogsAll
    hisform = FormData()
    try:
        operator = request.GET.get('operator', "").strip()
        if operator != "":
            ulogsAll = ulogsAll.filter(name__icontains=operator)
            hisform.operator = operator

        startdt = request.GET.get('startdate', "").strip()
        if startdt != "":
            startdt = startdt + " " + request.GET.get('starttime', "")
            ulogsAll = ulogsAll.filter(dt__gte=startdt.strip())
            hisform.startdate = request.GET.get('startdate', "").strip()
            hisform.starttime = request.GET.get('starttime', "").strip()

        enddt = request.GET.get('enddate', "").strip()
        if enddt != "":
            enddt = enddt + " " + request.GET.get('endtime', "")
            ulogsAll = ulogsAll.filter(dt__lte=enddt.strip())
            hisform.enddate = request.GET.get('enddate', "").strip()
            hisform.endtime = request.GET.get('endtime', "").strip()
    except:
        print("error in userhis")
        pass
    hisform.build_userhis_ref()

    ulogsAll = ulogsAll.order_by('-dt')[:PAGE_AMOUNT * PAGE_LIMIT]
    paginator = Paginator(ulogsAll, PAGE_AMOUNT)

    page = request.GET.get('page')
    START_INDEX = 0
    try:
        ulogs = paginator.page(page)
        START_INDEX = PAGE_AMOUNT * (ulogs.number - 1)
    except PageNotAnInteger:
        ulogs = paginator.page(1)
    except EmptyPage:
        ulogs = paginator.page(paginator.num_pages)

    print("...................")

    ulogs = UserLogSerializer(instance=ulogs, many=True)
    print(ulogs.data)
    # 准备响应数据
    response_data = {
        'ulogs': ulogs.data,
        'start_index': START_INDEX,

    }
    return JsonResponse(response_data)


def msghis(request):
    '''
        message message archive search 
    '''
    msgAll = ErrMsg.objects.all()
    mlogsAll = MsgLog.objects.all()
    hisform = FormData()
    try:
        msgstatus = request.GET.get('msgstatus', "").strip()
        if msgstatus != "" and msgstatus != "0":
            mlogsAll = mlogsAll.filter(comego__icontains=msgstatus)
            hisform.msgstatus = request.GET['msgstatus'].strip()

        msgid = request.GET.get('msgid', "").strip()
        if msgid != "" and msgid != "0":
            msglist = msgAll.get(errorid=int(msgid))
            mlogsAll = mlogsAll.filter(errMsg=msglist)
            hisform.msgid = request.GET['msgid'].strip()

        msgtxt = request.GET.get('msgtxt', "").strip()
        if msgtxt != "":
            msglist = msgAll.filter(msgtext__icontains=msgtxt)
            mlogsAll = mlogsAll.filter(errMsg__in=msglist)
            hisform.msgtxt = request.GET['msgtxt'].strip()

        startdt = request.GET.get('startdate', "").strip()
        if startdt != "":
            startdt = startdt + " " + request.GET.get('starttime', "")
            mlogsAll = mlogsAll.filter(dt__gte=startdt.strip())
            hisform.startdate = request.GET.get('startdate', "").strip()
            hisform.starttime = request.GET.get('starttime', "").strip()

        enddt = request.GET.get('enddate', "").strip()
        if enddt != "":
            enddt = enddt + " " + request.GET.get('endtime', "")
            mlogsAll = mlogsAll.filter(dt__lte=enddt.strip())
            hisform.enddate = request.GET.get('enddate', "").strip()
            hisform.endtime = request.GET.get('endtime', "").strip()
    except:
        print("error in msghis")
        pass
    hisform.build_msghis_ref()

    mlogsAll = mlogsAll.order_by('-dt')[:PAGE_AMOUNT * PAGE_LIMIT]
    paginator = Paginator(mlogsAll, PAGE_AMOUNT)

    page = request.GET.get('page')
    try:
        mlogs = paginator.page(page)
    except PageNotAnInteger:
        mlogs = paginator.page(1)
        START_INDEX = 0
    except EmptyPage:
        mlogs = paginator.page(paginator.num_pages)
    START_INDEX = PAGE_AMOUNT * (mlogs.number - 1)

    template = get_template('msghis.html')
    html = template.render(locals())
    return HttpResponse(html)


def bldhis(request):
    '''
        blade status and power statistic
    '''
    bldtypeAll = BladeRecord.objects.values("bldtype").distinct()
    bldAll = BladeRecord.objects.all()
    hisform = FormData()
    try:
        bldtype = request.GET.get('bldtype', "").strip()
        if bldtype != "" and bldtype != "0":
            bldAll = bldAll.filter(bldtype__icontains=bldtype)
            hisform.bldtype = request.GET['bldtype'].strip()

        bldname = request.GET.get('bldname', "").strip()
        if bldname != "":
            bldAll = bldAll.filter(bldname__icontains=bldname)
            hisform.bldname = request.GET['bldname'].strip()

        startdt = request.GET.get('startdate', "").strip()
        if startdt != "":
            startdt = startdt + " " + request.GET.get('starttime', "")
            bldAll = bldAll.filter(dt__gte=startdt.strip())
            hisform.startdate = request.GET.get('startdate', "").strip()
            hisform.starttime = request.GET.get('starttime', "").strip()

        enddt = request.GET.get('enddate', "").strip()
        if enddt != "":
            enddt = enddt + " " + request.GET.get('endtime', "")
            bldAll = bldAll.filter(dt__lte=enddt.strip())
            hisform.enddate = request.GET.get('enddate', "").strip()
            hisform.endtime = request.GET.get('endtime', "").strip()
    except:
        print("error in bldhis")
        pass
    hisform.build_bldhis_ref()

    showdetail = request.GET.get('detail', "0").strip()
    if bldAll.count() == 1:
        hisform.bldname = bldAll[0].bldname
        showdetail = '1'

    if showdetail != '1':
        bldAll = bldAll.order_by('-dt')[:PAGE_AMOUNT * PAGE_LIMIT]
        paginator = Paginator(bldAll, PAGE_AMOUNT)

        page = request.GET.get('page')
        try:
            blogs = paginator.page(page)
        except PageNotAnInteger:
            blogs = paginator.page(1)
            START_INDEX = 0
        except EmptyPage:
            blogs = paginator.page(paginator.num_pages)
        START_INDEX = PAGE_AMOUNT * (blogs.number - 1)
    else:
        bldshowdetail = BladeRecord.objects.get(bldname=hisform.bldname)
        powerdetails = PowerStat.objects.filter(bldrecord=bldshowdetail).order_by('-dt')
        statusdetails = BladeStatus.objects.filter(bldrecord=bldshowdetail).order_by('-dt')

        fd = FormData()
        fd.startdate = (bldshowdetail.dt + timedelta(hours=8)).strftime("%Y-%m-%d")
        fd.starttime = (bldshowdetail.dt + timedelta(hours=8)).strftime("%H:%M")
        fd.enddate = (bldshowdetail.dtleave + timedelta(hours=8)).strftime("%Y-%m-%d")
        fd.endtime = (bldshowdetail.dtleave + timedelta(hours=8)).strftime("%H:%M")
        userref = fd.build_userhis_ref()
        msgref = fd.build_msghis_ref()

    template = get_template('bldhis.html')
    html = template.render(locals())
    return HttpResponse(html)


def snaphis(request):
    '''
        machine status snap archive search 
    '''
    slogsAll = DMMSnap.objects.all()
    hisform = FormData()
    try:
        startdt = request.GET.get('startdate', "").strip()
        if startdt != "":
            startdt = startdt + " " + request.GET.get('starttime', "")
            slogsAll = slogsAll.filter(dt__gte=startdt.strip())
            hisform.startdate = request.GET.get('startdate', "").strip()
            hisform.starttime = request.GET.get('starttime', "").strip()

        enddt = request.GET.get('enddate', "").strip()
        if enddt != "":
            enddt = enddt + " " + request.GET.get('endtime', "")
            slogsAll = slogsAll.filter(dt__lte=enddt.strip())
            hisform.enddate = request.GET.get('enddate', "").strip()
            hisform.endtime = request.GET.get('endtime', "").strip()
    except:
        print("error in userhis")
        pass
    hisform.build_snaphis_ref()

    slogsAll = slogsAll.order_by('-dt')[:PAGE_AMOUNT * PAGE_LIMIT]
    paginator = Paginator(slogsAll, PAGE_AMOUNT)

    page = request.GET.get('page')
    try:
        slogs = paginator.page(page)
    except PageNotAnInteger:
        slogs = paginator.page(1)
        START_INDEX = 0
    except EmptyPage:
        slogs = paginator.page(paginator.num_pages)
    START_INDEX = PAGE_AMOUNT * (slogs.number - 1)

    template = get_template('snaphis.html')
    html = template.render(locals())
    return HttpResponse(html)