from django.urls import path

from . import views

urlpatterns = [
    path("realData/", views.real_data, name="real_data"),
    path("reportData/", views.reported_data, name="reported_data"),
    path("realLoginLog/", views.real_user_log_data, name="real_history_data"),
    path("realBladeLog/", views.real_blade_log_data, name="real_blade_log_data"),
    path("realSnapshotLog/", views.real_snapshot_log_data, name="real_snapshot_log_data"),
    path('bladeTypeCheckRule/', views.create_blade_type_check_rule, name='create_blade_type_check_rule'),
    path('bladeTypeCheckRuleById/<str:blade_id>/', views.get_blade_check_rule_by_id, name='get_blade_check_rule_by_id'),
    path('bladeTypeCheckRule/<str:blade_type>/', views.blade_type_check_rule_operate, name='blade_type_check_rule_operate'),
    path('allBladeTypeCheckRule/', views.get_all_blade_check_rules, name='get_all_blade_check_rules'),
    path('holeSignatureImage/<str:blade_id>/', views.get_blade_hole_signature_images, name='get_blade_hole_signature_images'),
    path('holeFlatnessData/<str:blade_id>/', views.get_blade_hole_flatness_by_id, name='get_blade_hole_flatness_by_id'),
    path("alarmLogData/", views.alarm_log_data, name="alarm_log_data"),
    path('snapshotData/<str:snap_id>/', views.real_snapshot_data, name='real_snapshot_data'),
]