import os
import sys

sys.path.append('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.administation.models import SandboxConfigs

configs = SandboxConfigs.objects.all()
for c in configs:
    print(f"Lang: {c.language}, Image: {c.docker_image}")
