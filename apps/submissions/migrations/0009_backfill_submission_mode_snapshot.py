from django.db import migrations


def backfill_submission_snapshots(apps, schema_editor):
    Submissions = apps.get_model('submissions', 'Submissions')

    Submissions.objects.filter(
        assignment__submission_mode='file',
    ).exclude(
        submission_mode_snapshot='file',
    ).update(submission_mode_snapshot='file')

    Submissions.objects.filter(
        assignment__submission_mode='quiz',
    ).exclude(
        submission_mode_snapshot='quiz',
    ).update(submission_mode_snapshot='quiz')

    Submissions.objects.filter(
        assignment__submission_mode='code',
    ).exclude(
        submission_mode_snapshot='code',
    ).update(submission_mode_snapshot='code')

    Submissions.objects.filter(
        submission_mode_snapshot='quiz',
        language='',
    ).update(language='quiz')


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0014_backfill_v2_modes'),
        ('submissions', '0008_gradechangelogs'),
    ]

    operations = [
        migrations.RunPython(backfill_submission_snapshots, migrations.RunPython.noop),
    ]
