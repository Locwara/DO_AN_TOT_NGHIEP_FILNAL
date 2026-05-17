from django import forms
from django.db.models import Q
from apps.classrooms.models import ClassroomSubjects, SubjectApprovalStatus
from .models import Assignments, Testcases, Rubrics


class AssignmentForm(forms.ModelForm):
    classroom_subject = forms.ModelChoiceField(
        queryset=ClassroomSubjects.objects.none(),
        required=False,
        empty_label='-- Chưa phân môn --',
        label='Môn học (trong lớp)',
        help_text='Gắn bài tập với (môn + kỳ học) của lớp. Có thể để trống.',
    )

    class Meta:
        model = Assignments
        fields = [
            'title', 'description', 'instructions', 'type', 'difficulty',
            'start_date', 'due_date', 'late_submission_allowed', 'late_penalty_percent',
            'max_score', 'max_attempts', 'show_testcase_result', 'enable_leaderboard',
            'is_exam', 'exam_duration_minutes', 'exam_start_time', 'exam_end_time',
            'exam_require_fullscreen', 'exam_allow_custom_input',
            'exam_allow_sample_run', 'exam_max_run_count', 'exam_grace_seconds',
            'classroom_subject',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Tên bài tập'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Mô tả ngắn về bài tập...'}),
            'instructions': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Hướng dẫn chi tiết (hỗ trợ Markdown)...'}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'exam_start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'exam_end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'max_score': forms.NumberInput(attrs={'min': 1}),
            'max_attempts': forms.NumberInput(attrs={'min': 1}),
            'exam_duration_minutes': forms.NumberInput(attrs={'min': 1, 'placeholder': 'Thời gian làm bài (phút)'}),
            'exam_max_run_count': forms.NumberInput(attrs={'min': 1, 'placeholder': 'Không giới hạn'}),
            'exam_grace_seconds': forms.NumberInput(attrs={'min': 0, 'max': 600}),
        }

    DIFFICULTY_CHOICES = [
        ('', '-- Chọn độ khó --'),
        ('easy', 'Dễ'),
        ('medium', 'Trung bình'),
        ('hard', 'Khó'),
        ('expert', 'Nâng cao'),
    ]

    TYPE_CHOICES = [
        ('auto_grade', 'Chấm tự động'),
        ('manual_grade', 'Chấm thủ công'),
        ('project', 'Đồ án'),
    ]

    difficulty = forms.ChoiceField(choices=DIFFICULTY_CHOICES, required=False)
    type = forms.ChoiceField(choices=TYPE_CHOICES)
    late_penalty_percent = forms.FloatField(required=False, min_value=0, max_value=100,
                                            widget=forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 1}))

    def __init__(self, *args, **kwargs):
        classroom = kwargs.pop('classroom', None)
        super().__init__(*args, **kwargs)
        self.fields['start_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['due_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['exam_start_time'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['exam_end_time'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['exam_duration_minutes'].required = False
        self.fields['exam_start_time'].required = False
        self.fields['exam_end_time'].required = False
        self.fields['exam_max_run_count'].required = False
        self.fields['exam_grace_seconds'].required = False

        # Chỉ hiển thị ClassroomSubjects của lớp này (nếu được truyền vào)
        target_classroom_id = None
        if classroom is not None:
            target_classroom_id = classroom.pk
        elif self.instance and self.instance.pk and self.instance.classroom_id:
            target_classroom_id = self.instance.classroom_id

        if target_classroom_id is not None:
            base_filter = Q(
                classroom_id=target_classroom_id,
                is_active=True,
                subject__is_active=True,
                subject__status=SubjectApprovalStatus.APPROVED,
            )
            # Luôn include classroom_subject hiện tại (nếu đang edit) để tránh mất giá trị
            if self.instance and self.instance.pk and self.instance.classroom_subject_id:
                base_filter = base_filter | Q(pk=self.instance.classroom_subject_id)
            qs = ClassroomSubjects.objects.filter(base_filter).select_related(
                'subject', 'semester'
            ).order_by('-semester__is_current', '-semester__start_date', 'subject__code').distinct()
            self.fields['classroom_subject'].queryset = qs

    def clean_late_penalty_percent(self):
        value = self.cleaned_data.get('late_penalty_percent')
        if value is None:
            return 0
        return value

    def clean(self):
        cleaned = super().clean()
        start_date = cleaned.get('start_date')
        due_date = cleaned.get('due_date')
        is_exam = cleaned.get('is_exam')
        exam_start = cleaned.get('exam_start_time')
        exam_end = cleaned.get('exam_end_time')
        duration = cleaned.get('exam_duration_minutes')
        max_attempts = cleaned.get('max_attempts')
        max_score = cleaned.get('max_score')
        late_penalty = cleaned.get('late_penalty_percent')
        exam_max_run_count = cleaned.get('exam_max_run_count')
        grace = cleaned.get('exam_grace_seconds')

        if start_date and due_date and due_date < start_date:
            raise forms.ValidationError('Hạn nộp phải sau ngày bắt đầu.')
        if max_score is None or max_score <= 0:
            self.add_error('max_score', 'Điểm tối đa phải lớn hơn 0.')
        if max_attempts is not None and max_attempts <= 0:
            self.add_error('max_attempts', 'Số lần nộp tối đa phải lớn hơn 0.')
        if late_penalty is not None and not 0 <= late_penalty <= 100:
            self.add_error('late_penalty_percent', 'Phần trăm phạt trễ phải từ 0 đến 100.')
        if is_exam:
            if not duration or duration <= 0:
                self.add_error('exam_duration_minutes', 'Bài thi cần có thời gian làm bài.')
            if exam_start and due_date and exam_start > due_date:
                self.add_error('exam_start_time', 'Giờ bắt đầu thi không được sau hạn nộp.')
            if exam_start and exam_end and exam_end < exam_start:
                self.add_error('exam_end_time', 'Giờ đóng phòng thi phải sau giờ bắt đầu.')
            if not max_attempts:
                cleaned['max_attempts'] = 1
            if exam_max_run_count is not None and exam_max_run_count <= 0:
                self.add_error('exam_max_run_count', 'Số lần chạy thử trong bài thi phải lớn hơn 0.')
        if not cleaned.get('late_submission_allowed'):
            cleaned['late_penalty_percent'] = 0
        if grace is None:
            cleaned['exam_grace_seconds'] = 30
        elif grace < 0:
            self.add_error('exam_grace_seconds', 'Thời gian grace không được âm.')
        return cleaned


class TestcaseImportForm(forms.Form):
    """Form để import nhiều testcase cùng lúc qua JSON hoặc CSV, hoặc nhập trực tiếp."""
    FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('csv', 'CSV'),
    ]
    import_format = forms.ChoiceField(
        choices=FORMAT_CHOICES,
        initial='json',
        widget=forms.RadioSelect,
    )
    file = forms.FileField(
        required=False,
        help_text='Upload file JSON/CSV. Hoặc dán nội dung vào ô bên dưới.',
    )
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 12,
            'class': 'font-mono',
            'placeholder': '[\n  {"name": "Test 1", "input": "1 2", "expected_output": "3", "is_sample": true, "weight": 1.0},\n  {"name": "Test 2", "input": "5 7", "expected_output": "12", "is_hidden": true, "weight": 2.0}\n]',
        }),
        help_text='Dán JSON array hoặc CSV (header: name,input,expected_output,is_sample,is_hidden,weight).',
    )
    clear_existing = forms.BooleanField(
        required=False,
        initial=False,
        help_text='Xóa tất cả testcase hiện có trước khi import (nếu bật).',
    )

    def clean_file(self):
        uploaded = self.cleaned_data.get('file')
        if not uploaded:
            return uploaded
        max_size = 1 * 1024 * 1024
        if uploaded.size > max_size:
            raise forms.ValidationError('File testcase tối đa 1MB.')
        name = (uploaded.name or '').lower()
        if not (name.endswith('.json') or name.endswith('.csv')):
            raise forms.ValidationError('Chỉ hỗ trợ file .json hoặc .csv.')
        return uploaded

    def clean(self):
        data = super().clean()
        has_file = bool(data.get('file'))
        has_content = bool((data.get('content') or '').strip())
        if not has_file and not has_content:
            raise forms.ValidationError('Vui lòng upload file hoặc dán nội dung.')
        return data


