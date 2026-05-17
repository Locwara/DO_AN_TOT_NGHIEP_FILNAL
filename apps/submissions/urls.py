from django.urls import path
from . import views

app_name = 'submissions'

urlpatterns = [
    path('solve/<int:assignment_pk>/', views.solve_problem_view, name='solve'),
    path('exam/<int:assignment_pk>/', views.exam_lobby_view, name='exam_lobby'),
    path('exam/<int:assignment_pk>/start/', views.start_exam_view, name='start_exam'),
    path('exam/<int:assignment_pk>/ide/', views.exam_ide_view, name='exam_ide'),
    path('exam/<int:assignment_pk>/ping/', views.exam_ping_view, name='exam_ping'),
    path('exam/<int:assignment_pk>/event/', views.exam_event_view, name='exam_event'),
    path('exam/<int:assignment_pk>/monitor/', views.exam_monitor_view, name='exam_monitor'),
    path('exam/<int:assignment_pk>/monitor/export/', views.exam_monitor_export_view, name='exam_monitor_export'),
    path('exam-session/<int:session_pk>/extend/', views.extend_exam_session_view, name='extend_exam_session'),
    path('exam-session/<int:session_pk>/force-submit/', views.force_submit_exam_session_view, name='force_submit_exam_session'),
    path('save-draft/', views.save_draft_view, name='save_draft'),
    path('run-test/<int:assignment_pk>/', views.run_test_view, name='run_test'),
    path('submit/<int:assignment_pk>/', views.submit_code_view, name='submit'),
    path('history/<int:assignment_pk>/', views.submission_history_view, name='history'),
    path('detail/<int:pk>/', views.submission_detail_view, name='detail'),
    path('teacher-list/<int:assignment_pk>/', views.submission_list_teacher_view, name='teacher_list'),
    path('grade/<int:pk>/', views.grade_submission_view, name='grade'),
    path('comment/<int:pk>/', views.add_code_comment_view, name='add_comment'),
    path('grade/<int:pk>/feedback-template/<int:template_pk>/delete/', views.delete_feedback_template_view, name='delete_feedback_template'),
    path('resolve-comment/<int:pk>/', views.resolve_comment_view, name='resolve_comment'),
]
