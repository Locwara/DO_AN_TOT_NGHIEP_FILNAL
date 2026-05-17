"""Management command: seed_semesters.

Usage:
    python manage.py seed_semesters
    python manage.py seed_semesters --no-assign
    python manage.py seed_semesters --assign-to HK1_2024
    python manage.py seed_semesters --reset

Tạo sẵn các kỳ học mặc định và (mặc định) auto-gán kỳ học "is_current"
cho tất cả ClassroomSubjects hiện có đang có semester=NULL.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.classrooms.models import Semesters, ClassroomSubjects


# Danh sách kỳ học mặc định sẽ được tạo.
# Thứ tự quan trọng: kỳ cuối cùng có is_current=True sẽ là kỳ hiện hành.
DEFAULT_SEMESTERS = [
    {
        'code': 'HK1_2024',
        'name': 'Học kỳ 1 - 2024-2025',
        'start_date': date(2024, 9, 1),
        'end_date': date(2025, 1, 15),
        'is_current': False,
    },
    {
        'code': 'HK2_2024',
        'name': 'Học kỳ 2 - 2024-2025',
        'start_date': date(2025, 2, 1),
        'end_date': date(2025, 6, 15),
        'is_current': True,  # Kỳ hiện hành mặc định
    },
    {
        'code': 'HK_He_2024',
        'name': 'Học kỳ hè - 2024-2025',
        'start_date': date(2025, 7, 1),
        'end_date': date(2025, 8, 31),
        'is_current': False,
    },
]


class Command(BaseCommand):
    help = (
        'Tạo các kỳ học mặc định (HK1_2024, HK2_2024, HK_He_2024) và auto-gán '
        'kỳ học hiện hành cho các ClassroomSubjects đang có semester=NULL.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-assign',
            action='store_true',
            help='Chỉ tạo Semesters, KHÔNG tự động gán vào ClassroomSubjects hiện có.',
        )
        parser.add_argument(
            '--assign-to',
            type=str,
            default=None,
            help='Mã kỳ học cụ thể để gán (VD: HK1_2024). Mặc định dùng kỳ is_current.',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Gán lại cho TẤT CẢ ClassroomSubjects (không chỉ những cái đang NULL).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Chỉ hiển thị những gì sẽ làm, không ghi DB.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        no_assign = options['no_assign']
        assign_to_code = options['assign_to']
        reset = options['reset']
        dry_run = options['dry_run']

        self.stdout.write(self.style.MIGRATE_HEADING('=== Seed Semesters ==='))
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Không có thay đổi nào được ghi DB.'))

        created_count = 0
        updated_count = 0
        existing_count = 0

        for data in DEFAULT_SEMESTERS:
            code = data['code']
            defaults = {
                'name': data['name'],
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'is_current': data['is_current'],
                'is_active': True,
            }

            existing = Semesters.objects.filter(code=code).first()
            if existing:
                # Không ghi đè is_current của kỳ đã tồn tại (tôn trọng lựa chọn manual)
                updates = {
                    k: v for k, v in defaults.items()
                    if k != 'is_current' and getattr(existing, k) != v
                }
                if updates and not dry_run:
                    for k, v in updates.items():
                        setattr(existing, k, v)
                    existing.save()
                    updated_count += 1
                    self.stdout.write(f'  ↻ Cập nhật kỳ học: {code} — {existing.name}')
                else:
                    existing_count += 1
                    self.stdout.write(f'  ✓ Đã tồn tại: {code} — {existing.name}')
            else:
                if not dry_run:
                    Semesters.objects.create(code=code, **defaults)
                created_count += 1
                flag = ' [is_current]' if data['is_current'] else ''
                self.stdout.write(self.style.SUCCESS(f'  + Tạo mới: {code} — {data["name"]}{flag}'))

        # Đảm bảo có đúng 1 is_current nếu DB chưa có kỳ nào is_current
        if not dry_run:
            has_current = Semesters.objects.filter(is_current=True).exists()
            if not has_current:
                target = Semesters.objects.filter(code='HK2_2024').first() \
                    or Semesters.objects.order_by('-start_date').first()
                if target:
                    target.is_current = True
                    target.save()
                    self.stdout.write(self.style.SUCCESS(f'  ★ Đặt kỳ hiện hành: {target.code}'))

        self.stdout.write('')
        self.stdout.write(
            f'Tổng kết Semesters: tạo mới {created_count}, cập nhật {updated_count}, đã tồn tại {existing_count}.'
        )

        # -----------------------------------------------------------------
        # Auto-gán vào ClassroomSubjects
        # -----------------------------------------------------------------
        if no_assign:
            self.stdout.write(self.style.WARNING('\n[--no-assign] Bỏ qua bước gán ClassroomSubjects.'))
            return

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Gán Semester vào ClassroomSubjects ==='))

        # Xác định kỳ học mục tiêu
        if assign_to_code:
            target_semester = Semesters.objects.filter(code=assign_to_code).first()
            if not target_semester:
                self.stdout.write(
                    self.style.ERROR(f'Không tìm thấy kỳ học với code={assign_to_code}. Dừng.')
                )
                return
        else:
            target_semester = Semesters.objects.filter(is_current=True, is_active=True).first()
            if not target_semester:
                target_semester = Semesters.objects.filter(is_active=True).order_by('-start_date').first()

        if not target_semester:
            self.stdout.write(self.style.ERROR('Không có kỳ học nào khả dụng để gán. Dừng.'))
            return

        self.stdout.write(f'Kỳ học mục tiêu: {target_semester.code} — {target_semester.name}')

        qs = ClassroomSubjects.objects.all()
        if not reset:
            qs = qs.filter(semester__isnull=True)

        total_candidates = qs.count()
        self.stdout.write(f'ClassroomSubjects {"cần gán" if not reset else "sẽ reset"}: {total_candidates}')

        if total_candidates == 0:
            self.stdout.write(self.style.SUCCESS('Không có bản ghi nào cần xử lý. Xong.'))
            return

        # Tránh vi phạm unique_together (classroom, subject, semester):
        # chỉ gán cho những ClassroomSubjects mà cặp (classroom, subject) chưa
        # tồn tại trong kỳ mục tiêu.
        assigned = 0
        skipped_duplicate = 0
        MAX_WARN_PRINT = 5
        for cs in qs.select_related('classroom', 'subject'):
            if cs.semester_id == target_semester.pk:
                continue
            duplicate_exists = ClassroomSubjects.objects.filter(
                classroom_id=cs.classroom_id,
                subject_id=cs.subject_id,
                semester_id=target_semester.pk,
            ).exclude(pk=cs.pk).exists()
            if duplicate_exists:
                skipped_duplicate += 1
                if skipped_duplicate <= MAX_WARN_PRINT:
                    self.stdout.write(self.style.WARNING(
                        f'  ! Bỏ qua (trùng): classroom={cs.classroom_id}, subject={cs.subject_id} đã có trong {target_semester.code}'
                    ))
                elif skipped_duplicate == MAX_WARN_PRINT + 1:
                    self.stdout.write(self.style.WARNING('  ! ... (rút gọn hiển thị, xem tổng kết bên dưới)'))
                continue
            if not dry_run:
                cs.semester = target_semester
                cs.save(update_fields=['semester'])
            assigned += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Đã gán: {assigned} bản ghi → {target_semester.code}. '
            f'Bỏ qua do trùng: {skipped_duplicate}.'
        ))
        if dry_run:
            self.stdout.write(self.style.WARNING('[DRY-RUN] Không có gì được ghi. Chạy lại không có --dry-run để áp dụng.'))
