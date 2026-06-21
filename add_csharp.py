import os
import sys

sys.path.append('/home/locwara/DO_AN_TOT_NGHIEP_FINAL/src/Websitedayvahoclaptrinh')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
import django
django.setup()

from apps.administation.models import ProgrammingLanguages

csharp, created = ProgrammingLanguages.objects.get_or_create(
    name='csharp',
    defaults={
        'display_name': 'C#',
        'version': '6.12',
        'file_extension': '.cs',
        'syntax_highlight_mode': 'text/x-csharp',
        'is_active': True,
        'default_template': 'using System;\n\nclass Program {\n    static void Main() {\n        Console.WriteLine("Hello DevLearn");\n    }\n}'
    }
)

if created:
    print("Created C# programming language successfully.")
else:
    print("C# programming language already exists.")
