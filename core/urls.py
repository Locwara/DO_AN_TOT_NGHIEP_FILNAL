from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

admin.site.site_header = 'LH Programming — Quản trị hệ thống'
admin.site.site_title = 'LH Programming Admin'
admin.site.index_title = 'Bảng điều khiển'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('classrooms/', include('apps.classrooms.urls')),
    path('assignments/', include('apps.assignments.urls')),
    path('submissions/', include('apps.submissions.urls')),
    path('discussions/', include('apps.discussions.urls')),
    path('administration/', include('apps.administation.urls')),
    path('notifications/', include('apps.notifications.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]
