# Generated manually for classroom approval fields

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classrooms', '0004_semesters_and_classroom_subject_semester'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='classrooms',
            name='approved_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='approved_classrooms', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='classrooms',
            name='reviewed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='classrooms',
            name='status',
            field=models.CharField(choices=[('pending', 'Chờ duyệt'), ('approved', 'Đã duyệt'), ('rejected', 'Từ chối')], default='pending', max_length=16),
        ),
        migrations.AlterField(
            model_name='classrooms',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]