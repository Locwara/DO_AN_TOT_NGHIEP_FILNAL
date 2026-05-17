from django import forms
from .models import CodeComments, FeedbackTemplates


class GradeSubmissionForm(forms.Form):
    manual_score = forms.FloatField(
        min_value=0,
        widget=forms.NumberInput(attrs={'step': '0.5', 'placeholder': 'Điểm'}),
    )
    teacher_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 5,
            'placeholder': 'Nhận xét tổng quan về bài làm của sinh viên...',
        }),
    )

    def __init__(self, *args, max_score=None, require_manual=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['manual_score'].required = require_manual
        if max_score is not None:
            self.fields['manual_score'].max_value = max_score
            self.fields['manual_score'].widget.attrs['max'] = max_score


class CodeCommentForm(forms.ModelForm):
    class Meta:
        model = CodeComments
        fields = ['line_number', 'comment_text']
        widgets = {
            'line_number': forms.HiddenInput(),
            'comment_text': forms.Textarea(attrs={
                'rows': 2,
                'placeholder': 'Nhận xét về dòng code này...',
            }),
        }


class FeedbackTemplateForm(forms.ModelForm):
    class Meta:
        model = FeedbackTemplates
        fields = ['title', 'category', 'content']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'VD: Thiếu edge case'}),
            'category': forms.TextInput(attrs={'placeholder': 'VD: logic, style, edge_case'}),
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Nội dung nhận xét mẫu...'}),
        }

    def clean_title(self):
        value = (self.cleaned_data.get('title') or '').strip()
        if not value:
            raise forms.ValidationError('Tên mẫu là bắt buộc.')
        return value

    def clean_content(self):
        value = (self.cleaned_data.get('content') or '').strip()
        if not value:
            raise forms.ValidationError('Nội dung mẫu là bắt buộc.')
        return value
