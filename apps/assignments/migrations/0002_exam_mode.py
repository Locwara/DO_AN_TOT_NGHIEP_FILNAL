from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignments',
            name='is_exam',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='assignments',
            name='exam_duration_minutes',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='assignments',
            name='exam_start_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='assignments',
            name='exam_end_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
