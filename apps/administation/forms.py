from django import forms
from django.contrib.auth.models import User
from .models import ProgrammingLanguages, SandboxConfigs, SystemSettings


ROLE_CHOICES = [
    ('student', 'Học sinh'),
    ('teacher', 'Giáo viên'),
    ('admin', 'Admin'),
]


SYSTEM_SETTING_SCHEMAS = {
    'exam.default_grace_seconds': {
        'type': int,
        'min': 0,
        'max': 600,
        'description': 'Grace period mặc định cho bài thi, tính bằng giây.',
    },
    'exam.require_fullscreen_default': {
        'type': bool,
        'description': 'Mặc định yêu cầu fullscreen khi tạo bài thi.',
    },
    'exam.allow_custom_input_default': {
        'type': bool,
        'description': 'Mặc định cho phép custom input trong bài thi.',
    },
    'notifications.due_soon_hours': {
        'type': int,
        'min': 1,
        'max': 336,
        'description': 'Số giờ trước deadline để gửi notification nhắc hạn.',
    },
    'sandbox.zombie_threshold_minutes': {
        'type': int,
        'min': 1,
        'max': 1440,
        'description': 'Số phút pending/running để coi submission là zombie.',
    },
    'uploads.assignment_max_mb': {
        'type': int,
        'min': 1,
        'max': 50,
        'description': 'Dung lượng tối đa cho file đính kèm bài tập, tính bằng MB.',
    },
    'uploads.submission_allowed_extensions': {
        'type': list,
        'default': ['.pdf', '.docx', '.zip', '.py', '.cpp'],
        'item_type': str,
        'description': 'Danh sách extension mặc định khi giáo viên tạo bài nộp file.',
    },
    'uploads.submission_default_max_mb': {
        'type': int,
        'min': 1,
        'max': 100,
        'default': 20,
        'description': 'Dung lượng tối đa mặc định mỗi file học sinh nộp, tính bằng MB.',
    },
    'uploads.submission_default_max_files': {
        'type': int,
        'min': 1,
        'max': 20,
        'default': 1,
        'description': 'Số file tối đa mặc định cho mỗi lượt nộp file.',
    },
    'uploads.submission_scan_required_default': {
        'type': bool,
        'default': False,
        'description': 'Mặc định yêu cầu scan file trước khi giáo viên chấm.',
    },
    'quiz.default_max_attempts': {
        'type': int,
        'min': 1,
        'max': 50,
        'default': 2,
        'description': 'Số lần làm mặc định cho bài tập trắc nghiệm.',
    },
    'quiz.random_questions_default': {
        'type': bool,
        'default': False,
        'description': 'Mặc định đảo thứ tự câu hỏi khi tạo quiz.',
    },
    'quiz.random_choices_default': {
        'type': bool,
        'default': False,
        'description': 'Mặc định đảo thứ tự đáp án khi tạo quiz.',
    },
    'quiz.show_score_after_submit_default': {
        'type': bool,
        'default': True,
        'description': 'Mặc định cho học sinh thấy điểm sau khi nộp quiz.',
    },
    'quiz.show_correct_answers_default': {
        'type': bool,
        'default': False,
        'description': 'Mặc định cho học sinh thấy đáp án đúng sau khi nộp quiz.',
    },
    'quiz.allow_review_default': {
        'type': bool,
        'default': True,
        'description': 'Mặc định cho học sinh xem lại bài quiz sau khi nộp.',
    },
}


class AdminUserForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    is_active = forms.BooleanField(required=False, initial=True)
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput,
        help_text='Bắt buộc khi tạo user mới. Để trống khi chỉnh sửa nếu không đổi mật khẩu.',
    )

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        if instance is None:
            self.fields['password'].required = True

    def clean_username(self):
        value = (self.cleaned_data.get('username') or '').strip()
        qs = User.objects.filter(username__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Username này đã tồn tại.')
        return value

    def clean_email(self):
        value = (self.cleaned_data.get('email') or '').strip()
        if not value:
            return value
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError('Email này đã tồn tại.')
        return value


class AdminPasswordResetForm(forms.Form):
    new_password = forms.CharField(min_length=8, widget=forms.PasswordInput)
    confirm_password = forms.CharField(min_length=8, widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('new_password') != cleaned.get('confirm_password'):
            raise forms.ValidationError('Mật khẩu xác nhận không khớp.')
        return cleaned


class ProgrammingLanguageForm(forms.ModelForm):
    class Meta:
        model = ProgrammingLanguages
        fields = [
            'name', 'display_name', 'version', 'file_extension',
            'is_active', 'syntax_highlight_mode', 'default_template',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'python'}),
            'display_name': forms.TextInput(attrs={'placeholder': 'Python 3.11'}),
            'version': forms.TextInput(attrs={'placeholder': '3.11'}),
            'file_extension': forms.TextInput(attrs={'placeholder': '.py'}),
            'syntax_highlight_mode': forms.TextInput(attrs={'placeholder': 'python'}),
            'default_template': forms.Textarea(attrs={'rows': 5, 'placeholder': '# Write your code here...', 'class': 'font-mono'}),
        }

    def clean_name(self):
        value = (self.cleaned_data.get('name') or '').strip().lower()
        if not value:
            raise forms.ValidationError('Tên ngôn ngữ là bắt buộc.')
        if ' ' in value:
            raise forms.ValidationError('Tên ngôn ngữ không nên chứa khoảng trắng, ví dụ: python, cpp, javascript.')
        return value


