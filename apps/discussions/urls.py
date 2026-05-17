from django.urls import path
from . import views

app_name = 'discussions'

urlpatterns = [
    path('assignment/<int:assignment_pk>/', views.discussion_list_view, name='list'),
    path('assignment/<int:assignment_pk>/create/', views.create_discussion_view, name='create'),
    path('<int:pk>/', views.discussion_detail_view, name='detail'),
    path('<int:pk>/edit/', views.edit_discussion_view, name='edit'),
    path('<int:pk>/delete/', views.delete_discussion_view, name='delete'),
    path('<int:pk>/vote/', views.vote_discussion_view, name='vote'),
    path('<int:pk>/mark-answer/', views.mark_answer_view, name='mark_answer'),
    path('<int:pk>/pin/', views.pin_discussion_view, name='pin'),
]
