from django import forms


class DiscussionForm(forms.Form):
    title = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'placeholder': 'Tiêu đề câu hỏi của bạn',
        }),
    )
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 6,
            'placeholder': 'Mô tả chi tiết vấn đề... (Hỗ trợ Markdown)',
        }),
    )


class ReplyForm(forms.Form):
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Viết câu trả lời...',
        }),
    )
