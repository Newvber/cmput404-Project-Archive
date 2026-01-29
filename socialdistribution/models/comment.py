# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from django.db import models
from django.conf import settings
from .entry import Entry
from .author import Author
import uuid


class Comment(models.Model):
    """
    Represents a comment made by an author on an entry (post).

    Fields correspond to JSON inbox format:
      - type: always "comment"
      - author: nested Author object
      - comment: text body
      - contentType: MIME type of the comment
      - published: ISO timestamp
      - id: full URL to this comment
      - entry: full URL to the entry
      - likes: paginated likes structure
    """
    id = models.CharField(primary_key=True, max_length=300, editable=False)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    entry = models.ForeignKey(
        Entry,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        Author,
        on_delete=models.CASCADE,
        related_name='comments',
        null=True,
        blank=True
    )
    comment = models.TextField()
    content_type = models.CharField(max_length=50, default='text/plain')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.id:
            comment_uuid = str(self.uuid)
            author_uuid = str(self.author.uuid)
            base = (self.author.host or settings.BASE_URL).rstrip('/')
            if not base.endswith('/api'):
                base = f"{base}/api"
            self.id = f"{base}/authors/{author_uuid}/commented/{comment_uuid}"
        super().save(*args, **kwargs)

    def __str__(self):
        display = self.author.display_name if self.author else 'Unknown'
        return f"Comment by {display} on {self.entry.id}"

