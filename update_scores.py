import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.assignments.models import Assignments
from apps.classrooms.models import Classrooms

def update_scores():
    cls = Classrooms.objects.filter(invite_code="VIPCLASS").first()
    if not cls:
        print("Không tìm thấy lớp VIPCLASS")
        return
        
    assignments = Assignments.objects.filter(classroom=cls)
    updated = assignments.update(max_score=100.0)
    print(f"Đã cập nhật điểm 100 cho {updated} bài tập trong lớp {cls.name}")

if __name__ == '__main__':
    update_scores()
