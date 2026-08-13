import django
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from apps.assignments.forms import AssignmentForm
from apps.assignments.models import Assignments, QuizSettings

a = Assignments.objects.get(pk=122)
post_data = {
    'title': 'Test Edit',
    'submission_mode': 'quiz',
    'grading_mode': 'auto_grade',
    'is_exam': False,
    'quiz_random_questions': 'on',
    'quiz_random_choices': 'on',
    'quiz_show_score_after_submit': 'on',
    'quiz_allow_review': 'on',
    'quiz_show_correct_answers': 'on',
    'quiz_show_explanation': 'on',
    'quiz_time_limit_minutes': 30,
    # add other required fields just to pass validation
    'description': 'test',
    'start_date': '2026-08-01T10:00',
    'due_date': '2026-08-30T10:00',
}

f = AssignmentForm(post_data, instance=a)
print("Is valid:", f.is_valid())
if not f.is_valid():
    print("Errors:", f.errors)
else:
    print("Cleaned random_questions:", f.cleaned_data.get('quiz_random_questions'))
    settings = f.save_quiz_settings(a)
    print("Saved Settings:", vars(settings) if settings else None)

