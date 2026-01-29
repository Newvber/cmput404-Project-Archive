# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

FIELD_MAX_LENGTH = 60

# Whats going to be saved in DB
# CREATE TABLE author (
#     id UUID PRIMARY KEY,
#     username VARCHAR(30) UNIQUE NOT NULL,
#     password VARCHAR(128) NOT NULL,
#     email VARCHAR(254),
#     is_active BOOLEAN NOT NULL,
#     is_staff BOOLEAN NOT NULL,
#     is_superuser BOOLEAN NOT NULL,
#     last_login TIMESTAMP,
#     date_joined TIMESTAMP NOT NULL,
#     display_name VARCHAR(30) NOT NULL,
#     github_link VARCHAR(200),
#     profile_image VARCHAR(200)
# );

class Author(AbstractUser):
    """
    Represents a user in the system. Inherits from Django's AbstractUser and adds
    custom fields such as display_name, github_link, and profile_image.

    Fields:
        id (UUID): Globally unique identifier for the user.
        username (str): Unique login name, shortened to max 60 characters.
        display_name (str): Public name shown in the UI.
        github_link (str, optional): Optional GitHub profile URL.
        profile_image (str, optional): Optional avatar image URL.

    Notes:
        - Uses UUID for the primary key to avoid collisions across distributed systems.
        - Provides custom admin display names via Meta class.
        - `username`, `password`, and other auth-related fields are inherited.
    """
    # uuid4 used to generate a random and unique identifier (UUID).
    # helps avoid ID collisions, especially when multiple systems or users are involved.
    # editable = False, so this field can't be edited through Django admin or forms.
    # Use a UUID for internal references but store the full author URL as the
    # primary key.  ``uuid`` stores just the UUID portion so other parts of the
    # system can still reference authors by UUID.
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    id = models.CharField(primary_key=True, max_length=200, editable=False)

    # 'username' and 'password' are already included via AbstractUser class.
    # overriding 'username' to make the max_length shorter
    username = models.CharField(max_length = FIELD_MAX_LENGTH, unique = True)
    # You don't need to define them manually unless you want to override their behavior.
    display_name = models.CharField(max_length = FIELD_MAX_LENGTH)

    github_link = models.URLField(blank = True)
    profile_image = models.TextField(blank = True)
    
    description = models.TextField(blank=True, null=True,max_length=50)

    # we can use static image from server i guess??
    # profile_image = models.URLField(blank = True, default = "https://static_image_from-server.png")

    # should use host to retrieve Authors from different nodes in later parts

    def _default_host():
        base = settings.BASE_URL.rstrip('/')
        return f"{base}/api/"

    host = models.URLField(default=_default_host)

    is_approved = models.BooleanField(default=False)

    class Meta:
        # customize how this model appears in the Django admin and elsewhere
        verbose_name = "Author"
        verbose_name_plural = "Authors"

    def __str__(self):
        return self.username

    @property
    def fqid(self) -> str:
        """Return the fully qualified ID for this author."""
        base = settings.BASE_URL.rstrip('/')
        return f"{base}/api/authors/{self.uuid}"

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = self.fqid
        super().save(*args, **kwargs)
    