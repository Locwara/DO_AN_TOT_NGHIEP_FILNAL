from django.urls import path
from . import views

app_name = 'assignments'

urlpatterns = [
    path('calendar/', views.calendar_view, name='calendar'),
    path('calendar/events/', views.calendar_events_view, name='calendar_events'),
    path('classroom/<int:classroom_pk>/', views.assignment_list_view, name='list'),
    path('classroom/<int:classroom_pk>/create/', views.create_assignment_view, name='create'),
    path('<int:pk>/', views.assignment_detail_view, name='detail'),
    path('<int:pk>/edit/', views.edit_assignment_view, name='edit'),
    path('<int:pk>/clone/', views.clone_assignment_view, name='clone'),
    path('<int:pk>/delete/', views.delete_assignment_view, name='delete'),
    path('<int:pk>/publish/', views.toggle_publish_view, name='toggle_publish'),
    path('<int:pk>/statistics/', views.statistics_view, name='statistics'),
    path('<int:pk>/plagiarism/', views.plagiarism_view, name='plagiarism'),
    path('<int:pk>/plagiarism/run/', views.run_plagiarism_view, name='run_plagiarism'),
    path('<int:pk>/rubrics/add/', views.add_rubric_view, name='add_rubric'),
    path('<int:pk>/rubrics/<int:rubric_pk>/delete/', views.delete_rubric_view, name='delete_rubric'),
    path('<int:pk>/testcases/add/', views.add_testcase_view, name='add_testcase'),
    path('<int:pk>/testcases/import/', views.import_testcases_view, name='import_testcases'),
    path('<int:pk>/testcases/<int:tc_pk>/edit/', views.edit_testcase_view, name='edit_testcase'),
    path('<int:pk>/testcases/<int:tc_pk>/delete/', views.delete_testcase_view, name='delete_testcase'),
    path('<int:pk>/files/upload/', views.upload_file_view, name='upload_file'),
    path('<int:pk>/files/<int:file_pk>/delete/', views.delete_file_view, name='delete_file'),
    # Bulk operations
    path('<int:pk>/bulk-regrade/', views.bulk_regrade_view, name='bulk_regrade'),
    path('<int:pk>/export-late/', views.export_late_report_view, name='export_late'),
    path('<int:pk>/export-submissions/', views.export_assignment_submissions_view, name='export_submissions'),
    path('<int:pk>/export-scores/', views.export_assignment_scores_view, name='export_scores'),
    path('<int:pk>/export-missing/', views.export_assignment_missing_view, name='export_missing'),
    path('<int:pk>/late-report/print/', views.late_report_print_view, name='late_report_print'),
]