class SandboxConfigForm(forms.ModelForm):
    class Meta:
        model = SandboxConfigs
        fields = [
            'language', 'docker_image', 'timeout_seconds',
            'memory_limit_mb', 'cpu_limit', 'is_active',
        ]
        widgets = {
            'language': forms.TextInput(attrs={'placeholder': 'python'}),
            'docker_image': forms.TextInput(attrs={'placeholder': 'python:3.11-alpine'}),
            'timeout_seconds': forms.NumberInput(attrs={'min': 1, 'max': 60}),
            'memory_limit_mb': forms.NumberInput(attrs={'min': 32, 'max': 1024}),
            'cpu_limit': forms.NumberInput(attrs={'min': 0.1, 'max': 4.0, 'step': 0.1}),
        }

    def clean_docker_image(self):
        value = (self.cleaned_data.get('docker_image') or '').strip()
        if not value or any(ch.isspace() for ch in value):
            raise forms.ValidationError('Docker image không hợp lệ.')
        if ':' not in value:
            raise forms.ValidationError('Nên chỉ rõ tag image, ví dụ python:3.11-alpine.')
        return value

    def clean(self):
        cleaned = super().clean()
        timeout = cleaned.get('timeout_seconds')
        memory = cleaned.get('memory_limit_mb')
        cpu = cleaned.get('cpu_limit')
        if timeout is not None and not 1 <= timeout <= 60:
            self.add_error('timeout_seconds', 'Timeout phải từ 1 đến 60 giây.')
        if memory is not None and not 32 <= memory <= 1024:
            self.add_error('memory_limit_mb', 'Memory phải từ 32MB đến 1024MB.')
        if cpu is not None and not 0.1 <= cpu <= 4:
            self.add_error('cpu_limit', 'CPU limit phải từ 0.1 đến 4.')
        return cleaned


class SystemSettingForm(forms.ModelForm):
    class Meta:
        model = SystemSettings
        fields = ['setting_key', 'setting_value', 'description']
        widgets = {
            'setting_key': forms.TextInput(attrs={'placeholder': 'max_upload_size'}),
            'setting_value': forms.Textarea(attrs={'rows': 4, 'placeholder': '{"value": 50}', 'class': 'font-mono'}),
            'description': forms.TextInput(attrs={'placeholder': 'Mô tả cài đặt...'}),
        }

    def clean_setting_key(self):
        value = (self.cleaned_data.get('setting_key') or '').strip()
        if not value:
            raise forms.ValidationError('Setting key là bắt buộc.')
        return value

    def clean_setting_value(self):
        import json
        value = self.cleaned_data['setting_value']
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                raise forms.ValidationError('Giá trị phải là JSON hợp lệ.')
        key = (self.cleaned_data.get('setting_key') or '').strip()
        schema = SYSTEM_SETTING_SCHEMAS.get(key)
        if schema:
            expected_type = schema['type']
            if expected_type is int and isinstance(value, bool):
                raise forms.ValidationError('Giá trị phải là số nguyên.')
            if not isinstance(value, expected_type):
                type_label = {
                    bool: 'boolean',
                    int: 'integer',
                    list: 'array',
                    str: 'string',
                    float: 'float',
                }.get(expected_type, 'JSON')
                raise forms.ValidationError(f'Giá trị của key này phải là {type_label}.')
            if expected_type is int:
                minimum = schema.get('min')
                maximum = schema.get('max')
                if minimum is not None and value < minimum:
                    raise forms.ValidationError(f'Giá trị phải >= {minimum}.')
                if maximum is not None and value > maximum:
                    raise forms.ValidationError(f'Giá trị phải <= {maximum}.')
            if expected_type is list:
                item_type = schema.get('item_type')
                if item_type and any(not isinstance(item, item_type) for item in value):
                    raise forms.ValidationError('Các phần tử trong array không đúng kiểu.')
                if key == 'uploads.submission_allowed_extensions':
                    invalid = [
                        item for item in value
                        if not isinstance(item, str) or not item.startswith('.') or len(item) > 16
                    ]
                    if invalid:
                        raise forms.ValidationError('Extension phải có dạng .pdf, .docx, .py...')
        return value
