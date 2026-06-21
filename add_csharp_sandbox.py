import os
import sys

sys.path.append('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.administation.models import SandboxConfigs

config, created = SandboxConfigs.objects.get_or_create(
    language='csharp',
    defaults={
        'docker_image': 'mono:6.12',
        'timeout_seconds': 5,
        'memory_limit_mb': 256,
        'cpu_limit': 1.0,
        'is_active': True
    }
)

if created:
    print("Created C# sandbox config successfully.")
else:
    config.docker_image = 'mono:6.12'
    config.is_active = True
    config.save()
    print("Updated existing C# sandbox config.")
