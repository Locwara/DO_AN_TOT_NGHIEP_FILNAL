from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import CustomPasswordResetForm, CustomSetPasswordForm

app_name = 'accounts'

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/<int:user_id>/', views.profile_view, name='profile_detail'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('dashboard/', views.student_dashboard_view, name='student_dashboard'),
    path('teacher-dashboard/', views.teacher_dashboard_view, name='teacher_dashboard'),
    path('teacher-register/', views.teacher_register_view, name='teacher_register'),

    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        form_class=CustomPasswordResetForm,
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url='/accounts/password-reset/done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        form_class=CustomSetPasswordForm,
        success_url='/accounts/password-reset-complete/',
    ), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
]
