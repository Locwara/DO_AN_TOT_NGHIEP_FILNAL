import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assignments', '0002_exam_mode'),
        ('classrooms', '0004_semesters_and_classroom_subject_semester'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignments',
            name='classroom_subject',
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text='Gắn bài tập vào (lớp + môn + kỳ học). Có thể để trống cho bài tập chưa phân môn.',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assignments',
                to='classrooms.classroomsubjects',
            ),
        ),
    ]
