import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q, Count
from django.core.paginator import Paginator

from core.decorators import teacher_required
from apps.assignments.models import Assignments
from apps.classrooms.views import _is_classroom_teacher, _is_classroom_member
from apps.notifications.services import notify_user
from .models import Discussions, DiscussionVotes
from .forms import DiscussionForm, ReplyForm


def _parse_discussion_title(content):
    """Extract title from content. Title is stored as first line prefixed with '# '."""
    if not content:
        return '', ''
    lines = content.split('\n', 1)
    first_line = lines[0].strip()
    if first_line.startswith('# '):
        title = first_line[2:].strip()
        body = lines[1].strip() if len(lines) > 1 else ''
        return title, body
    return first_line[:100], content


@login_required
def discussion_list_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True)
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)

    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')
    if not is_teacher and not assignment.is_published:
        messages.error(request, 'Bài tập chưa được công bố.')
        return redirect('classrooms:classroom_detail', pk=classroom.pk)

    discussions = Discussions.objects.filter(
        assignment=assignment, parent__isnull=True
    ).select_related('user').annotate(
        reply_count=Count('discussions'),
        has_accepted_answer=Count('discussions', filter=Q(discussions__is_answer=True)),
    ).order_by('-is_pinned', '-created_at')

    tab = request.GET.get('tab', 'all')
    if tab == 'unanswered':
        discussions = discussions.filter(is_answer=False).exclude(
            pk__in=Discussions.objects.filter(
                assignment=assignment, parent__isnull=False, is_answer=True
            ).values_list('parent_id', flat=True)
        )
    elif tab == 'my':
        discussions = discussions.filter(user=request.user)
    elif tab == 'popular':
        discussions = discussions.order_by('-upvotes', '-created_at')

    query = request.GET.get('q', '').strip()
    if query:
        discussions = discussions.filter(content__icontains=query)

    paginator = Paginator(discussions, 15)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    discussion_data = []
    for d in page_obj:
        title, body = _parse_discussion_title(d.content)
        discussion_data.append({
            'discussion': d,
            'title': title,
            'body_preview': body[:150] if body else '',
            'reply_count': d.reply_count,
            'has_answer': d.has_accepted_answer > 0,
        })

    context = {
        'assignment': assignment,
        'classroom': classroom,
        'discussions': discussion_data,
        'page_obj': page_obj,
        'tab': tab,
        'query': query,
        'is_teacher': is_teacher,
        'total_count': paginator.count,
    }
    return render(request, 'discussions/list.html', context)


@login_required
def discussion_detail_view(request, pk):
    discussion = get_object_or_404(Discussions, pk=pk, parent__isnull=True)
    assignment = discussion.assignment
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)

    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    title, body = _parse_discussion_title(discussion.content)

    replies = list(Discussions.objects.filter(
        parent=discussion
    ).select_related('user').order_by('-is_answer', 'created_at'))

    user_votes = {}
    if request.user.is_authenticated:
        all_discussion_ids = [discussion.pk] + [r.pk for r in replies]
        votes_qs = DiscussionVotes.objects.filter(
            discussion_id__in=all_discussion_ids, user=request.user
        )
        user_votes = {v.discussion_id: v.vote_type for v in votes_qs}

    reply_data = []
    for r in replies:
        reply_data.append({
            'reply': r,
            'user_vote': user_votes.get(r.pk),
        })

    user_vote_topic = user_votes.get(discussion.pk)

    reply_form = ReplyForm()

    if request.method == 'POST':
        reply_form = ReplyForm(request.POST)
        if reply_form.is_valid():
            reply = Discussions.objects.create(
                assignment=assignment,
                user=request.user,
                parent=discussion,
                content=reply_form.cleaned_data['content'],
            )
            if discussion.user_id and discussion.user_id != request.user.id:
                notify_user(
                    discussion.user,
                    title=f'Có trả lời mới: {title}',
                    message=f'{request.user.get_full_name() or request.user.username} vừa trả lời thảo luận của bạn.',
                    link=f'/discussions/{discussion.pk}/',
                    notification_type='discussion_replied',
                    actor=request.user,
                    metadata={'discussion_id': discussion.pk, 'reply_id': reply.pk, 'assignment_id': assignment.pk},
                )
            messages.success(request, 'Đã đăng câu trả lời!')
            return redirect('discussions:detail', pk=discussion.pk)

    context = {
        'discussion': discussion,
        'title': title,
        'body': body,
        'assignment': assignment,
        'classroom': classroom,
        'replies': reply_data,
        'reply_form': reply_form,
        'is_teacher': is_teacher,
        'user_vote_topic': user_vote_topic,
    }
    return render(request, 'discussions/detail.html', context)


@login_required
def create_discussion_view(request, assignment_pk):
    assignment = get_object_or_404(Assignments, pk=assignment_pk, is_published=True)
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)

    if not is_teacher and not is_member:
        messages.error(request, 'Bạn không phải thành viên của lớp này.')
        return redirect('classrooms:classroom_list')

    if request.method == 'POST':
        form = DiscussionForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            content_body = form.cleaned_data['content']
            full_content = f"# {title}\n\n{content_body}"

            Discussions.objects.create(
                assignment=assignment,
                user=request.user,
                content=full_content,
            )
            messages.success(request, 'Đã tạo chủ đề thảo luận mới!')
            return redirect('discussions:list', assignment_pk=assignment.pk)
    else:
        form = DiscussionForm()

    context = {
        'form': form,
        'assignment': assignment,
        'classroom': classroom,
    }
    return render(request, 'discussions/create.html', context)


