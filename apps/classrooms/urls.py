from django.urls import path
from . import views

app_name = 'classrooms'

urlpatterns = [
    path('', views.classroom_list_view, name='classroom_list'),
    path('search/', views.search_classroom_view, name='search'),
    path('create/', views.create_classroom_view, name='create'),
    path('join/', views.join_classroom_view, name='join'),
    # Semester management (admin)
    path('semesters/', views.semester_list_view, name='semester_list'),
    path('semesters/create/', views.semester_create_view, name='semester_create'),
    path('semesters/<int:pk>/edit/', views.semester_edit_view, name='semester_edit'),
    path('semesters/<int:pk>/delete/', views.semester_delete_view, name='semester_delete'),
    path('<int:pk>/', views.classroom_detail_view, name='classroom_detail'),
    path('<int:pk>/gradebook/', views.gradebook_view, name='gradebook'),
    path('<int:pk>/gradebook/export/', views.gradebook_export_view, name='gradebook_export'),
    path('<int:pk>/gradebook/export-missing/', views.gradebook_missing_export_view, name='gradebook_missing_export'),
    path('<int:pk>/members/export/', views.classroom_members_export_view, name='members_export'),
    path('<int:pk>/edit/', views.edit_classroom_view, name='edit'),
    path('<int:pk>/delete/', views.delete_classroom_view, name='delete'),
    path('<int:pk>/leave/', views.leave_classroom_view, name='leave'),
    path('<int:pk>/quick-join/', views.quick_join_classroom_view, name='quick_join'),
    path('<int:pk>/leaderboard/', views.leaderboard_view, name='leaderboard'),
    path('<int:pk>/members/import/', views.import_members_view, name='import_members'),
    # Subject name-availability check (AJAX)
    path('subjects/check-name/', views.check_subject_name_view, name='subject_check_name'),
    path('<int:pk>/subjects/', views.classroom_subjects_view, name='subjects'),
    path('<int:pk>/subjects/create/', views.create_subject_view, name='subject_create'),
    path('<int:pk>/subjects/assign/', views.assign_subject_view, name='subject_assign'),
    path('<int:pk>/subjects/<int:link_pk>/', views.classroom_subject_detail_view, name='subject_detail'),
    path('<int:classroom_pk>/subjects/<int:subject_pk>/edit/', views.edit_subject_view, name='subject_edit'),
    path('<int:classroom_pk>/subjects/<int:subject_pk>/delete/', views.delete_subject_view, name='subject_delete'),
    path('<int:pk>/members/<int:member_id>/approve/', views.approve_member_view, name='approve_member'),
    path('<int:pk>/members/<int:member_id>/remove/', views.remove_member_view, name='remove_member'),
    path('<int:pk>/announcements/create/', views.create_announcement_view, name='create_announcement'),
    path('<int:pk>/announcements/<int:announcement_id>/pin/', views.pin_announcement_view, name='pin_announcement'),
    path('<int:pk>/announcements/<int:announcement_id>/delete/', views.delete_announcement_view, name='delete_announcement'),
]
