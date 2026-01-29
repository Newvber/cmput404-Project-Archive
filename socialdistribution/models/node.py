from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.crypto import get_random_string
from .author import Author
import threading



class RemoteNode(models.Model):
    """Represents a federated node that can receive broadcasts."""
    base_url = models.URLField(unique=True)
    username = models.CharField(max_length=150, blank=True, null=True)
    password = models.CharField(max_length=150, blank=True, null=True)
    service_account_password = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text="Password for the generated service account",
    )
    service_account = models.ForeignKey(
        Author,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text="this node should use it for Basic Auth",
    )

    class Meta:
        verbose_name = "Remote Node"
        verbose_name_plural = "Remote Nodes"

    def __str__(self):
        return self.base_url

    def generate_service_account(self):
        """Create or reset the local credentials for this node."""
        username = get_random_string(16)
        password = get_random_string(24)
        if self.service_account:
            user = self.service_account
            user.username = username
            user.set_password(password)
            user.save(update_fields=["username", "password"])
        else:
            from urllib.parse import urlparse
            host = urlparse(self.base_url).hostname or self.base_url
            user = Author.objects.create_user(
                username=username,
                password=password,
                display_name=host,
            )
            self.service_account = user
            self.save(update_fields=["service_account"])

        self.service_account_password = password
        self.save(update_fields=["service_account_password"])

        return username, password

    @property
    def service_account_active(self) -> bool:
        """Return whether the linked service account is active."""
        if self.service_account:
            return self.service_account.is_active
        return False

    @service_account_active.setter
    def service_account_active(self, value: bool) -> None:
        if self.service_account and self.service_account.is_active != value:
            self.service_account.is_active = value
            self.service_account.save(update_fields=["is_active"])

@receiver(post_save, sender=RemoteNode)
def on_remote_node_saved(sender, instance, **kwargs):
    from socialdistribution.utils import (
        send_all_to_new_remote,
        sync_remote_entries,
        sync_remote_comments,
        sync_remote_likes,
    )
    threading.Thread(target=send_all_to_new_remote, args=(instance,), daemon=True).start()
    threading.Thread(target=sync_remote_entries, args=(instance,), daemon=True).start()
    threading.Thread(target=sync_remote_comments, args=(instance,), daemon=True).start()
    threading.Thread(target=sync_remote_likes, args=(instance,), daemon=True).start()
    
