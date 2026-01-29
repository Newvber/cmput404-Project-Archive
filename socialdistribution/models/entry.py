# socialdistribution/models/entry.py
# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
import uuid
from django.db import models
from .author import Author
from django.utils import timezone
from django.conf import settings

class Entry(models.Model):
    """
    Represents a post or entry created by an author.

    This model supports various content types (text, markdown, image, base64),
    different visibility levels (public, friends, unlisted), and includes metadata
    such as creation time, last updated time, and optional description.

    Fields:
        - id: Unique UUID for each entry (used in URLs).
        - author: Foreign key linking the entry to the Author.
        - title: Title of the entry.
        - content: Main content body (text, base64, image, etc.).
        - contentType: Specifies format of the content.
        - visibility: Who can see the post (public/friends/unlisted).
        - created_at: Timestamp when the post was created.
        - updated_at: Timestamp when the post was last modified.
        - description: Optional short summary.
        - is_deleted: Soft-delete flag to hide entry from feed without removing from DB.
    """
    # Unique ID for the post (used in URL)
    id = models.CharField(
        primary_key=True,
        max_length=300,
        editable=False,
        help_text="full url: \n"
                  "  http://<node>/api/authors/{author_id}/entries/{entry_id}"
    )


    # Foreign key to the Author (the person who wrote the post)
    author = models.ForeignKey(
        Author,
        related_name='entries',
        on_delete=models.CASCADE
    )

    # Choices for content types (used for rendering/parsing content)
    CONTENT_TYPE_CHOICES = [
        ("text/markdown", "Markdown"),
        ("text/plain", "Plain text"),
        ("application/base64", "Base64"),
        ("image/png;base64", "PNG image"),
        ("image/jpeg;base64", "JPEG image"),
    ]

    VISIBILITY_CHOICES = [
        ("PUBLIC", "Public"),
        ("FRIENDS", "Friends only"),
        ("UNLISTED", "Unlisted"),
        ("DELETED", "Deleted"),
    ]

    # id = models.TextField(primary_key=True) # must be the URL
    # web = models.TextField()
    visibility = models.TextField(choices=VISIBILITY_CHOICES)
    
    title = models.CharField(max_length=120)
    content = models.TextField()
    contentType = models.CharField(
        max_length=30,
        choices=CONTENT_TYPE_CHOICES,
        default="text/plain"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    description = models.CharField(max_length=200, blank=True)

    is_deleted = models.BooleanField(default=False)
    def save(self, *args, **kwargs):
        if not self.id:
            entry_id = kwargs.pop("force_id", None) or str(uuid.uuid4())
            author_uuid = str(self.author.uuid)
            self.id = (
                f"{settings.BASE_URL}/api/authors/{author_uuid}/entries/{entry_id}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} ({self.author.display_name})"

    @property
    def uuid(self) -> str:
        """Return the UUID portion of the entry's ID."""
        return str(self.id).rstrip("/").split("/")[-1]
