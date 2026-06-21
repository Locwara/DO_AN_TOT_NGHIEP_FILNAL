import os
import sys

sys.path.append('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.assignments.models import Assignments
from apps.submissions.models import Submissions
from apps.submissions.utils import get_assignment_final_score

asg = Assignments.objects.get(pk=76)
print(f"Asg: {asg.title}, Max: {asg.max_score}, Mode: {asg.score_aggregation_mode}")

subs = Submissions.objects.filter(assignment=asg)
for s in subs:
    print(f"Sub {s.pk}: Student: {s.student.username}, Score: {s.total_score}, Status: {s.status}")

students = {s.student for s in subs if s.student}
for st in students:
    final = get_assignment_final_score(asg, st)
    print(f"Student {st.username} Final Score: {final}")
