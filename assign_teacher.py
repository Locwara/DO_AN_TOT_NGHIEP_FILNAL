import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.classrooms.models import Classrooms
from django.contrib.auth import get_user_model

User = get_user_model()

def assign_teacher():
    cls = Classrooms.objects.filter(invite_code="VIPCLASS").first()
    if not cls:
        print("Không tìm thấy lớp VIPCLASS")
        return
        
    gv = User.objects.filter(username="gv_demo").first()
    if not gv:
        print("Không tìm thấy user gv_demo")
        return
        
    cls.teacher = gv
    cls.save()
    print(f"Đã gán lớp {cls.name} cho giáo viên {gv.username}")

if __name__ == '__main__':
    assign_teacher()
