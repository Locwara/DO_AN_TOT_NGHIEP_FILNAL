from django import forms
from django.db.models import Q
from apps.administation.utils import get_bool_setting, get_int_setting, get_list_setting
from apps.classrooms.models import ClassroomSubjects, SubjectApprovalStatus
from .models import (
    Assignments, AssignmentFileRequirements, Testcases, Rubrics,
    QuizSettings, QuizQuestions,
)


class AssignmentForm(forms.ModelForm):
    max_score = forms.FloatField(
        initial=100, 
        label='Điểm tối đa', 
        widget=forms.NumberInput(attrs={'readonly': 'readonly', 'class': 'bg-slate-100 cursor-not-allowed'})
    )
    FILE_EXTENSION_CHOICES = [
        ('.pdf', 'PDF'),
        ('.doc', 'DOC'),
        ('.docx', 'DOCX'),
        ('.xls', 'XLS'),
        ('.xlsx', 'XLSX'),
        ('.ppt', 'PPT'),
        ('.pptx', 'PPTX'),
        ('.zip', 'ZIP'),
        ('.rar', 'RAR'),
        ('.py', 'Python'),
        ('.cpp', 'C++'),
        ('.java', 'Java'),
        ('.js', 'JavaScript'),
        ('.html', 'HTML'),
        ('.css', 'CSS'),
        ('.txt', 'TXT'),
        ('.md', 'Markdown'),
    ]
    MIME_TYPE_BY_EXTENSION = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.zip': 'application/zip',
        '.rar': 'application/vnd.rar',
        '.py': 'text/x-python',
        '.cpp': 'text/x-c++src',
        '.java': 'text/x-java-source',
        '.js': 'application/javascript',
        '.html': 'text/html',
        '.css': 'text/css',
        '.txt': 'text/plain',
        '.md': 'text/markdown',
    }

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
            'title', 'description', 'instructions', 'starter_code', 
            'solution_code', 'solution_language',
            'submission_mode', 'grading_mode',
            'type', 'difficulty',
            'start_date', 'due_date', 'late_submission_allowed', 'late_penalty_percent',
            'max_score', 'max_attempts', 'score_aggregation_mode', 'show_testcase_result', 'enable_leaderboard',
            'is_exam', 'exam_duration_minutes', 'exam_start_time', 'exam_end_time',
            'exam_require_fullscreen', 'exam_allow_custom_input',
            'exam_allow_sample_run', 'exam_max_run_count', 'exam_grace_seconds',
            'quiz_random_questions', 'quiz_random_choices', 
            'quiz_show_correct_answers', 'quiz_show_explanation', 
            'quiz_show_score_after_submit', 'quiz_allow_review',
            'quiz_time_limit_minutes', 'quiz_passing_score',
            'classroom_subject',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Tên bài tập'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Mô tả ngắn về bài tập...'}),
            'instructions': forms.Textarea(attrs={'rows': 8, 'placeholder': 'Hướng dẫn chi tiết (hỗ trợ Markdown)...'}),
            'starter_code': forms.Textarea(attrs={'rows': 10, 'placeholder': 'VD: def solution():\n    pass', 'class': 'font-mono'}),
            'solution_code': forms.Textarea(attrs={'rows': 12, 'placeholder': 'Nhập mã nguồn mẫu để hệ thống kiểm tra testcase...', 'class': 'font-mono bg-slate-900 text-green-400'}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'exam_start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'exam_end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
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

    SUBMISSION_MODE_CHOICES = Assignments.SUBMISSION_MODE_CHOICES
    GRADING_MODE_CHOICES = Assignments.GRADING_MODE_CHOICES

    submission_mode = forms.ChoiceField(
        choices=SUBMISSION_MODE_CHOICES,
        initial=Assignments.SUBMISSION_CODE,
    )
    grading_mode = forms.ChoiceField(
        choices=GRADING_MODE_CHOICES,
        initial=Assignments.GRADING_AUTO,
    )
    difficulty = forms.ChoiceField(choices=DIFFICULTY_CHOICES, required=False)
    type = forms.ChoiceField(choices=TYPE_CHOICES, required=False, widget=forms.HiddenInput)
    late_penalty_percent = forms.FloatField(required=False, min_value=0, max_value=100,
                                            widget=forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 1}))
    file_allowed_extensions = forms.MultipleChoiceField(
        choices=FILE_EXTENSION_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Định dạng file cho phép',
    )
    file_max_size_mb = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
        initial=20,
        label='Dung lượng tối đa mỗi file',
        widget=forms.NumberInput(attrs={'min': 1, 'max': 100}),
    )
    file_max_files = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=20,
        initial=1,
        label='Số lượng file tối đa',
        widget=forms.NumberInput(attrs={'min': 1, 'max': 20}),
    )
    file_require_comment = forms.BooleanField(required=False, label='Yêu cầu học sinh ghi chú khi nộp')
    file_allow_resubmit = forms.BooleanField(required=False, initial=True, label='Cho phép nộp lại')
    file_require_all_files_before_submit = forms.BooleanField(required=False, initial=True, label='Yêu cầu đủ file trước khi nộp')
    file_scan_required = forms.BooleanField(required=False, label='Yêu cầu quét file trước khi chấm')
    quiz_random_questions = forms.BooleanField(required=False, label='Đảo thứ tự câu hỏi')
    quiz_random_choices = forms.BooleanField(required=False, label='Đảo thứ tự đáp án')
    quiz_show_score_after_submit = forms.BooleanField(required=False, initial=True, label='Hiện điểm sau khi nộp')
    quiz_show_correct_answers = forms.BooleanField(required=False, label='Hiện đáp án đúng')
    quiz_show_explanation = forms.BooleanField(required=False, label='Hiện giải thích')
    quiz_allow_review = forms.BooleanField(required=False, initial=True, label='Cho học sinh xem lại bài')
    quiz_time_limit_minutes = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=600,
        label='Giới hạn thời gian quiz',
        widget=forms.NumberInput(attrs={'min': 1, 'max': 600, 'placeholder': 'Theo thời lượng thi hoặc không giới hạn'}),
    )
    quiz_passing_score = forms.FloatField(
        required=False,
        min_value=0,
        label='Điểm đạt',
        widget=forms.NumberInput(attrs={'min': 0, 'step': 0.5, 'placeholder': 'VD: 50'}),
    )

    def __init__(self, *args, **kwargs):
        classroom = kwargs.pop('classroom', None)
        user = kwargs.pop('user', None)  # Extract user here
        super().__init__(*args, **kwargs)
        self.user = user  # Store user for later use in queryset filtering
        self.fields['start_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['due_date'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['exam_start_time'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['exam_end_time'].input_formats = ['%Y-%m-%dT%H:%M']
        self.fields['exam_duration_minutes'].required = False
        self.fields['exam_start_time'].required = False
        self.fields['exam_end_time'].required = False
        self.fields['exam_max_run_count'].required = False
        self.fields['exam_grace_seconds'].required = False
        self._seed_v2_modes_from_legacy_type()
        self._seed_file_requirements()
        self._seed_quiz_settings()

        # Chỉ hiển thị ClassroomSubjects của lớp này (nếu được truyền vào)
        target_classroom_id = None
        if classroom is not None:
            target_classroom_id = classroom.pk
        elif self.instance and self.instance.pk and self.instance.classroom_id:
            target_classroom_id = self.instance.classroom_id

        if target_classroom_id is not None:
            # Lấy tất cả link môn học của lớp này,
            # nhưng chỉ hiển thị những môn đã APPROVED hoặc do user hiện tại tạo.
            base_filter = Q(
                classroom_id=target_classroom_id,
                is_active=True,
                subject__is_active=True,
            )
            
            # Filter subjects: Approved OR Created by this user
            if self.user:  # Use self.user here
                base_filter &= (Q(subject__status=SubjectApprovalStatus.APPROVED) | Q(subject__created_by=self.user))
            else:
                base_filter &= Q(subject__status=SubjectApprovalStatus.APPROVED)

            # Luôn include classroom_subject hiện tại (nếu đang edit) để tránh mất giá trị
            if self.instance and self.instance.pk and self.instance.classroom_subject_id:
                base_filter = base_filter | Q(pk=self.instance.classroom_subject_id)
            qs = ClassroomSubjects.objects.filter(base_filter).select_related(
                'subject', 'semester'
            ).order_by('-semester__is_current', '-semester__start_date', 'subject__code').distinct()
            self.fields['classroom_subject'].queryset = qs

    def _seed_file_requirements(self):
        if self.is_bound:
            return
        available_extensions = [ext for ext, _label in self.FILE_EXTENSION_CHOICES]
        requirements = None
        if self.instance and self.instance.pk:
            try:
                requirements = self.instance.file_requirements
            except AssignmentFileRequirements.DoesNotExist:
                requirements = None
        if requirements:
            self.initial.setdefault('file_allowed_extensions', requirements.allowed_extensions or [])
            self.initial.setdefault('file_max_size_mb', requirements.max_file_size_mb)
            self.initial.setdefault('file_max_files', requirements.max_files)
            self.initial.setdefault('file_require_comment', requirements.require_comment)
            self.initial.setdefault('file_allow_resubmit', requirements.allow_resubmit)
            self.initial.setdefault('file_require_all_files_before_submit', requirements.require_all_files_before_submit)
            self.initial.setdefault('file_scan_required', requirements.scan_required)
        else:
            self.initial.setdefault(
                'file_allowed_extensions',
                get_list_setting(
                    'uploads.submission_allowed_extensions',
                    ['.pdf', '.docx', '.zip', '.py', '.cpp'],
                    allowed_values=available_extensions,
                ),
            )
            self.initial.setdefault(
                'file_max_size_mb',
                get_int_setting('uploads.submission_default_max_mb', 20, minimum=1, maximum=100),
            )
            self.initial.setdefault(
                'file_max_files',
                get_int_setting('uploads.submission_default_max_files', 1, minimum=1, maximum=20),
            )
            self.initial.setdefault(
                'file_scan_required',
                get_bool_setting('uploads.submission_scan_required_default', False),
            )
            self.initial.setdefault('file_allow_resubmit', True)
            self.initial.setdefault('file_require_all_files_before_submit', True)

    def _seed_quiz_settings(self):
        if self.is_bound:
            return
        settings = None
        if self.instance and self.instance.pk:
            try:
                settings = self.instance.quiz_settings
            except QuizSettings.DoesNotExist:
                settings = None
        is_exam = bool(getattr(self.instance, 'is_exam', False) or self.initial.get('is_exam'))
        if settings:
            self.initial.setdefault('quiz_random_questions', settings.question_order_mode == QuizSettings.ORDER_RANDOM)
            self.initial.setdefault('quiz_random_choices', settings.choice_order_mode == QuizSettings.ORDER_RANDOM)
            self.initial.setdefault('quiz_show_score_after_submit', settings.show_score_after_submit)
            self.initial.setdefault('quiz_show_correct_answers', settings.show_correct_answers)
            self.initial.setdefault('quiz_show_explanation', settings.show_explanation)
            self.initial.setdefault('quiz_allow_review', settings.allow_review)
            self.initial.setdefault('quiz_time_limit_minutes', settings.time_limit_minutes)
            self.initial.setdefault('quiz_passing_score', settings.passing_score)
        else:
            self.initial.setdefault(
                'quiz_random_questions',
                get_bool_setting('quiz.random_questions_default', False),
            )
            self.initial.setdefault(
                'quiz_random_choices',
                get_bool_setting('quiz.random_choices_default', False),
            )
            self.initial.setdefault(
                'quiz_show_score_after_submit',
                False if is_exam else get_bool_setting('quiz.show_score_after_submit_default', True),
            )
            self.initial.setdefault(
                'quiz_show_correct_answers',
                False if is_exam else get_bool_setting('quiz.show_correct_answers_default', False),
            )
            self.initial.setdefault('quiz_show_explanation', False)
            self.initial.setdefault(
                'quiz_allow_review',
                False if is_exam else get_bool_setting('quiz.allow_review_default', True),
            )

    def _seed_v2_modes_from_legacy_type(self):
        """Keep old `type` values readable while V2 moves to explicit modes."""
        if self.is_bound:
            return
        legacy_type = None
        if self.instance and self.instance.pk:
            legacy_type = self.instance.type
        else:
            legacy_type = self.initial.get('type')

        if not self.initial.get('submission_mode'):
            self.initial['submission_mode'] = (
                getattr(self.instance, 'submission_mode', None)
                or Assignments.SUBMISSION_CODE
            )
        if not self.initial.get('grading_mode'):
            self.initial['grading_mode'] = (
                getattr(self.instance, 'grading_mode', None)
                or self._grading_mode_from_type(legacy_type)
            )
        if not self.initial.get('type'):
            self.initial['type'] = legacy_type or self._type_from_grading_mode(
                self.initial.get('grading_mode'),
                self.initial.get('submission_mode'),
            )

    @staticmethod
    def _grading_mode_from_type(value):
        if value == 'auto_grade':
            return Assignments.GRADING_AUTO
        if value in ('manual_grade', 'project'):
            return Assignments.GRADING_MANUAL
        return Assignments.GRADING_AUTO

    @staticmethod
    def _type_from_grading_mode(grading_mode, submission_mode):
        if submission_mode == Assignments.SUBMISSION_CODE and grading_mode == Assignments.GRADING_AUTO:
            return 'auto_grade'
        if submission_mode == Assignments.SUBMISSION_CODE and grading_mode == Assignments.GRADING_MIXED:
            return 'manual_grade'
        if submission_mode == Assignments.SUBMISSION_FILE:
            return 'project'
        if submission_mode == Assignments.SUBMISSION_QUIZ:
            return 'auto_grade' if grading_mode == Assignments.GRADING_AUTO else 'manual_grade'
        return 'manual_grade'

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
        submission_mode = cleaned.get('submission_mode') or Assignments.SUBMISSION_CODE
        grading_mode = cleaned.get('grading_mode') or Assignments.GRADING_AUTO

        if submission_mode == Assignments.SUBMISSION_FILE:
            grading_mode = Assignments.GRADING_MANUAL
            cleaned['grading_mode'] = grading_mode

        if submission_mode != Assignments.SUBMISSION_CODE:
            cleaned['show_testcase_result'] = False
            cleaned['exam_allow_custom_input'] = False
            cleaned['exam_allow_sample_run'] = False
            cleaned['exam_max_run_count'] = None
            exam_max_run_count = None

        if submission_mode == Assignments.SUBMISSION_FILE:
            extensions = cleaned.get('file_allowed_extensions') or []
            max_size = cleaned.get('file_max_size_mb')
            max_files = cleaned.get('file_max_files')
            allow_resubmit = cleaned.get('file_allow_resubmit')
            if not extensions:
                self.add_error('file_allowed_extensions', 'Vui lòng chọn ít nhất một định dạng file.')
            if not max_size or max_size <= 0:
                self.add_error('file_max_size_mb', 'Dung lượng tối đa phải lớn hơn 0MB.')
            if not max_files or max_files <= 0:
                self.add_error('file_max_files', 'Số lượng file tối đa phải lớn hơn 0.')
            if not allow_resubmit:
                cleaned['max_attempts'] = 1

        if submission_mode == Assignments.SUBMISSION_QUIZ:
            if grading_mode not in (Assignments.GRADING_AUTO, Assignments.GRADING_MIXED):
                cleaned['grading_mode'] = Assignments.GRADING_AUTO
                grading_mode = Assignments.GRADING_AUTO
            if not max_attempts and not is_exam:
                cleaned['max_attempts'] = get_int_setting(
                    'quiz.default_max_attempts',
                    2,
                    minimum=1,
                    maximum=50,
                )
                max_attempts = cleaned['max_attempts']
            if is_exam:
                cleaned['max_attempts'] = 1
                cleaned['quiz_show_score_after_submit'] = False
                cleaned['quiz_show_correct_answers'] = False
                cleaned['quiz_allow_review'] = False
            passing_score = cleaned.get('quiz_passing_score')
            if passing_score is not None and max_score is not None and passing_score > max_score:
                self.add_error('quiz_passing_score', f'Điểm đạt không được vượt quá {max_score}.')

        cleaned['type'] = self._type_from_grading_mode(grading_mode, submission_mode)

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
            if submission_mode in (Assignments.SUBMISSION_FILE, Assignments.SUBMISSION_QUIZ):
                cleaned['max_attempts'] = 1
                if submission_mode == Assignments.SUBMISSION_FILE:
                    cleaned['file_allow_resubmit'] = False
            if exam_max_run_count is not None and exam_max_run_count <= 0:
                self.add_error('exam_max_run_count', 'Số lần chạy thử trong bài thi phải lớn hơn 0.')
        if not cleaned.get('late_submission_allowed'):
            cleaned['late_penalty_percent'] = 0
        if grace is None:
            cleaned['exam_grace_seconds'] = 30
        elif grace < 0:
            self.add_error('exam_grace_seconds', 'Thời gian grace không được âm.')
        return cleaned

    def save_file_requirements(self, assignment):
        if assignment.submission_mode != Assignments.SUBMISSION_FILE:
            AssignmentFileRequirements.objects.filter(assignment=assignment).delete()
            return None

        extensions = self.cleaned_data.get('file_allowed_extensions') or []
        mime_types = [
            mime
            for ext, mime in self.MIME_TYPE_BY_EXTENSION.items()
            if ext in extensions
        ]
        requirements, _ = AssignmentFileRequirements.objects.update_or_create(
            assignment=assignment,
            defaults={
                'allowed_extensions': extensions,
                'allowed_mime_types': mime_types,
                'max_file_size_mb': self.cleaned_data.get('file_max_size_mb') or 20,
                'max_files': self.cleaned_data.get('file_max_files') or 1,
                'require_comment': bool(self.cleaned_data.get('file_require_comment')),
                'allow_resubmit': bool(self.cleaned_data.get('file_allow_resubmit')),
                'require_all_files_before_submit': bool(self.cleaned_data.get('file_require_all_files_before_submit')),
                'scan_required': bool(self.cleaned_data.get('file_scan_required')),
            },
        )
        return requirements

    def save_quiz_settings(self, assignment):
        if assignment.submission_mode != Assignments.SUBMISSION_QUIZ:
            QuizSettings.objects.filter(assignment=assignment).delete()
            return None

        settings, _ = QuizSettings.objects.update_or_create(
            assignment=assignment,
            defaults={
                'question_order_mode': (
                    QuizSettings.ORDER_RANDOM
                    if self.cleaned_data.get('quiz_random_questions')
                    else QuizSettings.ORDER_FIXED
                ),
                'choice_order_mode': (
                    QuizSettings.ORDER_RANDOM
                    if self.cleaned_data.get('quiz_random_choices')
                    else QuizSettings.ORDER_FIXED
                ),
                'show_score_after_submit': bool(self.cleaned_data.get('quiz_show_score_after_submit')),
                'show_correct_answers': bool(self.cleaned_data.get('quiz_show_correct_answers')),
                'show_explanation': bool(self.cleaned_data.get('quiz_show_explanation')),
                'allow_review': bool(self.cleaned_data.get('quiz_allow_review')),
                'time_limit_minutes': self.cleaned_data.get('quiz_time_limit_minutes'),
                'passing_score': self.cleaned_data.get('quiz_passing_score'),
            },
        )
        return settings


class AssignmentFileRequirementsForm(forms.ModelForm):
    allowed_extensions = forms.MultipleChoiceField(
        choices=AssignmentForm.FILE_EXTENSION_CHOICES,
        required=True,
        widget=forms.CheckboxSelectMultiple,
        label='Định dạng file cho phép',
    )

    class Meta:
        model = AssignmentFileRequirements
        fields = [
            'allowed_extensions', 'max_file_size_mb', 'max_files',
            'require_comment', 'allow_resubmit',
            'require_all_files_before_submit', 'scan_required',
        ]
        widgets = {
            'max_file_size_mb': forms.NumberInput(attrs={'min': 1, 'max': 100}),
            'max_files': forms.NumberInput(attrs={'min': 1, 'max': 20}),
        }

    def clean_allowed_extensions(self):
        extensions = self.cleaned_data.get('allowed_extensions') or []
        allowed_values = {value for value, _label in AssignmentForm.FILE_EXTENSION_CHOICES}
        invalid = [ext for ext in extensions if ext not in allowed_values]
        if invalid:
            raise forms.ValidationError(f'Định dạng không hợp lệ: {", ".join(invalid)}')
        return extensions

    def clean_max_file_size_mb(self):
        value = self.cleaned_data.get('max_file_size_mb') or 0
        if not 1 <= value <= 100:
            raise forms.ValidationError('Dung lượng tối đa phải từ 1MB đến 100MB.')
        return value

    def clean_max_files(self):
        value = self.cleaned_data.get('max_files') or 0
        if not 1 <= value <= 20:
            raise forms.ValidationError('Số lượng file tối đa phải từ 1 đến 20.')
        return value

    def save(self, commit=True):
        instance = super().save(commit=False)
        extensions = self.cleaned_data.get('allowed_extensions') or []
        instance.allowed_mime_types = [
            mime
            for ext, mime in AssignmentForm.MIME_TYPE_BY_EXTENSION.items()
            if ext in extensions
        ]
        if commit:
            instance.save()
        return instance


class QuizQuestionForm(forms.ModelForm):
    choices_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 6,
            'placeholder': 'Mỗi dòng là một đáp án. VD:\nA. O(n)\nB. O(log n)\nC. O(n log n)',
        }),
        label='Các đáp án',
    )
    correct_answers = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'VD: A hoặc A;C hoặc 1;3'}),
        label='Đáp án đúng',
    )

    class Meta:
        model = QuizQuestions
        fields = [
            'question_text', 'question_type', 'points', 'order_index',
            'explanation', 'media_url', 'tags', 'difficulty',
        ]
        widgets = {
            'question_text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Nội dung câu hỏi...'}),
            'points': forms.NumberInput(attrs={'min': 0.5, 'step': 0.5}),
            'order_index': forms.NumberInput(attrs={'min': 0}),
            'explanation': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Giải thích đáp án sau khi công bố...'}),
            'media_url': forms.URLInput(attrs={'placeholder': 'Link hình ảnh/tài liệu minh họa nếu có'}),
            'tags': forms.TextInput(attrs={'placeholder': 'array, sorting, oop'}),
            'difficulty': forms.Select(choices=AssignmentForm.DIFFICULTY_CHOICES),
        }

    def clean_question_text(self):
        value = (self.cleaned_data.get('question_text') or '').strip()
        if not value:
            raise forms.ValidationError('Vui lòng nhập nội dung câu hỏi.')
        return value

    def clean_tags(self):
        value = self.cleaned_data.get('tags')
        if isinstance(value, str):
            return [item.strip() for item in value.split(',') if item.strip()]
        return value or []

    def clean(self):
        cleaned = super().clean()
        question_type = cleaned.get('question_type')
        choices = [
            line.strip()
            for line in (cleaned.get('choices_text') or '').splitlines()
            if line.strip()
        ]
        correct = [
            token.strip().upper()
            for token in (cleaned.get('correct_answers') or '').replace(',', ';').split(';')
            if token.strip()
        ]

        if question_type == QuizQuestions.TYPE_TRUE_FALSE:
            choices = choices or ['Đúng', 'Sai']
            correct = correct or ['A']

        if question_type in (
            QuizQuestions.TYPE_SINGLE_CHOICE,
            QuizQuestions.TYPE_MULTIPLE_CHOICE,
            QuizQuestions.TYPE_TRUE_FALSE,
        ):
            if len(choices) < 2:
                self.add_error('choices_text', 'Câu hỏi trắc nghiệm cần ít nhất 2 đáp án.')
            if not correct:
                self.add_error('correct_answers', 'Vui lòng nhập đáp án đúng.')
            if question_type in (QuizQuestions.TYPE_SINGLE_CHOICE, QuizQuestions.TYPE_TRUE_FALSE) and len(correct) != 1:
                self.add_error('correct_answers', 'Câu một đáp án/đúng sai chỉ được có một đáp án đúng.')

        cleaned['_parsed_choices'] = choices
        cleaned['_parsed_correct_answers'] = correct
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
