from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.classrooms.models import Classrooms
from apps.assignments.models import Assignments
from .models import Submissions, QuizAttempts
from django.db.models import Max

@login_required
def my_grades_view(request):
    user = request.user
    
    # 1. Get Classrooms
    classrooms = Classrooms.objects.filter(students=user, status='approved').prefetch_related(
        'classroom_subjects__subject',
        'classroom_subjects__assignments',
    )
    
    classes_data = []
    
    for cls in classrooms:
        cls_info = {
            'classroom': cls,
            'subjects': []
        }
        for cs in cls.classroom_subjects.all():
            subj_info = {
                'subject': cs.subject,
                'assignments': []
            }
            
            for assignment in cs.assignments.all():
                # Get max score
                score = None
                status = None
                submission = None
                
                if assignment.submission_mode == 'quiz':
                    attempts = QuizAttempts.objects.filter(assignment=assignment, student=user)
                    if attempts.exists():
                        best_attempt = attempts.order_by('-score').first()
                        score = best_attempt.score
                        status = 'Đã nộp' if best_attempt.status == 'submitted' else 'Đang làm'
                        submission = best_attempt
                else:
                    subs = Submissions.objects.filter(assignment=assignment, student=user)
                    if subs.exists():
                        best_sub = subs.order_by('-score').first()
                        score = best_sub.score
                        status = best_sub.get_status_display()
                        submission = best_sub
                        
                subj_info['assignments'].append({
                    'assignment': assignment,
                    'score': score,
                    'status': status,
                    'submission': submission,
                    'is_exam': assignment.is_exam
                })
            
            if subj_info['assignments']:
                cls_info['subjects'].append(subj_info)
                
        if cls_info['subjects']:
            classes_data.append(cls_info)
            
    # Recent activity
    recent_subs = list(Submissions.objects.filter(student=user).order_by('-submitted_at').select_related('assignment', 'assignment__classroom')[:10])
    recent_quizzes = list(QuizAttempts.objects.filter(student=user, status='submitted').order_by('-submitted_at').select_related('assignment', 'assignment__classroom')[:10])
    
    recent_activity = recent_subs + recent_quizzes
    recent_activity.sort(key=lambda x: x.submitted_at if x.submitted_at else x.created_at, reverse=True)
    recent_activity = recent_activity[:10]
    
    return render(request, 'submissions/my_grades.html', {
        'classes_data': classes_data,
        'recent_activity': recent_activity
    })
