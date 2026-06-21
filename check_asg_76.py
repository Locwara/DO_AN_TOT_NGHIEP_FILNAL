import os
import sys

sys.path.append('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.assignments.models import Assignments, QuizSettings

try:
    asg = Assignments.objects.get(pk=76)
    print(f"Assignment 76: {asg.title}")
    print(f"Submission Mode: {asg.submission_mode}")
    print(f"Max Score: {asg.max_score}")
    
    if asg.submission_mode == 'quiz':
        qs = QuizSettings.objects.filter(assignment=asg).first()
        if qs:
            print(f"Quiz Passing Score: {qs.passing_score}")
        else:
            print("No QuizSettings found for this assignment.")
except Exception as e:
    print(f"Error: {e}")
