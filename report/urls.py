from django.urls import path

from . import views,blade_phase

urlpatterns = [
    path("BladeInfo/", views.get_blade_report_info, name="bladeInfo"),
    path("bladeReportQuery/", views.blade_report_query, name="bladeReportQuery"),
    path("downloadBladeReport/", views.download_blade_report, name="downloadBladeInfo"),
    path("BladeSignatureUpload/", views.blade_signature_upload, name="blade_signature_upload"),
    path("chartDataQuery/", views.blade_report_chart_query, name="blade_report_chart_query"),
    path("chartUserLogoutData/", views.report_user_logout_chart_query, name="report_user_logout_chart_query"),
    path("userLoginChartUpload/", views.user_login_chart_upload, name="user_login_chart_upload"),
    path('bladePhaseLog/<str:blade_id>/', blade_phase.get_blade_phase_log, name='get_blade_phase_log'),
    path('bladeTypePhaseStatistic/', blade_phase.get_blade_type_phase_statistic, name='get_blade_type_phase_statistic'),
    path('bladeType/<str:blade_id>/', blade_phase.get_blade_type_by_name, name='get_blade_type_by_name'),
    path('bladeHoleSignQuery/<str:blade_id>/', blade_phase.blade_signature_query, name='blade_signature_query'),
    path('chartImageUpload/', views.blade_chart_image_upload, name='chart_image_upload'),
    path('bladeStatisticData/<str:blade_id>/', blade_phase.get_blade_statistic_data, name='get_blade_statistic_data'),
    path("downloadSingleBladeReport/", views.download_single_blade_report, name="download_single_blade_report"),
    path("downloadBladeTypeReport/", views.download_blade_type_report, name="download_blade_type_report"),
    path("downloadFlatnessReport/", views.download_flatness_report, name="download_flatness_report"),
]