@login_required
def edit_discussion_view(request, pk):
    discussion = get_object_or_404(Discussions, pk=pk)
    assignment = discussion.assignment
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)

    if discussion.user != request.user and not is_teacher:
        messages.error(request, 'Bạn không có quyền chỉnh sửa.')
        return redirect('discussions:detail', pk=discussion.pk if discussion.parent is None else discussion.parent.pk)

    is_topic = discussion.parent is None
    title, body = _parse_discussion_title(discussion.content) if is_topic else ('', discussion.content)

    if request.method == 'POST':
        if is_topic:
            form = DiscussionForm(request.POST)
            if form.is_valid():
                new_title = form.cleaned_data['title']
                new_body = form.cleaned_data['content']
                discussion.content = f"# {new_title}\n\n{new_body}"
                discussion.save(update_fields=['content', 'updated_at'])
                messages.success(request, 'Đã cập nhật thảo luận!')
                return redirect('discussions:detail', pk=discussion.pk)
        else:
            form = ReplyForm(request.POST)
            if form.is_valid():
                discussion.content = form.cleaned_data['content']
                discussion.save(update_fields=['content', 'updated_at'])
                messages.success(request, 'Đã cập nhật câu trả lời!')
                return redirect('discussions:detail', pk=discussion.parent.pk)
    else:
        if is_topic:
            form = DiscussionForm(initial={'title': title, 'content': body})
        else:
            form = ReplyForm(initial={'content': discussion.content})

    context = {
        'form': form,
        'discussion': discussion,
        'assignment': assignment,
        'classroom': classroom,
        'is_topic': is_topic,
    }
    return render(request, 'discussions/edit.html', context)


@login_required
@require_POST
def delete_discussion_view(request, pk):
    discussion = get_object_or_404(Discussions, pk=pk)
    assignment = discussion.assignment
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)

    if discussion.user != request.user and not is_teacher:
        messages.error(request, 'Bạn không có quyền xóa.')
        return redirect('discussions:list', assignment_pk=assignment.pk)

    parent = discussion.parent
    discussion.delete()
    messages.success(request, 'Đã xóa thảo luận.')

    if parent:
        return redirect('discussions:detail', pk=parent.pk)
    return redirect('discussions:list', assignment_pk=assignment.pk)


@login_required
@require_POST
def vote_discussion_view(request, pk):
    discussion = get_object_or_404(Discussions, pk=pk)
    assignment = discussion.assignment
    classroom = assignment.classroom
    is_teacher = _is_classroom_teacher(request.user, classroom)
    is_member = _is_classroom_member(request.user, classroom)

    if not is_teacher and not is_member:
        return JsonResponse({'status': 'error', 'message': 'Không có quyền.'}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)

    vote_type = data.get('vote_type', 0)
    if vote_type not in (1, -1):
        return JsonResponse({'status': 'error', 'message': 'vote_type phải là 1 hoặc -1.'}, status=400)

    existing_vote = DiscussionVotes.objects.filter(
        discussion=discussion, user=request.user
    ).first()

    if existing_vote:
        if existing_vote.vote_type == vote_type:
            discussion.upvotes -= vote_type
            discussion.save(update_fields=['upvotes'])
            existing_vote.delete()
            return JsonResponse({
                'status': 'ok',
                'action': 'removed',
                'upvotes': discussion.upvotes,
                'user_vote': None,
            })
        else:
            discussion.upvotes += 2 * vote_type
            discussion.save(update_fields=['upvotes'])
            existing_vote.vote_type = vote_type
            existing_vote.save(update_fields=['vote_type'])
            return JsonResponse({
                'status': 'ok',
                'action': 'changed',
                'upvotes': discussion.upvotes,
                'user_vote': vote_type,
            })
    else:
        DiscussionVotes.objects.create(
            discussion=discussion,
            user=request.user,
            vote_type=vote_type,
        )
        discussion.upvotes += vote_type
        discussion.save(update_fields=['upvotes'])
        return JsonResponse({
            'status': 'ok',
            'action': 'created',
            'upvotes': discussion.upvotes,
            'user_vote': vote_type,
        })


@teacher_required
@require_POST
def mark_answer_view(request, pk):
    discussion = get_object_or_404(Discussions, pk=pk)
    if discussion.parent is None:
        return JsonResponse({'status': 'error', 'message': 'Chỉ có thể đánh dấu câu trả lời.'}, status=400)

    assignment = discussion.assignment
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        return JsonResponse({'status': 'error', 'message': 'Không có quyền.'}, status=403)

    discussion.is_answer = not discussion.is_answer
    discussion.save(update_fields=['is_answer'])
    if discussion.is_answer and discussion.user_id and discussion.user_id != request.user.id:
        notify_user(
            discussion.user,
            title='Câu trả lời của bạn đã được đánh dấu đúng',
            message=f'Giáo viên đã đánh dấu câu trả lời trong bài {assignment.title}.',
            link=f'/discussions/{discussion.parent_id}/',
            notification_type='discussion_marked_answer',
            actor=request.user,
            metadata={'discussion_id': discussion.parent_id, 'reply_id': discussion.pk, 'assignment_id': assignment.pk},
        )

    return JsonResponse({
        'status': 'ok',
        'is_answer': discussion.is_answer,
    })


@teacher_required
@require_POST
def pin_discussion_view(request, pk):
    discussion = get_object_or_404(Discussions, pk=pk, parent__isnull=True)
    assignment = discussion.assignment
    classroom = assignment.classroom
    if not _is_classroom_teacher(request.user, classroom):
        return JsonResponse({'status': 'error', 'message': 'Không có quyền.'}, status=403)

    discussion.is_pinned = not discussion.is_pinned
    discussion.save(update_fields=['is_pinned'])

    return JsonResponse({
        'status': 'ok',
        'is_pinned': discussion.is_pinned,
    })
