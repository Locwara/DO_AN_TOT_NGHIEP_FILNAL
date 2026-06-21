import os
import sys

# Setup Django environment
sys.path.append('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django
django.setup()

from services.docker_service import execute_code

code = """a = int(input(""))
b = int(input(""))
print(str(a+b))"""

input_data = "1 1"

result = execute_code(code, "python", input_data)
print(f"Success: {result.success}")
print(f"Timed Out: {result.timed_out}")
print(f"Stdout: {repr(result.stdout)}")
print(f"Stderr: {repr(result.stderr)}")
print(f"Exit Code: {result.exit_code}")
