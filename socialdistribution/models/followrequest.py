# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from django.db import models
from .author import Author

class FollowRequest(models.Model):
    """
    Represents a follow request between two authors in the system.

    This model captures the state of a relationship initiated by one author (`from_author`)
    toward another (`to_author`). It supports pending requests and accepted relationships,
    and stores the timestamp when the request was created.

    Fields:
        - from_author: The author initiating the follow request.
        - to_author: The target author being followed.
        - pending: Indicates if the request is awaiting a response.
        - accepted: Indicates if the request has been approved.
        - created_at: Timestamp when the request was created.
    """
    from_author  = models.ForeignKey(Author, related_name="followings", on_delete=models.CASCADE, db_index=True)
    to_author    = models.ForeignKey(Author, related_name="followers",  on_delete=models.CASCADE, db_index=True)

    summary      = models.TextField(default="", blank=True)

    actor_data   = models.JSONField(default=dict, blank=True)
    object_data  = models.JSONField(default=dict, blank=True)

    pending      = models.BooleanField(default=True)
    accepted     = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)