class TestcaseForm(forms.ModelForm):
    class Meta:
        model = Testcases
        fields = [
            'name', 'input_data', 'expected_output', 'is_hidden', 'is_sample',
            'weight', 'timeout_override', 'memory_override', 'order_index',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Tên testcase (vd: Test cơ bản #1)'}),
            'input_data': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Dữ liệu đầu vào...', 'class': 'font-mono'}),
            'expected_output': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Kết quả mong đợi...', 'class': 'font-mono'}),
            'weight': forms.NumberInput(attrs={'min': 0, 'step': 0.1, 'placeholder': '1.0'}),
            'timeout_override': forms.NumberInput(attrs={'min': 1, 'placeholder': 'Giây (mặc định theo cấu hình)'}),
            'memory_override': forms.NumberInput(attrs={'min': 1, 'placeholder': 'MB (mặc định theo cấu hình)'}),
            'order_index': forms.NumberInput(attrs={'min': 0}),
        }


class RubricForm(forms.ModelForm):
    class Meta:
        model = Rubrics
        fields = ['name', 'description', 'max_points', 'order_index']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'VD: Đúng thuật toán'}),
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Mô tả tiêu chí...'}),
            'max_points': forms.NumberInput(attrs={'step': '0.5', 'min': 0}),
            'order_index': forms.NumberInput(attrs={'min': 0}),
        }

    def clean_name(self):
        value = (self.cleaned_data.get('name') or '').strip()
        if not value:
            raise forms.ValidationError('Tên tiêu chí là bắt buộc.')
        return value

    def clean_max_points(self):
        value = self.cleaned_data.get('max_points')
        if value is None or value <= 0:
            raise forms.ValidationError('Điểm tối đa phải lớn hơn 0.')
        return value
