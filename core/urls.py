from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import home_view, user_guide, terms_policies, submit_feedback

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
    path('huong-dan/', user_guide, name='user_guide'),
    path('chinh-sach/', terms_policies, name='terms_policies'),
    path('bao-loi/', submit_feedback, name='submit_feedback'),
    path('', home_view, name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
