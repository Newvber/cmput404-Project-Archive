from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Author
from .models import FollowRequest
from .models import Entry
from .models import Comment
from .models import Like
from .models import RemoteNode
from django import forms
# localhost:8000/admin
# username: admin
# Email: admin@admin.com
# password: admin

class AuthorAdmin(UserAdmin):
    list_display = ('id', 'username', 'display_name', 'github_link','is_approved')
    fieldsets = UserAdmin.fieldsets + (
        ('Profile', {'fields': ('github_link','is_approved')}),
    )

# Register Author model with Django's default UserAdmin to enable password hashing in /admin
class FollowRequestAdmin(admin.ModelAdmin):
    list_display = ['from_author', 'to_author', 'pending', 'accepted', 'created_at']
    list_filter = ['pending', 'accepted']
    search_fields = ['from_author__username', 'to_author__username']

admin.site.register(FollowRequest, FollowRequestAdmin)

admin.site.register(Author, AuthorAdmin)

@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "visibility", "id", "created_at")
    search_fields = ("title", "content", "description")
    list_filter = ("visibility", "contentType")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Comment._meta.fields]

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'entry', 'comment', 'object_url', 'created_at')
    search_fields = ('entry__title', 'author__username')
    list_filter = ('created_at',)

class RemoteNodeAdminForm(forms.ModelForm):
    service_account_active = forms.BooleanField(required=False, label="Service account active")
    service_account_username = forms.CharField(
        required=False,
        label="Service account username",
    )
    service_account_password = forms.CharField(
        required=False,
        label="Service account password",
        widget=forms.TextInput,
    )

    class Meta:
        model = RemoteNode
        fields = [
            "base_url",
            "username",
            "password",
            "service_account_username",
            "service_account_password",
            "service_account_active",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.service_account:
            self.fields["service_account_active"].initial = (
                self.instance.service_account.is_active
            )
            self.fields["service_account_username"].initial = (
                self.instance.service_account.username
            )
            self.fields["service_account_password"].initial = (
                self.instance.service_account_password
            )

    def save(self, commit=True):
        node = super().save(commit=False)
        active = self.cleaned_data.get("service_account_active")
        username = self.cleaned_data.get("service_account_username")
        password = self.cleaned_data.get("service_account_password")

        user = node.service_account
        if user:
            updates = []
            if username and username != user.username:
                user.username = username
                updates.append("username")
            if password:
                user.set_password(password)
                updates.append("password")
                node.service_account_password = password
            if updates:
                user.save(update_fields=updates)
        elif username or password:
            from urllib.parse import urlparse
            from django.utils.crypto import get_random_string

            if not username:
                username = get_random_string(16)
            if not password:
                password = get_random_string(24)

            host = urlparse(node.base_url).hostname or node.base_url
            user = Author.objects.create_user(
                username=username,
                password=password,
                display_name=host,
            )
            node.service_account = user
            node.service_account_password = password

        if user and user.is_active != active:
            user.is_active = active
            user.save(update_fields=["is_active"])

        if commit:
            node.save()
        return node


@admin.register(RemoteNode)
class RemoteNodeAdmin(admin.ModelAdmin):
    form = RemoteNodeAdminForm
    list_display = (
        "base_url",
        "service_account_username",
        "service_account_password",
        "service_account_active",
    )
    readonly_fields = ("service_account",)

    def service_account_username(self, obj):
        if obj.service_account:
            return obj.service_account.username
        return ""
    service_account_username.short_description = "Service account"

    def service_account_password(self, obj):
        return obj.service_account_password or ""
    service_account_password.short_description = "Service password"

    def service_account_active(self, obj):
        return obj.service_account_active
    service_account_active.boolean = True

    def save_model(self, request, obj, form, change):
        """Create a service account for newly added nodes and display credentials."""
        super().save_model(request, obj, form, change)
        if not change and obj.service_account is None:
            service_username, service_password = obj.generate_service_account()
            self.message_user(
                request,
                f"Generated credentials for {obj.base_url}: "
                f"username={service_username} password={service_password}",
            )
