import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classrooms', '0003_subject_catalog_and_classroom_subjects'),
    ]

    operations = [
        migrations.CreateModel(
            name='Semesters',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(help_text='VD: HK1_2024, HK2_2024', max_length=32, unique=True)),
                ('name', models.CharField(help_text='VD: Học kỳ 1 - 2024-2025', max_length=128)),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('is_current', models.BooleanField(default=False, help_text='Đánh dấu kỳ học đang diễn ra')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'semesters',
                'ordering': ('-start_date', '-code'),
            },
        ),
        migrations.AlterUniqueTogether(
            name='classroomsubjects',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='classroomsubjects',
            name='semester',
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text='Kỳ học mà lớp này dạy môn này. Có thể để trống nếu chưa phân kỳ.',
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='classroom_subject_links',
                to='classrooms.semesters',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='classroomsubjects',
            unique_together={('classroom', 'subject', 'semester')},
        ),
        migrations.AlterModelOptions(
            name='classroomsubjects',
            options={'ordering': ('classroom_id', 'subject_id', '-semester_id')},
        ),
    ]
