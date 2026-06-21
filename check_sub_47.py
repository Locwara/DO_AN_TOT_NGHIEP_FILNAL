import os
import sys

sys.path.append('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.submissions.models import Submissions, SubmissionDetails

try:
    sub = Submissions.objects.get(pk=47)
    print(f"Submission 47 found. Assignment: {sub.assignment.title}")
    details = SubmissionDetails.objects.filter(submission=sub)
    print(f"Total details: {details.count()}")
    for d in details:
        print(f"TC: {d.testcase.name}, is_sample: {d.testcase.is_sample}, is_hidden: {d.testcase.is_hidden}")
except Exception as e:
    print(f"Error: {e}")
