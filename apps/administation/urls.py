from django.urls import path
from . import views

app_name = 'administation'

urlpatterns = [
    path('', views.admin_dashboard_view, name='dashboard'),

    # Teacher approvals
    path('teacher-approvals/', views.teacher_approvals_view, name='teacher_approvals'),
    path('teachers/<int:pk>/approve/', views.approve_teacher_view, name='approve_teacher'),
    path('teachers/<int:pk>/reject/', views.reject_teacher_view, name='reject_teacher'),

    # User management
    path('users/', views.user_management_view, name='user_management'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/export/', views.user_export_view, name='user_export'),
    path('users/bulk/', views.user_bulk_action_view, name='user_bulk_action'),
    path('users/<int:pk>/', views.user_detail_view, name='user_detail'),
    path('users/<int:pk>/edit/', views.user_edit_view, name='user_edit'),
    path('users/<int:pk>/reset-password/', views.user_reset_password_view, name='user_reset_password'),

    # Teacher management
    path('teachers/', views.teacher_management_view, name='teacher_management'),
    path('students/', views.student_management_view, name='student_management'),

    # Subject export
    path('subjects/export/', views.subject_export_view, name='subject_export'),
    path('subjects/bulk/', views.subject_bulk_action_view, name='subject_bulk_action'),



    # Classroom management
    path('classrooms/', views.classroom_management_view, name='classroom_management'),
    path('classrooms/export/', views.classroom_export_view, name='classroom_export'),
    path('classrooms/bulk/', views.classroom_bulk_action_view, name='classroom_bulk_action'),
    path('classrooms/<int:pk>/approve/', views.approve_classroom_view, name='approve_classroom'),
    path('classrooms/<int:pk>/reject/', views.reject_classroom_view, name='reject_classroom'),

    # Subject management
    path('subjects/', views.subject_management_view, name='subject_approvals'),
    path('subjects/<int:pk>/approve/', views.approve_subject_view, name='approve_subject'),
    path('subjects/<int:pk>/reject/', views.reject_subject_view, name='reject_subject'),

    # Programming languages
    path('languages/', views.language_list_view, name='languages'),
    path('languages/create/', views.language_create_view, name='language_create'),
    path('languages/<int:pk>/edit/', views.language_edit_view, name='language_edit'),
    path('languages/<int:pk>/delete/', views.language_delete_view, name='language_delete'),
    path('languages/<int:pk>/toggle/', views.language_toggle_view, name='language_toggle'),

    # Sandbox configs
    path('sandboxes/', views.sandbox_list_view, name='sandboxes'),
    path('sandboxes/create/', views.sandbox_create_view, name='sandbox_create'),
    path('sandboxes/<int:pk>/edit/', views.sandbox_edit_view, name='sandbox_edit'),
    path('sandboxes/<int:pk>/delete/', views.sandbox_delete_view, name='sandbox_delete'),
    path('sandboxes/<int:pk>/test/', views.sandbox_test_view, name='sandbox_test'),

    # Server metrics
    path('metrics/', views.server_metrics_view, name='metrics'),

    # System settings
    path('settings/', views.system_settings_view, name='system_settings'),
    path('settings/create/', views.system_setting_create_view, name='setting_create'),
    path('settings/<int:pk>/edit/', views.system_setting_edit_view, name='setting_edit'),
    path('settings/<int:pk>/delete/', views.system_setting_delete_view, name='setting_delete'),
    path('settings/<int:pk>/toggle/', views.system_setting_toggle_view, name='setting_toggle'),

    # Activity logs
    path('logs/', views.activity_logs_view, name='activity_logs'),
    path('logs/export/', views.activity_logs_export_view, name='activity_logs_export'),
    path('exam-events/', views.exam_events_view, name='exam_events'),
    path('exam-events/export/', views.exam_events_export_view, name='exam_events_export'),

    # Analytics (reporting)
    path('analytics/', views.analytics_view, name='analytics'),

    # Sandbox monitor (Docker containers + queue + zombie tasks)
    path('sandbox-monitor/', views.sandbox_monitor_view, name='sandbox_monitor'),
    path('sandbox-monitor/kill/<int:submission_pk>/', views.kill_zombie_view, name='kill_zombie'),
    path('sandbox-monitor/requeue/<int:submission_pk>/', views.requeue_zombie_view, name='requeue_zombie'),
]
