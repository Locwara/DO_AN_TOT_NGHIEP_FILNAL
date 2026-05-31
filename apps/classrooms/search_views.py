from django.db.models import Q, F
from django.contrib.postgres.search import TrigramSimilarity
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Classrooms, ClassroomMembers, Subjects, ClassroomSubjects
from apps.assignments.models import Assignments
from apps.accounts.models import SearchHistory

@login_required
def unified_search_suggestions(request):
    """
    Gợi ý tìm kiếm tổng hợp cho lớp học, môn học, bài tập và bài thi.
    """
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')
    
    # Lấy lịch sử tìm kiếm nếu không có query
    if not query:
        history = SearchHistory.objects.filter(user=request.user).order_by('-created_at')[:8]
        return JsonResponse({
            'history': [{'query': h.query, 'created_at': h.created_at.isoformat()} for h in history],
            'results': []
        })

    # Lấy danh sách lớp người dùng đã tham gia
    joined_classroom_ids = list(ClassroomMembers.objects.filter(
        student=request.user, status='approved'
    ).values_list('classroom_id', flat=True))

    results = []

    # 1. Tìm kiếm Lớp học
    if search_type in ['all', 'classroom']:
        classroom_qs = Classrooms.objects.filter(is_active=True).annotate(
            similarity=TrigramSimilarity('name', query)
        ).filter(
            Q(similarity__gt=0.1) | Q(name__icontains=query) | Q(invite_code__iexact=query)
        ).order_by('-similarity', 'name')[:5]

        for c in classroom_qs:
            results.append({
                'type': 'classroom',
                'id': c.id,
                'title': c.name,
                'subtitle': f"Mã: {c.invite_code} · GV: {c.teacher.get_full_name() if c.teacher else 'Hệ thống'}",
                'is_joined': c.id in joined_classroom_ids,
                'url': reverse('classrooms:classroom_detail', kwargs={'pk': c.id})
            })

    # 2. Tìm kiếm Môn học
    if joined_classroom_ids and search_type in ['all', 'subject']:
        subject_ids_in_joined = ClassroomSubjects.objects.filter(
            classroom_id__in=joined_classroom_ids,
            is_active=True
        ).values_list('subject_id', flat=True).distinct()

        subject_qs = Subjects.objects.filter(id__in=subject_ids_in_joined, is_active=True).annotate(
            similarity=TrigramSimilarity('name', query)
        ).filter(
            Q(similarity__gt=0.1) | Q(name__icontains=query) | Q(code__icontains=query)
        ).order_by('-similarity', 'name')[:5]

        for s in subject_qs:
            link = ClassroomSubjects.objects.filter(
                subject=s, 
                classroom_id__in=joined_classroom_ids,
                is_active=True
            ).first()
            if link:
                results.append({
                    'type': 'subject',
                    'id': s.id,
                    'title': s.name,
                    'subtitle': f"Mã môn: {s.code}",
                    'url': reverse('classrooms:subject_detail', kwargs={'pk': link.classroom_id, 'link_pk': link.id})
                })

    # 3. Tìm kiếm Bài tập & Bài thi
    if joined_classroom_ids:
        assignment_base_qs = Assignments.objects.filter(
            classroom_id__in=joined_classroom_ids,
            is_published=True
        ).select_related('classroom').annotate(
            similarity=TrigramSimilarity('title', query)
        ).filter(
            Q(similarity__gt=0.1) | Q(title__icontains=query)
        )

        # Bài tập (không phải exam)
        if search_type in ['all', 'assignment']:
            for a in assignment_base_qs.filter(is_exam=False).order_by('-similarity', '-created_at')[:5]:
                results.append({
                    'type': 'assignment',
                    'id': a.id,
                    'title': a.title,
                    'subtitle': f"Lớp: {a.classroom.name}",
                    'url': reverse('assignments:detail', kwargs={'pk': a.id})
                })

        # Bài thi (exam)
        if search_type in ['all', 'exam']:
            for a in assignment_base_qs.filter(is_exam=True).order_by('-similarity', '-created_at')[:5]:
                results.append({
                    'type': 'exam',
                    'id': a.id,
                    'title': a.title,
                    'subtitle': f"Lớp: {a.classroom.name}",
                    'url': reverse('submissions:exam_lobby', kwargs={'assignment_pk': a.id})
                })

    return JsonResponse({'results': results})

@login_required
def search_results_view(request):
    """Trang kết quả tìm kiếm chi tiết."""
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')
    
    if not query:
        return render(request, 'classrooms/search_results.html', {'query': '', 'results': {}})

    joined_classroom_ids = list(ClassroomMembers.objects.filter(
        student=request.user, status='approved'
    ).values_list('classroom_id', flat=True))

    results = {
        'classrooms': [],
        'subjects': [],
        'assignments': [],
        'exams': []
    }

    # Search Classrooms
    if search_type in ['all', 'classroom']:
        results['classrooms'] = Classrooms.objects.filter(is_active=True).annotate(
            similarity=TrigramSimilarity('name', query)
        ).filter(
            Q(similarity__gt=0.05) | Q(name__icontains=query) | Q(invite_code__iexact=query)
        ).order_by('-similarity', 'name')[:20]

    # Search Subjects
    if joined_classroom_ids and search_type in ['all', 'subject']:
        subject_ids = ClassroomSubjects.objects.filter(
            classroom_id__in=joined_classroom_ids, is_active=True
        ).values_list('subject_id', flat=True).distinct()
        
        results['subjects'] = Subjects.objects.filter(id__in=subject_ids, is_active=True).annotate(
            similarity=TrigramSimilarity('name', query)
        ).filter(
            Q(similarity__gt=0.05) | Q(name__icontains=query) | Q(code__icontains=query)
        ).order_by('-similarity', 'name')[:20]

    # Search Assignments & Exams
    if joined_classroom_ids:
        asg_qs = Assignments.objects.filter(
            classroom_id__in=joined_classroom_ids, is_published=True
        ).annotate(similarity=TrigramSimilarity('title', query)).filter(
            Q(similarity__gt=0.05) | Q(title__icontains=query)
        )
        
        if search_type in ['all', 'assignment']:
            results['assignments'] = asg_qs.filter(is_exam=False).order_by('-similarity', '-created_at')[:20]
        if search_type in ['all', 'exam']:
            results['exams'] = asg_qs.filter(is_exam=True).order_by('-similarity', '-created_at')[:20]

    return render(request, 'classrooms/search_results.html', {
        'query': query,
        'search_type': search_type,
        'results': results,
        'joined_classroom_ids': joined_classroom_ids
    })

@login_required
@require_POST
def save_search_history(request):
    """Lưu từ khóa vào lịch sử tìm kiếm."""
    query = request.POST.get('q', '').strip()
    if query and len(query) <= 255:
        # Xóa các bản ghi cũ trùng query để đưa lên đầu
        SearchHistory.objects.filter(user=request.user, query__iexact=query).delete()
        SearchHistory.objects.create(user=request.user, query=query)
        
        # Giới hạn 15 bản ghi gần nhất
        history_to_keep = SearchHistory.objects.filter(user=request.user).values_list('id', flat=True)[:15]
        SearchHistory.objects.filter(user=request.user).exclude(id__in=history_to_keep).delete()
        
    return JsonResponse({'status': 'ok'})

@login_required
@require_POST
def clear_search_history(request):
    """Xóa toàn bộ lịch sử tìm kiếm của người dùng."""
    SearchHistory.objects.filter(user=request.user).delete()
    return JsonResponse({'status': 'ok'})
