import os
import sys

sys.path.append('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.assignments.models import Assignments, Testcases
from apps.submissions.models import Submissions
from apps.submissions.utils import get_assignment_final_score
from django.db.models import Count, Q

asg = Assignments.objects.get(pk=76)
classroom = asg.classroom

members = classroom.classroommembers_set.filter(status='approved')
student_final_list = []
submissions_qs = Submissions.objects.filter(assignment=asg)

print(f"Members: {members.count()}")

for member in members:
    final_score = get_assignment_final_score(asg, member.student)
    print(f"Student {member.student.username} Final Score: {final_score}")
    if final_score is not None:
        rep_sub = submissions_qs.filter(student=member.student).order_by('-total_score', '-submitted_at').first()
        if rep_sub:
            rep_sub.final_score = final_score
            student_final_list.append(rep_sub)
            print(f"Added rep_sub {rep_sub.pk} with final_score {rep_sub.final_score}")

all_scores = [sub.final_score for sub in student_final_list]
max_score = asg.max_score or 100
threshold = max_score * 0.5
print(f"Threshold default: {threshold}")

try:
    if asg.submission_mode == 'quiz' and asg.quiz_settings.passing_score is not None:
        threshold = asg.quiz_settings.passing_score
        print(f"Threshold from settings: {threshold}")
except Exception as e:
    print(f"Error getting passing_score: {e}")

pass_rate = round(sum(1 for s in all_scores if s >= threshold) / len(all_scores) * 100, 1) if all_scores else 0
print(f"Pass Rate: {pass_rate}")
