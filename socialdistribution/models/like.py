# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from django.db import models
from django.conf import settings
from .author import Author
from .entry import Entry
from .comment import Comment
import uuid


class Like(models.Model):
    """
    Represents a 'like' action where an Author likes a specific Entry.

    Each Like instance indicates that one author has liked one post. This model
    captures the relationship along with a timestamp of when the like occurred.

    Fields:
        - id: Unique UUID for the like.
        - entry: The Entry (post) that was liked.
        - author: The Author who liked the entry.
        - created_at: The timestamp when the like was created.

    Notes:
        - 'entry' and 'author' can be null
        - A given author should not be able to like the same entry more than once (can be enforced via 'unique_together').
    """
    class Meta:
        unique_together = ('author', 'entry')

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    id = models.CharField(primary_key=True, max_length=300, editable=False)

    entry = models.ForeignKey(
        Entry,
        related_name='likes',
        on_delete=models.CASCADE,
        null = True
    )
    
    comment = models.ForeignKey(
        Comment,
        related_name='likes',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    author = models.ForeignKey(
        Author,
        related_name='likes',
        on_delete=models.CASCADE,
        null = True
    )

    object_url = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        author_name = self.author.display_name if self.author else "Unknown"
        entry_title = self.entry.title if self.entry else "Unknown Entry"
        return f"{author_name} liked {entry_title}"

    def save(self, *args, **kwargs):
        if not self.id and self.author:
            author_uuid = str(self.author.uuid)
            host = self.author.host.rstrip('/') if self.author.host else settings.BASE_URL.rstrip('/')
            base = host if host.endswith('/api') else f"{host}/api"
            self.id = f"{base}/authors/{author_uuid}/liked/{self.uuid}"
        super().save(*args, **kwargs)
