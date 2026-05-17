from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from .models import Profiles, TeacherRegistrations


class RegisterForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Nguyen Van A'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'email@example.com'})
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )

    class Meta:
        model = User
        fields = ['username', 'email']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email này đã được sử dụng.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', 'Mật khẩu xác nhận không khớp.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data.get('full_name', '')
        parts = full_name.strip().split(' ', 1)
        user.first_name = parts[0]
        user.last_name = parts[1] if len(parts) > 1 else ''
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
            Profiles.objects.create(id=user, role='student')
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Username'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'})
    )


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)

    class Meta:
        model = Profiles
        fields = ['avatar_url', 'bio', 'phone']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Giới thiệu về bản thân...'}),
            'phone': forms.TextInput(attrs={'placeholder': '+84 xxx xxx xxx'}),
            'avatar_url': forms.URLInput(attrs={'placeholder': 'https://...'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email


class TeacherRegistrationForm(forms.ModelForm):
    class Meta:
        model = TeacherRegistrations
        fields = ['institution', 'reason', 'proof_document_url']
        widgets = {
            'institution': forms.TextInput(attrs={'placeholder': 'Tên trường / tổ chức'}),
            'reason': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Lý do bạn muốn trở thành giáo viên...'}),
            'proof_document_url': forms.URLInput(attrs={'placeholder': 'Link tài liệu minh chứng (Google Drive, Cloudinary...)'}),
        }


class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'email@example.com'})
    )


class CustomSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Mật khẩu mới'})
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Xác nhận mật khẩu mới'})
    )
