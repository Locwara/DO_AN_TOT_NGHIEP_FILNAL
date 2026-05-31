from django import forms
from django.utils.text import slugify
from apps.administation.models import ProgrammingLanguages
from .models import Classrooms, Announcements, Subjects, SubjectApprovalStatus, ClassroomSubjects, Semesters

# NOTE: slugify vẫn được dùng bởi SemesterForm.clean_code bên dưới.


class ClassroomForm(forms.ModelForm):
    YEAR_CHOICES = [
        ('', '-- Chọn năm học --'),
        ('2024-2025', '2024-2025'),
        ('2025-2026', '2025-2026'),
        ('2026-2027', '2026-2027'),
    ]
    TERM_CHOICES = [
        ('', '-- Chọn học kỳ --'),
        ('Học kỳ 1', 'Học kỳ 1'),
        ('Học kỳ 2', 'Học kỳ 2'),
        ('Học kỳ 3 (Hè)', 'Học kỳ 3 (Hè)'),
    ]

    school_year = forms.ChoiceField(
        choices=YEAR_CHOICES,
        label='Năm học',
        required=True,
    )
    semester_term = forms.ChoiceField(
        choices=TERM_CHOICES,
        label='Học kỳ',
        required=True,
    )
    join_requires_approval = forms.BooleanField(
        required=False,
        label='Học sinh tham gia cần giáo viên duyệt',
        initial=True,
    )

    class Meta:
        model = Classrooms
        fields = ['name', 'description', 'school_year', 'semester_term', 'max_students']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Tên lớp học'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Mô tả lớp học...'}),
            'max_students': forms.NumberInput(attrs={'min': 1, 'max': 500}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['join_requires_approval'].initial = bool(
                (self.instance.settings or {}).get('join_requires_approval')
            )


class JoinClassroomForm(forms.Form):
    invite_code = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={'placeholder': 'Nhập mã mời lớp học'})
    )


class MemberImportForm(forms.Form):
    csv_file = forms.FileField(
        label='File CSV',
        help_text='File .csv UTF-8, tối đa 1MB. Cần có cột username hoặc email.',
        widget=forms.FileInput(attrs={
            'accept': '.csv,text/csv',
            'class': 'w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-bold file:bg-primary/10 file:text-primary hover:file:bg-primary/20',
        }),
    )

    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        if csv_file.size > 1024 * 1024:
            raise forms.ValidationError('File CSV tối đa 1MB.')
        name = (csv_file.name or '').lower()
        if not name.endswith('.csv'):
            raise forms.ValidationError('Vui lòng upload file có đuôi .csv.')
        return csv_file


class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = Announcements
        fields = ['title', 'content', 'is_pinned']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Tiêu đề thông báo'}),
            'content': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Nội dung thông báo...'}),
        }


class SubjectForm(forms.ModelForm):
    languages = forms.ModelMultipleChoiceField(
        queryset=ProgrammingLanguages.objects.filter(is_active=True).order_by('display_name'),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        help_text='Chọn ít nhất một ngôn ngữ lập trình.',
    )

    class Meta:
        model = Subjects
        # `code` được sinh tự động ở view — không cho user nhập
        fields = ['name', 'description', 'languages']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Tên môn học'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Mô tả môn học...'}),
        }

    def clean_name(self):
        from apps.classrooms.views import _normalize_subject_name
        value = (self.cleaned_data.get('name') or '').strip()
        if not value:
            raise forms.ValidationError('Tên môn học là bắt buộc.')
        target = _normalize_subject_name(value)
        qs = Subjects.objects.filter(is_active=True)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        for s in qs.only('id', 'code', 'name'):
            if _normalize_subject_name(s.name) == target:
                raise forms.ValidationError(
                    f'Tên môn học "{value}" đã tồn tại (mã: {s.code}). Vui lòng đặt tên khác.'
                )
        return value

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get('languages'):
            raise forms.ValidationError('Vui lòng chọn ít nhất một ngôn ngữ lập trình.')
        return cleaned


class ClassroomSubjectForm(forms.ModelForm):
    subject = forms.ModelChoiceField(
        queryset=Subjects.objects.filter(is_active=True, status=SubjectApprovalStatus.APPROVED).order_by('code'),
        empty_label='-- Chọn môn học --',
    )

    class Meta:
        model = ClassroomSubjects
        fields = ['subject']


class SemesterForm(forms.ModelForm):
    class Meta:
        model = Semesters
        fields = ['code', 'name', 'start_date', 'end_date', 'is_current', 'is_active']
        widgets = {
            'code': forms.TextInput(attrs={'placeholder': 'VD: HK1_2024'}),
            'name': forms.TextInput(attrs={'placeholder': 'VD: Học kỳ 1 - 2024-2025'}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_code(self):
        value = (self.cleaned_data.get('code') or '').strip()
        if not value:
            raise forms.ValidationError('Mã kỳ học là bắt buộc.')
        value = slugify(value).replace('-', '_').upper()
        return value

    def clean(self):
        cleaned = super().clean()
        start = cleaned.get('start_date')
        end = cleaned.get('end_date')
        if start and end and end < start:
            raise forms.ValidationError('Ngày kết thúc phải sau ngày bắt đầu.')
        return cleaned
