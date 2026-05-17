from django.db import models
from django.contrib.auth.models import User
from apps.assignments.models import Assignments

class Discussions(models.Model):
    assignment = models.ForeignKey(Assignments, models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    parent = models.ForeignKey('self', models.CASCADE, blank=True, null=True)
    content = models.TextField()
    is_pinned = models.BooleanField(default=False)
    is_answer = models.BooleanField(default=False)
    upvotes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discussions'

class DiscussionVotes(models.Model):
    discussion = models.ForeignKey(Discussions, models.CASCADE, blank=True, null=True)
    user = models.ForeignKey(User, models.CASCADE, blank=True, null=True)
    vote_type = models.IntegerField() # 1 hoặc -1
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'discussion_votes'
        unique_together = (('discussion', 'user'),)