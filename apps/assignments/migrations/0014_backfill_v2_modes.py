from django.db import migrations


def backfill_assignment_modes(apps, schema_editor):
    Assignments = apps.get_model('assignments', 'Assignments')

    Assignments.objects.filter(
        type='auto_grade',
        submission_mode='code',
        grading_mode__in=['', 'manual', 'mixed'],
    ).update(grading_mode='auto')

    Assignments.objects.filter(
        type__in=['manual_grade', 'project'],
        submission_mode='code',
        grading_mode__in=['', 'auto'],
    ).update(grading_mode='manual')


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0013_assignments_grades_released_at_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_assignment_modes, migrations.RunPython.noop),
    ]
