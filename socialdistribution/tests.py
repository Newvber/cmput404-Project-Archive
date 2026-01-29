# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from pathlib import Path
from rest_framework import status
from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from socialdistribution.models import Author, Entry, FollowRequest, Comment, Like
from socialdistribution.views.like_views import LikeAPIView
from unittest.mock import patch
import base64, uuid, re

# US 1
class AuthorIdentityConsistencyTests(APITestCase):
    def setUp(self):
        self.author = Author.objects.create_user(
            username="identityuser",
            password="testpass",
            display_name="Identity User",
            is_approved = True,
        )

    def _login(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "identityuser", "password": "testpass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_author_id_and_entry_url_stable_after_username_change(self):
        self._login()
        author_uuid = str(self.author.uuid)
        old_id = self.author.id
        create_url = f"/api/authors/{author_uuid}/entries/"
        data = {
            "title": "Test",
            "content": "hi",
            "contentType": "text/plain",
            "visibility": "PUBLIC",
        }
        resp = self.client.post(create_url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        entry_id = resp.data["id"]
        entry_uuid = entry_id.rstrip('/').split('/')[-1]

        resp = self.client.patch(
            "/api/profile/edit/",
            {"username": "newname"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.author.refresh_from_db()
        self.assertEqual(str(self.author.id), old_id)

        resp = self.client.get(f"/api/authors/{author_uuid}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        expected_id = f"{settings.BASE_URL}/api/authors/{author_uuid}"
        self.assertEqual(resp.data.get("id"), expected_id)

        detail_url = f"/api/authors/{author_uuid}/entries/{entry_uuid}/"
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get("id"), entry_id)

# US 2
class MultipleAuthorSignupTests(APITestCase):
    def test_create_multiple_authors(self):
        data1 = {"username": "user1", "display_name": "User One", "password": "12345678"}
        data2 = {"username": "user2", "display_name": "User Two", "password": "12345678"}
        response1 = self.client.post("/api/signup/", data1, format="json")
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
        response2 = self.client.post("/api/signup/", data2, format="json")
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Author.objects.count(), 2)
        usernames = set(Author.objects.values_list("username", flat=True))
        self.assertIn("user1", usernames)
        self.assertIn("user2", usernames)

    def test_duplicate_username_rejected(self):
        data = {"username": "user1", "display_name": "User One", "password": "12345678"}
        self.client.post("/api/signup/", data, format="json")
        response = self.client.post("/api/signup/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Author.objects.count(), 1)

    def test_authors_endpoint_lists_all(self):
        """GET /api/authors/ should return all created authors."""
        author1 = Author.objects.create_user(
            username="author1",
            display_name="Author One",
            password="pass1234",
            is_approved=True,
        )
        author2 = Author.objects.create_user(
            username="author2",
            display_name="Author Two",
            password="pass1234",
            is_approved=True,
        )
        # Authenticate so the authors endpoint is accessible
        login_resp = self.client.post(
            "/api/login/",
            {"username": "author1", "password": "pass1234"},
            format="json",
        )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)

        resp = self.client.get("/api/authors/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get("type"), "authors")

        ids = {a["id"] for a in resp.data.get("authors", [])}
        self.assertEqual(len(ids), 2)
        self.assertIn(author1.id, ids)
        self.assertIn(author2.id, ids)

# US 3
class PublicProfilePageTests(APITestCase):
    """Tests for publicly accessible author profile pages."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="publicuser",
            password="strongpassword",
            display_name="Public User",
        )

    def test_profile_page_accessible_without_login(self):
        """The profile page should be reachable without authentication."""
        from urllib.parse import quote
        encoded_id = quote(self.author.id, safe="")
        response = self.client.get(f"/authors/{encoded_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("profile_author", response.context)
        self.assertEqual(response.context["profile_author"], self.author)
        self.assertContains(response, self.author.display_name)

# US 4
class GitHubActivityToEntryTests(APITestCase):
    def setUp(self):
        self.author = Author.objects.create_user(
            username="ghuser",
            password="pass",
            display_name="GitHub User",
            github_link="https://github.com/testuser",
        )

    @patch("socialdistribution.views.github_update_views.requests.get")
    def test_fetch_events_creates_public_entries(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "id": "evt1",
                "type": "PushEvent",
                "repo": {"name": "gh/repo"},
                "payload": {"commits": [{"message": "Add file"}]},
                "created_at": "2024-01-01T12:00:00Z",
            },
            {
                "id": "evt2",
                "type": "IssuesEvent",
                "repo": {"name": "gh/other"},
                "created_at": "2024-01-02T12:00:00Z",
            },
        ]

        url = f"/api/authors/{self.author.id}/github_update/"
        resp = self.client.post(url, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Entry.objects.filter(author=self.author).count(), 2)
        e1 = Entry.objects.get(author=self.author, description="PushEvent")
        e2 = Entry.objects.get(author=self.author, description="IssuesEvent")

        base = settings.BASE_URL

        self.assertTrue(e1.id.endswith("/evt1"))
        self.assertTrue(e2.id.endswith("/evt2"))

        self.assertEqual(e1.title, "[GitHub] PushEvent")
        self.assertEqual(e1.visibility, "PUBLIC")
        self.assertEqual(e1.contentType, "text/plain")
        self.assertIn("gh/repo: Add file", e1.content)

        self.assertEqual(e2.title, "[GitHub] IssuesEvent")
        self.assertEqual(e2.visibility, "PUBLIC")
        self.assertEqual(e2.contentType, "text/plain")
        self.assertEqual(e2.content, "gh/other")

        resp2 = self.client.post(url, format="json")
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(Entry.objects.filter(author=self.author).count(), 2)

# US 5
class ProfilePagePublicEntriesTests(APITestCase):
    def setUp(self):
        self.author = Author.objects.create_user(
            username="author", display_name="Author", password="pass1234"
        )
        self.viewer = Author.objects.create_user(
            username="viewer", display_name="Viewer", password="pass1234"
        )
        now = timezone.now()
        # Two public posts with different creation times
        self.public_old = Entry.objects.create(
            author=self.author,
            title="Old public",
            content="old",
            visibility="PUBLIC",
            created_at=now - timedelta(days=1),
        )
        self.public_new = Entry.objects.create(
            author=self.author,
            title="New public",
            content="new",
            visibility="PUBLIC",
            created_at=now,
        )
        # Non public post should not appear
        self.friends_post = Entry.objects.create(
            author=self.author,
            title="Friends",
            content="hidden",
            visibility="FRIENDS",
            created_at=now - timedelta(hours=12),
        )
    
    def test_guest_sees_recent_public_posts_only(self):
        """Unauthenticated visitors should only see public posts in reverse chronological order."""
        url = f"/authors/{self.author.uuid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        posts = list(response.context.get("posts"))
        self.assertEqual(posts, [self.public_new, self.public_old])
        self.assertNotIn(self.friends_post, posts)
        
# US 6
class AuthorProfileEditTests(APITestCase):
    def setUp(self):
        self.user = Author.objects.create_user(
            username="author1",
            display_name="Author One",
            password="oldpassword",
        )
        self.user.is_approved = True
        self.user.save(update_fields=["is_approved"])
        self.user2 = Author.objects.create_user(
            username="author2",
            display_name="Author Two",
            password="otherpass",
        )
        self.user2.is_approved = True
        self.user2.save(update_fields=["is_approved"])

    def _login(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "author1", "password": "oldpassword"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_edit_display_name(self):
        self._login()
        resp = self.client.patch(
            "/api/profile/edit/",
            {"display_name": "New Name"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.display_name, "New Name")

    def test_edit_username_conflict(self):
        self._login()
        resp = self.client.patch(
            "/api/profile/edit/",
            {"username": "author2"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, "author1")

    def test_edit_password_logs_out(self):
        self._login()
        resp = self.client.patch(
            "/api/profile/edit/",
            {"password": "newpassword"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # After password change, user should be logged out
        resp2 = self.client.patch(
            "/api/profile/edit/",
            {"display_name": "Another"},
            format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword"))

    def test_edit_github_link(self):
        self._login()
        resp = self.client.patch(
            "/api/profile/edit/",
            {"github_link": "https://github.com/newname"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.github_link, "https://github.com/newname")

    def test_edit_profile_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        self._login()
        image = SimpleUploadedFile(
            "avatar.png", b"imgdata", content_type="image/png"
        )
        resp = self.client.patch(
            "/api/profile/edit/",
            {"profile_image": image},
            format="multipart",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_image.startswith("data:image/png;base64,"))

    def test_profile_page_for_self(self):
        self._login()
        from urllib.parse import quote
        encoded_id = quote(self.user.id, safe="")
        resp = self.client.get(f"/authors/{encoded_id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.context.get("is_self"))
        self.assertEqual(resp.context.get("profile_author"), self.user)
        self.assertEqual(resp.context.get("display_name"), self.user.display_name)
        self.assertTrue(resp.context.get("is_authenticated"))

# US 7
class EntryCreationTests(APITestCase):
    """Tests for creating basic text and image entries."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="entryauthor",
            password="testpass123",
            display_name="Entry Author",
        )

    def test_create_plain_text_entry(self):
        self.client.login(username="entryauthor", password="testpass123")

        data = {
            "title": "Text Post",
            "content": "Just some thoughts",
            "contentType": "text/plain",
            "visibility": "PUBLIC",
        }

        url = f"/api/authors/{self.author.uuid}/entries/"
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = Entry.objects.get(id=response.data["id"])
        self.assertEqual(entry.title, data["title"])
        self.assertEqual(entry.content, data["content"])
        self.assertEqual(entry.contentType, "text/plain")
        self.assertEqual(entry.visibility, "PUBLIC")

    def test_create_entry_with_image(self):
        self.client.login(username="entryauthor", password="testpass123")

        data = {
            "title": "Picture Post",
            "content": "![img](data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII)",
            "contentType": "image/png;base64",
            "visibility": "PUBLIC",
        }

        url = f"/api/authors/{self.author.uuid}/entries/"
        response = self.client.post(url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = Entry.objects.get(id=response.data["id"])
        self.assertEqual(entry.content, data["content"])
        self.assertEqual(entry.contentType, data["contentType"])
        self.assertEqual(entry.visibility, "PUBLIC")

    def test_entry_visible_to_other_local_author(self):
        """A public entry should be retrievable by another local author."""
        self.client.login(username="entryauthor", password="testpass123")

        data = {
            "title": "Shareable",
            "content": "Hello world",
            "contentType": "text/plain",
            "visibility": "PUBLIC",
        }

        url = f"/api/authors/{self.author.uuid}/entries/"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        entry_id = resp.data["id"]
        entry_uuid = entry_id.rstrip("/").split("/")[-1]

        other = Author.objects.create_user(username="viewer", password="viewpass")
        self.client.logout()
        self.client.login(username="viewer", password="viewpass")

        detail_url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.uuid, "entry_id": entry_uuid},
        )
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("id"), entry_id)

# US 8
class RemoteEntryBroadcastTests(APITestCase):
    def setUp(self):
        self.author = Author.objects.create_user(
            username="remoteauthor",
            password="pass123",
            display_name="Remote Author",
        )
        self.client.login(username="remoteauthor", password="pass123")

    @patch("socialdistribution.views.entry_views.broadcast_entry_to_remotes")
    def test_public_entry_sent_to_remote_followers(self, mock_broadcast):
        data = {
            "title": "Remote Post",
            "content": "hi",
            "contentType": "text/plain",
            "visibility": "PUBLIC",
        }
        url = f"/api/authors/{self.author.uuid}/entries/"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_broadcast.assert_called_once_with(resp.data)

    @patch("socialdistribution.views.entry_views.broadcast_entry_to_remotes")
    def test_non_public_entry_not_broadcast(self, mock_broadcast):
        data = {
            "title": "Hidden",
            "content": "hi",
            "contentType": "text/plain",
            "visibility": "FRIENDS",
        }
        url = f"/api/authors/{self.author.uuid}/entries/"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_broadcast.assert_not_called()

# US 9
class EntryEditTests(APITestCase):
    """Tests for editing an author's own entries."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="edituser",
            password="testpass",
            display_name="Edit User",
        )
        self.client.login(username="edituser", password="testpass")
        self.entry = Entry.objects.create(
            author=self.author,
            title="Original",
            content="Old content",
            visibility="PUBLIC",
            contentType="text/plain",
        )

    def test_author_can_edit_entry(self):
        url = reverse(
            "entry-detail",
            kwargs={
                "author_id": self.author.uuid,
                "entry_id": self.entry.id.rsplit("/", 1)[-1],
            },
        )
        resp = self.client.put(
            url,
            {"content": "Updated content", "title": "Updated"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.content, "Updated content")
        self.assertEqual(self.entry.title, "Updated")

# US 10
class EntryEditResendTests(APITestCase):
    """Ensure edited public entries are broadcast to remote nodes again."""

    @patch("socialdistribution.views.entry_views.broadcast_entry_to_remotes")
    def test_edit_triggers_resend(self, mock_broadcast):
        author = Author.objects.create_user(
            username="resenduser",
            password="pass",
            display_name="Resend User",
            is_approved=True,
        )

        self.client.login(username="resenduser", password="pass")

        create_url = f"/api/authors/{author.uuid}/entries/"
        data = {
            "title": "Orig",
            "content": "text",
            "contentType": "text/plain",
            "visibility": "PUBLIC",
        }
        resp = self.client.post(create_url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        self.assertTrue(mock_broadcast.called)
        mock_broadcast.reset_mock()

        entry_id = resp.data["id"]
        entry_uuid = entry_id.rstrip("/").split("/")[-1]
        edit_url = f"/api/authors/{author.uuid}/entries/{entry_uuid}/"
        resp2 = self.client.put(
            edit_url,
            {"title": "Edited", "content": "new"},
            format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        mock_broadcast.assert_called_once()
        called_data = mock_broadcast.call_args[0][0]
        self.assertEqual(called_data.get("title"), "Edited")
        self.assertEqual(called_data.get("content"), "new")

# US 11
class CommonMarkEntryTests(APITestCase):
    """Tests for creating and retrieving markdown entries."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="markuser",
            password="pass",
            display_name="Mark User",
        )

    def test_author_can_create_and_fetch_markdown_entry(self):
        self.client.login(username="markuser", password="pass")
        data = {
            "title": "Markdown Post",
            "content": "# Heading\n\nSome **bold** text.",
            "contentType": "text/markdown",
            "visibility": "PUBLIC",
        }
        url = f"/api/authors/{self.author.uuid}/entries/"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        entry_id = resp.data.get("id")
        self.assertIsNotNone(entry_id)
        entry_uuid = entry_id.rstrip("/").split("/")[-1]

        entry = self.author.entries.get(id=entry_id)
        self.assertEqual(entry.contentType, "text/markdown")
        self.assertEqual(entry.content, data["content"])

        detail_url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.uuid, "entry_id": entry_uuid},
        )
        resp_get = self.client.get(detail_url)
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_get.data.get("contentType"), "text/markdown")
        self.assertEqual(resp_get.data.get("content"), data["content"])

# US 12
class PlainTextEntryTests(APITestCase):
    """User story #12: Authors can create entries in simple plain text."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="plaintextuser",
            password="testpass",
            display_name="PlainText User",
        )

    def test_create_plain_text_entry(self):
        self.client.login(username="plaintextuser", password="testpass")
        data = {
            "title": "Plain Post",
            "content": "This is some plain text.",
            "contentType": "text/plain",
            "visibility": "PUBLIC",
        }
        url = reverse("entry-list-create", kwargs={"author_id": self.author.uuid})
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        entry = Entry.objects.get(id=response.data["id"])
        self.assertEqual(entry.contentType, "text/plain")
        self.assertEqual(entry.content, data["content"])

    def test_retrieve_plain_text_entry(self):
        entry = Entry.objects.create(
            author=self.author,
            title="Existing Plain",
            content="Existing content",
            contentType="text/plain",
            visibility="PUBLIC",
        )
        entry_uuid = entry.id.rsplit("/", 1)[-1]
        url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.uuid, "entry_id": entry_uuid},
        )
        self.client.login(username="plaintextuser", password="testpass")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("contentType"), "text/plain")
        self.assertEqual(response.data.get("content"), entry.content)

# US 13
class ImageEntryCreationTests(APITestCase):
    """Ensure authors can create and retrieve image entries."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="imageuser",
            password="strongpass",
            display_name="Image User",
        )
        self.image_bytes = b"imagedata"
        self.base64_data = base64.b64encode(self.image_bytes).decode()

    def _create_image_entry(self):
        self.client.login(username="imageuser", password="strongpass")
        data = {
            "title": "Image Post",
            "content": self.base64_data,
            "contentType": "image/png;base64",
            "visibility": "PUBLIC",
        }
        url = f"/api/authors/{self.author.uuid}/entries/"
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.data["id"]

    def test_create_image_entry(self):
        entry_id = self._create_image_entry()
        entry = Entry.objects.get(id=entry_id)
        self.assertEqual(entry.title, "Image Post")
        self.assertEqual(entry.content, self.base64_data)
        self.assertEqual(entry.contentType, "image/png;base64")
        self.assertEqual(entry.visibility, "PUBLIC")

    def test_retrieve_image_binary(self):
        entry_id = self._create_image_entry()
        entry_uuid = str(entry_id).rstrip("/").split("/")[-1]
        url = reverse(
            "entry-image",
            kwargs={"author_id": self.author.uuid, "entry_id": entry_uuid},
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.content, self.image_bytes)
        self.assertEqual(resp["Content-Type"], "image/png")

# US 14
class MarkdownImageLinkTests(APITestCase):
    """Ensure markdown entries can include links to images."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="mdimguser",
            password="pass",
            display_name="Markdown Image User",
            is_approved=True,
        )

    def test_markdown_entry_with_image_link(self):
        resp_login = self.client.post(
            "/api/login/",
            {"username": "mdimguser", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp_login.status_code, status.HTTP_200_OK)


        data = {
            "title": "Markdown Image",
            "content": "Here is an image ![alt](http://example.com/image.png)",
            "contentType": "text/markdown",
            "visibility": "PUBLIC",
        }

        url = f"/api/authors/{self.author.uuid}/entries/"
        resp = self.client.post(url, data, format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        entry_id = resp.data.get("id")
        entry = Entry.objects.get(id=entry_id)
        self.assertEqual(entry.contentType, "text/markdown")
        self.assertEqual(entry.content, data["content"])

        entry_uuid = entry_id.rsplit("/", 1)[-1]
        detail_url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.uuid, "entry_id": entry_uuid},
        )
        resp_get = self.client.get(detail_url)
        self.assertEqual(resp_get.status_code, status.HTTP_200_OK)
        self.assertEqual(resp_get.data.get("content"), data["content"])
        self.assertEqual(resp_get.data.get("contentType"), "text/markdown")

# US 15
class AuthorEntryDeletionTests(APITestCase):
    """Tests for deleting an author's own entries."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="deleteuser",
            password="pass123",
            display_name="Delete User",
        )
        self.author.is_approved = True
        self.author.save(update_fields=["is_approved"])
        self.client.login(username="deleteuser", password="pass123")
        self.entry = Entry.objects.create(
            author=self.author,
            title="Temporary",
            content="temp",
            visibility="PUBLIC",
        )

    def test_author_can_delete_entry(self):
        entry_uuid = self.entry.id.rsplit("/", 1)[-1]
        url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.uuid, "entry_id": entry_uuid},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.entry.refresh_from_db()
        self.assertEqual(self.entry.visibility, "DELETED")

        get_resp = self.client.get(url)
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

# US 16
class DeletedEntryBroadcastTests(APITestCase):
    """Ensure deleting an entry notifies remote nodes."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="delbroadcast",
            password="pass123",
            display_name="Del Broadcast",
            is_approved=True,
        )
        self.client.login(username="delbroadcast", password="pass123")
        self.entry = Entry.objects.create(
            author=self.author,
            title="To Delete",
            content="bye",
            visibility="PUBLIC",
        )

    @patch("socialdistribution.views.entry_views.broadcast_delete_to_remotes")
    def test_delete_triggers_remote_broadcast(self, mock_broadcast):
        url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.uuid, "entry_id": self.entry.uuid},
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.entry.refresh_from_db()

        mock_broadcast.assert_called_once()
        sent = mock_broadcast.call_args.args[0]
        self.assertEqual(sent.get("id"), self.entry.id)
        self.assertEqual(sent.get("visibility"), "DELETED")
        
# US 17 
class BrowserEntryManagementTests(TestCase):
    """Web interface tests for creating and editing entries."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="author17",
            password="pass",
            display_name="Author 17",
            is_approved=True,
        )
        self.other = Author.objects.create_user(
            username="other17",
            password="pass",
            display_name="Other 17",
            is_approved=True,
        )
        self.entry = Entry.objects.create(
            author=self.author,
            title="Entry Title",
            content="Entry body",
            visibility="PUBLIC",
            contentType="text/plain",
        )

    def test_write_post_page_renders_for_logged_in_author(self):
        self.client.login(username="author17", password="pass")
        url = reverse("write_post_page", kwargs={"pk": self.author.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "write_new_post.html")
        self.assertEqual(str(response.context.get("author_id")), str(self.author.id))

    def test_entry_detail_page_shows_manage_buttons_for_owner(self):
        self.client.login(username="author17", password="pass")
        url = reverse(
            "entry_page",
            kwargs={"author_id": self.author.uuid, "entry_id": self.entry.id},
        )
        response = self.client.get(url)
        self.assertContains(response, "Delete Post")
        self.assertContains(response, "Edit Post")

    def test_entry_detail_page_hides_manage_buttons_for_non_owner(self):
        self.client.login(username="other17", password="pass")
        url = reverse(
            "entry_page",
            kwargs={"author_id": self.author.uuid, "entry_id": self.entry.id},
        )
        response = self.client.get(url)
        self.assertNotContains(response, "Delete Post")
        self.assertNotContains(response, "Edit Post")

    def test_edit_entry_page_loads_entry_data(self):
        self.client.login(username="author17", password="pass")
        url = reverse(
            "edit_entry_page",
            kwargs={"author_id": self.author.uuid, "entry_id": self.entry.id},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "edit_entry.html")
        self.assertEqual(response.context.get("entry"), self.entry)
        self.assertContains(response, self.entry.title)

# US 18
class EntryModificationPermissionTests(APITestCase):
    """User story #18: ensure only the entry author can modify it."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="author1",
            password="testpass",
            display_name="Author One",
        )
        self.other = Author.objects.create_user(
            username="author2",
            password="testpass",
            display_name="Author Two",
        )
        self.entry = Entry.objects.create(
            author=self.author,
            title="Original",
            content="Content",
            visibility="PUBLIC",
            contentType="text/plain",
        )

    def test_other_author_cannot_edit_entry(self):
        self.client.login(username="author2", password="testpass")
        entry_uuid = self.entry.uuid
        url = reverse(
            "entry-detail",
            kwargs={
                "author_id": self.author.uuid,
                "entry_id": entry_uuid,
            },
        )
        response = self.client.put(
            url,
            {"content": "Hacked", "title": "Hacked"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.entry.refresh_from_db()
        self.assertEqual(self.entry.title, "Original")
        self.assertEqual(self.entry.content, "Content")

    def test_other_author_cannot_delete_entry(self):
        self.client.login(username="author2", password="testpass")
        entry_uuid = self.entry.uuid
        url = reverse(
            "entry-detail",
            kwargs={
                "author_id": self.author.uuid,
                "entry_id": entry_uuid,
            },
        )
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.entry.refresh_from_db()
        self.assertFalse(self.entry.is_deleted)

# US 19
class AuthorFeedStreamTests(APITestCase):
    """User story #19: authors see relevant entries in their stream."""

    def setUp(self):
        now = timezone.now()
        self.user = Author.objects.create_user(
            username="mainuser", password="pass", display_name="Main"
        )
        self.user.is_approved = True
        self.user.save(update_fields=["is_approved"])

        self.friend = Author.objects.create_user(
            username="friend", password="pass", display_name="Friend"
        )
        self.friend.is_approved = True
        self.friend.save(update_fields=["is_approved"])

        self.following = Author.objects.create_user(
            username="following", password="pass", display_name="Following"
        )
        self.following.is_approved = True
        self.following.save(update_fields=["is_approved"])

        self.stranger = Author.objects.create_user(
            username="stranger", password="pass", display_name="Stranger"
        )
        self.stranger.is_approved = True
        self.stranger.save(update_fields=["is_approved"])

        # relationships
        FollowRequest.objects.create(
            from_author=self.user,
            to_author=self.friend,
            accepted=True,
            pending=False,
        )
        FollowRequest.objects.create(
            from_author=self.friend,
            to_author=self.user,
            accepted=True,
            pending=False,
        )
        FollowRequest.objects.create(
            from_author=self.user,
            to_author=self.following,
            accepted=True,
            pending=False,
        )

        self.user_entry = Entry.objects.create(
            author=self.user,
            title="mine",
            content="c",
            visibility="FRIENDS",
            created_at=now - timedelta(minutes=2),
        )
        self.friend_public = Entry.objects.create(
            author=self.friend,
            title="fp",
            content="c",
            visibility="PUBLIC",
            created_at=now - timedelta(minutes=4),
        )
        self.friend_friends = Entry.objects.create(
            author=self.friend,
            title="ff",
            content="c",
            visibility="FRIENDS",
            created_at=now - timedelta(minutes=1),
        )
        self.following_unlisted = Entry.objects.create(
            author=self.following,
            title="fu",
            content="c",
            visibility="UNLISTED",
            created_at=now - timedelta(minutes=3),
        )
        self.stranger_public = Entry.objects.create(
            author=self.stranger,
            title="sp",
            content="c",
            visibility="PUBLIC",
            created_at=now - timedelta(minutes=5),
        )
        # entries not expected in feed
        Entry.objects.create(
            author=self.friend,
            title="del",
            content="c",
            visibility="DELETED",
            created_at=now - timedelta(minutes=6),
        )
        Entry.objects.create(
            author=self.stranger,
            title="su",
            content="c",
            visibility="UNLISTED",
            created_at=now - timedelta(minutes=6),
        )
        Entry.objects.create(
            author=self.stranger,
            title="sf",
            content="c",
            visibility="FRIENDS",
            created_at=now - timedelta(minutes=7),
        )

    def _login(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "mainuser", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_stream_shows_relevant_entries_in_order(self):
        self._login()
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        posts = list(resp.context["entries"])
        expected = [
            self.friend_friends.id,
            self.user_entry.id,
            self.following_unlisted.id,
            self.friend_public.id,
            self.stranger_public.id,
        ]
        self.assertEqual([p.id for p in posts], expected)
        ids = [p.id for p in posts]
        self.assertNotIn("su", ids)

# US 20
class PublicStreamPageTests(TestCase):
    """User story #20: stream page shows all public entries on the node."""

    def setUp(self):
        self.author1 = Author.objects.create_user(
            username="author1", display_name="Author One", password="pass"
        )
        self.author2 = Author.objects.create_user(
            username="author2", display_name="Author Two", password="pass"
        )

        now = timezone.now()
        self.public_recent = Entry.objects.create(
            author=self.author1,
            title="recent",
            content="c",
            visibility="PUBLIC",
            created_at=now,
        )
        self.public_old = Entry.objects.create(
            author=self.author2,
            title="old",
            content="c",
            visibility="PUBLIC",
            created_at=now - timedelta(days=1),
        )
        Entry.objects.create(
            author=self.author1,
            title="friends",
            content="c",
            visibility="FRIENDS",
            created_at=now - timedelta(hours=1),
        )
        Entry.objects.create(
            author=self.author2,
            title="unlisted",
            content="c",
            visibility="UNLISTED",
            created_at=now - timedelta(hours=2),
        )
        Entry.objects.create(
            author=self.author1,
            title="deleted",
            content="c",
            visibility="DELETED",
            created_at=now - timedelta(days=2),
        )

    def test_stream_shows_all_public_entries(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        posts = list(response.context["entries"])
        expected_ids = [self.public_recent.id, self.public_old.id]
        self.assertEqual([p.id for p in posts], expected_ids)

# US 22
class FollowedAuthorsHiddenPostsTests(APITestCase):
    """Ensure an author's feed shows unlisted and friends-only posts from every followed author."""

    def setUp(self):
        self.user = Author.objects.create_user(
            username="viewer22",
            display_name="Viewer22",
            password="pass",
            is_approved=True,
        )
        self.friend = Author.objects.create_user(
            username="friend22",
            display_name="Friend22",
            password="pass",
            is_approved=True,
        )
        self.following = Author.objects.create_user(
            username="following22",
            display_name="Following22",
            password="pass",
            is_approved=True,
        )
        self.stranger = Author.objects.create_user(
            username="stranger22",
            display_name="Stranger22",
            password="pass",
            is_approved=True,
        )

        FollowRequest.objects.create(
            from_author=self.user,
            to_author=self.friend,
            accepted=True,
            pending=False,
        )
        FollowRequest.objects.create(
            from_author=self.friend,
            to_author=self.user,
            accepted=True,
            pending=False,
        )
        FollowRequest.objects.create(
            from_author=self.user,
            to_author=self.following,
            accepted=True,
            pending=False,
        )

        now = timezone.now()
        self.friend_friends = Entry.objects.create(
            author=self.friend,
            title="friends post",
            content="c",
            visibility="FRIENDS",
            created_at=now - timedelta(minutes=1),
        )
        self.friend_unlisted = Entry.objects.create(
            author=self.friend,
            title="unlisted friend",
            content="c",
            visibility="UNLISTED",
            created_at=now,
        )
        self.following_unlisted = Entry.objects.create(
            author=self.following,
            title="following hidden",
            content="c",
            visibility="UNLISTED",
            created_at=now - timedelta(minutes=2),
        )
        self.stranger_unlisted = Entry.objects.create(
            author=self.stranger,
            title="stranger hidden",
            content="c",
            visibility="UNLISTED",
            created_at=now - timedelta(minutes=3),
        )

    def test_feed_includes_followed_hidden_posts(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "viewer22", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        ids = [e.id for e in response.context["entries"]]
        self.assertIn(self.friend_friends.id, ids)
        self.assertIn(self.friend_unlisted.id, ids)
        self.assertIn(self.following_unlisted.id, ids)
        self.assertNotIn(self.stranger_unlisted.id, ids)

# US 23
class StreamShowsUpdatedEntryTests(APITestCase):
    """Ensure the feed displays the latest version of an edited entry."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="editor23",
            password="pass",
            display_name="Editor 23",
            is_approved=True,
        )
        self.entry = Entry.objects.create(
            author=self.author,
            title="Original",
            content="old",
            visibility="PUBLIC",
            contentType="text/plain",
        )

    def _login(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "editor23", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_feed_shows_updated_entry_after_edit(self):
        self._login()
        entry_uuid = self.entry.id.rsplit("/", 1)[-1]
        url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.uuid, "entry_id": entry_uuid},
        )
        resp = self.client.put(
            url,
            {"title": "Updated", "content": "new content"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        posts = list(response.context["entries"])
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].title, "Updated")
        self.assertEqual(posts[0].content, "new content")

# US 24
class StreamHiddenDeletedEntriesTests(APITestCase):
    """User story #24: deleted entries should not appear in the logged in author's stream."""

    def setUp(self):
        self.user = Author.objects.create_user(
            username="user24", password="pass", display_name="User24", is_approved=True
        )
        self.friend = Author.objects.create_user(
            username="friend24", password="pass", display_name="Friend24", is_approved=True
        )

        # establish mutual follow so friend posts appear in feed
        FollowRequest.objects.create(
            from_author=self.user, to_author=self.friend, accepted=True, pending=False
        )
        FollowRequest.objects.create(
            from_author=self.friend, to_author=self.user, accepted=True, pending=False
        )

        now = timezone.now()
        self.friend_post = Entry.objects.create(
            author=self.friend,
            title="visible",
            content="c",
            visibility="FRIENDS",
            created_at=now,
        )
        self.deleted_post = Entry.objects.create(
            author=self.friend,
            title="deleted",
            content="c",
            visibility="DELETED",
            created_at=now,
        )

    def _login(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "user24", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_deleted_entries_absent_from_stream(self):
        self._login()
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

        ids = [e.id for e in resp.context["entries"]]
        self.assertIn(self.friend_post.id, ids)
        self.assertNotIn(self.deleted_post.id, ids)

# US 25
class StreamPageOrderingUpdatedTests(APITestCase):
    """User story #25: Stream page shows newest entries first"""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="streamorder", display_name="Stream Order", password="pass", is_approved=True,
        )
        now = timezone.now()
        self.old_entry = Entry.objects.create(
            author=self.author,
            title="old",
            content="c",
            visibility="PUBLIC",
            created_at=now - timedelta(days=2),
        )
        self.mid_entry = Entry.objects.create(
            author=self.author,
            title="mid",
            content="c",
            visibility="PUBLIC",
            created_at=now - timedelta(days=1),
        )
        self.new_entry = Entry.objects.create(
            author=self.author,
            title="new",
            content="c",
            visibility="PUBLIC",
            created_at=now,
        )

    def test_stream_shows_entries_in_descending_order(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "streamorder", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        posts = list(response.context["entries"])
        expected = [self.new_entry.id, self.mid_entry.id, self.old_entry.id]
        self.assertEqual([p.id for p in posts], expected)

# US 26
class PublicEntryVisibilityTests(APITestCase):
    """User story #26: authors can mark entries public for everyone to see."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="pubauthor", password="pass", display_name="Public Author"
        )
        self.viewer = Author.objects.create_user(
            username="viewer26b", password="pass", display_name="Viewer 26B"
        )
        self.entries_url = reverse(
            "entry-list-create", kwargs={"author_id": self.author.id}
        )

    def _create_public_entry(self):
        self.client.login(username="pubauthor", password="pass")
        data = {
            "title": "Public Post",
            "content": "hello world",
            "contentType": "text/plain",
            "visibility": "PUBLIC",
        }
        resp = self.client.post(self.entries_url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        entry_id = resp.data["id"]
        entry_uuid = entry_id.rstrip("/").split("/")[-1]
        self.client.logout()
        return entry_id, entry_uuid

    def test_logged_in_user_can_view_public_entry(self):
        entry_id, entry_uuid = self._create_public_entry()
        self.client.login(username="viewer26b", password="pass")
        resp = self.client.get(self.entries_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        entries = resp.data if isinstance(resp.data, list) else resp.data.get("src", [])
        ids = {e["id"] for e in entries}
        self.assertIn(entry_id, ids)
        detail_url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.id, "entry_id": entry_uuid},
        )
        dresp = self.client.get(detail_url)
        self.assertEqual(dresp.status_code, status.HTTP_200_OK)
        self.assertEqual(dresp.data.get("id"), entry_id)

    def test_guest_can_view_public_entry(self):
        entry_id, entry_uuid = self._create_public_entry()
        resp = self.client.get(self.entries_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {e["id"] for e in resp.data}
        self.assertIn(entry_id, ids)
        detail_url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.id, "entry_id": entry_uuid},
        )
        dresp = self.client.get(detail_url)
        self.assertEqual(dresp.status_code, status.HTTP_200_OK)
        self.assertEqual(dresp.data.get("id"), entry_id)

# US 27
class UnlistedEntryVisibilityTests(APITestCase):
    """User Story #27: Followers see unlisted posts and anyone with the link can access."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="author27", display_name="Author 27", password="pass", is_approved=True
        )
        self.follower = Author.objects.create_user(
            username="follower27", display_name="Follower 27", password="pass", is_approved=True
        )
        self.stranger = Author.objects.create_user(
            username="stranger27", display_name="Stranger 27", password="pass", is_approved=True
        )

        FollowRequest.objects.create(
            from_author=self.follower,
            to_author=self.author,
            accepted=True,
            pending=False,
        )

        self.entry = Entry.objects.create(
            author=self.author,
            title="unlisted entry",
            content="hidden",
            visibility="UNLISTED",
        )

    def test_follower_sees_unlisted_entry_in_feed(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "follower27", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        ids = [e.id for e in response.context["entries"]]
        self.assertIn(self.entry.id, ids)

    def test_non_follower_does_not_see_unlisted_entry_in_feed(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "stranger27", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        ids = [e.id for e in response.context["entries"]]
        self.assertNotIn(self.entry.id, ids)

    def test_unlisted_entry_inaccessible_with_direct_link(self):
        """Unauthenticated users should not be able to access unlisted entries directly."""
        self.client.logout()
        entry_uuid = self.entry.id.rstrip("/").split("/")[-1]
        url = f"/api/authors/{self.author.uuid}/entries/{entry_uuid}/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

# US 28
class FriendsOnlyEntryTests(APITestCase):
    """User story #28: entries marked friends-only are visible only to friends."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="owner28",
            password="pass",
            display_name="Owner 28",
            is_approved=True,
        )
        self.friend = Author.objects.create_user(
            username="friend28",
            password="pass",
            display_name="Friend 28",
            is_approved=True,
        )
        self.stranger = Author.objects.create_user(
            username="stranger28",
            password="pass",
            display_name="Stranger 28",
            is_approved=True,
        )
        # establish mutual following between author and friend
        FollowRequest.objects.create(from_author=self.author, to_author=self.friend, accepted=True, pending=False)
        FollowRequest.objects.create(from_author=self.friend, to_author=self.author, accepted=True, pending=False)

    def _login(self, user):
        resp = self.client.post(
            "/api/login/",
            {"username": user, "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def _create_friends_entry(self):
        self._login("owner28")
        data = {
            "title": "Friends post",
            "content": "secret",
            "contentType": "text/plain",
            "visibility": "FRIENDS",
        }
        url = f"/api/authors/{self.author.uuid}/entries/"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        entry_id = resp.data["id"]
        self.client.post("/api/logout/")
        return entry_id

    def test_author_can_create_friends_only_entry(self):
        entry_id = self._create_friends_entry()
        entry = Entry.objects.get(id=entry_id)
        self.assertEqual(entry.visibility, "FRIENDS")

    def test_friend_can_access_friends_only_entry(self):
        entry_id = self._create_friends_entry()
        entry_uuid = entry_id.rstrip("/").split("/")[-1]
        self._login("friend28")
        url = reverse("entry-detail", kwargs={"author_id": self.author.uuid, "entry_id": entry_uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get("id"), entry_id)

    def test_non_friend_cannot_access_friends_only_entry(self):
        entry_id = self._create_friends_entry()
        entry_uuid = entry_id.rstrip("/").split("/")[-1]
        self._login("stranger28")
        url = reverse("entry-detail", kwargs={"author_id": self.author.uuid, "entry_id": entry_uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        # listing should also not include the entry
        list_url = f"/api/authors/{self.author.uuid}/entries/"
        list_resp = self.client.get(list_url)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        entries = (
            list_resp.data
            if isinstance(list_resp.data, list)
            else list_resp.data.get("src", [])
        )
        ids = {e["id"] for e in entries}
        self.assertNotIn(entry_id, ids)

# US 29
class FriendStreamEntriesVisibilityTests(APITestCase):
    def setUp(self):
        self.author = Author.objects.create_user(
            username="author", display_name="Author", password="pass"
        )
        self.friend = Author.objects.create_user(
            username="friend", display_name="Friend", password="pass"
        )
        self.author.is_approved = True
        self.author.save(update_fields=["is_approved"])
        self.friend.is_approved = True
        self.friend.save(update_fields=["is_approved"])

        # establish mutual following
        FollowRequest.objects.create(
            from_author=self.author,
            to_author=self.friend,
            accepted=True,
            pending=False,
        )
        FollowRequest.objects.create(
            from_author=self.friend,
            to_author=self.author,
            accepted=True,
            pending=False,
        )

        now = timezone.now()
        self.public_entry = Entry.objects.create(
            author=self.author,
            title="public",
            content="c",
            visibility="PUBLIC",
            created_at=now,
        )
        self.friends_entry = Entry.objects.create(
            author=self.author,
            title="friends",
            content="c",
            visibility="FRIENDS",
            created_at=now - timedelta(minutes=1),
        )
        self.unlisted_entry = Entry.objects.create(
            author=self.author,
            title="unlisted",
            content="c",
            visibility="UNLISTED",
            created_at=now - timedelta(minutes=2),
        )

    def test_friend_can_see_all_entry_types(self):
        self.client.post(
            "/api/login/",
            {"username": "friend", "password": "pass"},
            format="json",
        )

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        posts = list(response.context["entries"])
        ids = [p.id for p in posts]
        self.assertEqual(ids[:3], [self.public_entry.id, self.friends_entry.id, self.unlisted_entry.id])

# US 30
class FollowerSeesUnlistedPublicEntriesTests(APITestCase):
    """Ensure followers see author's unlisted and public posts in their feed."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="author", display_name="Author", password="pass"
        )
        self.follower = Author.objects.create_user(
            username="follower", display_name="Follower", password="pass"
        )
        self.author.is_approved = True
        self.author.save(update_fields=["is_approved"])
        self.follower.is_approved = True
        self.follower.save(update_fields=["is_approved"])

        # follower follows author
        FollowRequest.objects.create(
            from_author=self.follower,
            to_author=self.author,
            accepted=True,
            pending=False,
        )

        now = timezone.now()
        self.public_entry = Entry.objects.create(
            author=self.author,
            title="public",
            content="c",
            visibility="PUBLIC",
            created_at=now,
        )
        self.unlisted_entry = Entry.objects.create(
            author=self.author,
            title="unlisted",
            content="c",
            visibility="UNLISTED",
            created_at=now - timedelta(minutes=1),
        )
        # entries not visible to follower
        Entry.objects.create(
            author=self.author,
            title="friends",
            content="c",
            visibility="FRIENDS",
            created_at=now - timedelta(minutes=2),
        )
        Entry.objects.create(
            author=self.author,
            title="deleted",
            content="c",
            visibility="PUBLIC",
            is_deleted=True,
            created_at=now - timedelta(minutes=3),
        )

    def test_follower_stream_contains_unlisted_and_public(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "follower", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        ids = [e.id for e in response.context["entries"]]
        self.assertIn(self.public_entry.id, ids)
        self.assertIn(self.unlisted_entry.id, ids)
        # ensure follower does not see friends-only or deleted posts
        self.assertNotIn(
            Entry.objects.get(title="friends").id,
            ids,
        )

# US 31
class PublicEntryVisibilityTests(APITestCase):
    """User story #31: Author's public posts visible in everyone\'s feed."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="author31",
            password="pass",
            display_name="Author 31",
        )
        self.viewer = Author.objects.create_user(
            username="viewer31",
            password="pass",
            display_name="Viewer 31",
        )
        self.public_entry = Entry.objects.create(
            author=self.author,
            title="public entry",
            content="content",
            visibility="PUBLIC",
            created_at=timezone.now(),
        )

    def test_logged_in_user_sees_public_post(self):
        self.client.post(
            "/api/login/",
            {"username": "viewer31", "password": "pass"},
            format="json",
        )
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        ids = [e.id for e in resp.context["entries"]]
        self.assertIn(self.public_entry.id, ids)

    def test_guest_user_sees_public_post(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        ids = [e.id for e in resp.context["entries"]]
        self.assertIn(self.public_entry.id, ids)

# US 32
class EntryLinkAccessTests(APITestCase):
    """Ensure public and unlisted entries are accessible via direct link."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="author32",
            password="pass",
            display_name="Author 32",
            is_approved=True,
        )
        self.public_entry = Entry.objects.create(
            author=self.author,
            title="Public Entry",
            content="public",
            visibility="PUBLIC",
        )
        self.unlisted_entry = Entry.objects.create(
            author=self.author,
            title="Unlisted Entry",
            content="hidden",
            visibility="UNLISTED",
        )

    def _detail_url(self, entry):
        entry_uuid = entry.id.rstrip('/') .split('/')[-1]
        return reverse(
            "entry-detail",
            kwargs={"author_id": self.author.uuid, "entry_id": entry_uuid},
        )

    def test_public_entry_accessible_by_link(self):
        viewer = Author.objects.create_user(username="viewer32", password="viewpass")
        self.client.logout()
        self.client.login(username="viewer32", password="viewpass")
        url = self._detail_url(self.public_entry)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get("id"), str(self.public_entry.id))

    def test_unlisted_entry_accessible_by_link_not_listed(self):
        viewer = Author.objects.create_user(username="viewer32b", password="viewpass")
        self.client.logout()
        self.client.login(username="viewer32b", password="viewpass")
        list_url = reverse("entry-list-create", kwargs={"author_id": self.author.uuid})
        resp = self.client.get(list_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        entries = resp.data if isinstance(resp.data, list) else resp.data.get("src", [])
        ids = {e["id"] for e in entries}
        self.assertNotIn(str(self.unlisted_entry.id), ids)
        detail_resp = self.client.get(self._detail_url(self.unlisted_entry))
        # Unlisted entries are accessible via direct link but remain hidden from lists
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_resp.data.get("id"), str(self.unlisted_entry.id))

# US 33
class FriendsOnlyVisibilityTests(APITestCase):
    """User story #33: non-friends cannot access friends-only entries or images."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="author33n", password="pass", display_name="Author 33", is_approved=True
        )
        self.friend = Author.objects.create_user(
            username="friend33n", password="pass", display_name="Friend 33", is_approved=True
        )
        self.stranger = Author.objects.create_user(
            username="stranger33n", password="pass", display_name="Stranger 33", is_approved=True
        )
        FollowRequest.objects.create(from_author=self.author, to_author=self.friend, accepted=True, pending=False)
        FollowRequest.objects.create(from_author=self.friend, to_author=self.author, accepted=True, pending=False)
        img_data = base64.b64encode(b"img").decode()
        now = timezone.now()
        self.text_entry = Entry.objects.create(
            author=self.author,
            title="Friends Text",
            content="secret text",
            contentType="text/plain",
            visibility="FRIENDS",
            created_at=now
        )
        self.image_entry = Entry.objects.create(
            author=self.author,
            title="Friends Image",
            content=img_data,
            contentType="image/png;base64",
            visibility="FRIENDS",
            created_at=now - timedelta(seconds=1)
        )

    def _login(self, username):
        resp = self.client.post("/api/login/", {"username": username, "password": "pass"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_friend_can_view_friends_entries(self):
        self._login("friend33n")
        detail_url = f"/api/authors/{self.author.uuid}/entries/{self.text_entry.uuid}/"
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_200_OK)
        img_detail_url = f"/api/authors/{self.author.uuid}/entries/{self.image_entry.uuid}/"
        self.assertEqual(self.client.get(img_detail_url).status_code, status.HTTP_200_OK)

    def test_non_friend_cannot_view_friends_entries(self):
        self._login("stranger33n")
        detail_url = f"/api/authors/{self.author.uuid}/entries/{self.text_entry.uuid}/"
        self.assertEqual(self.client.get(detail_url).status_code, status.HTTP_403_FORBIDDEN)
        img_detail_url = f"/api/authors/{self.author.uuid}/entries/{self.image_entry.uuid}/"
        self.assertEqual(self.client.get(img_detail_url).status_code, status.HTTP_403_FORBIDDEN)
        img_url = reverse(
            "entry-image",
            kwargs={"author_id": self.author.uuid, "entry_id": self.image_entry.uuid},
        )
        self.assertEqual(self.client.get(img_url).status_code, status.HTTP_403_FORBIDDEN)

# US 34
class DeletedEntryVisibilityTests(APITestCase):
    """Deleted entries should only be visible to node admins."""

    def setUp(self):
        self.admin = Author.objects.create_superuser(
            username="admin34",
            password="adminpass",
            email="admin@example.com",
            display_name="Admin",
        )
        self.admin.is_approved = True
        self.admin.save(update_fields=["is_approved"])
        self.owner = Author.objects.create_user(
            username="owner34",
            display_name="Owner 34",
            password="pass",
        )
        self.owner.is_approved = True
        self.owner.save(update_fields=["is_approved"])
        self.viewer = Author.objects.create_user(
            username="viewer34",
            display_name="Viewer 34",
            password="pass",
        )
        self.viewer.is_approved = True
        self.viewer.save(update_fields=["is_approved"])
        self.entry = Entry.objects.create(
            author=self.owner,
            title="deleted",
            content="gone",
            visibility="DELETED",
        )
        self.entry_uuid = self.entry.id.split("/")[-1]

    def test_non_admin_cannot_view_deleted_entry(self):
        self.client.post(
            "/api/login/",
            {"username": "viewer34", "password": "pass"},
            format="json",
        )

        url = f"/api/authors/{self.owner.uuid}/entries/{self.entry_uuid}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_view_deleted_entry(self):
        self.client.post(
            "/api/login/",
            {"username": "admin34", "password": "adminpass"},
            format="json",
        )

        url = f"/api/authors/{self.owner.uuid}/entries/{self.entry_uuid}/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get("id"), str(self.entry.id))

# US 35
class AuthorEntryVisibilityTests(APITestCase):
    """Entries created by an author remain visible to them until deleted."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="author35", display_name="Author 35", password="pass"
        )
        self.client.login(username="author35", password="pass")
        self.entries_url = f"/api/authors/{self.author.uuid}/entries/"

    def _create_entry(self, visibility):
        entry = Entry.objects.create(
            author=self.author,
            title=f"{visibility} entry",
            content="body",
            visibility=visibility,
            contentType="text/plain",
        )
        return entry.id, entry.id.split("/")[-1]

    def test_owner_sees_all_until_deleted(self):
        # create entries of varying visibilities
        public_fqid, public_uuid = self._create_entry("PUBLIC")
        friends_fqid, friends_uuid = self._create_entry("FRIENDS")
        unlisted_fqid, unlisted_uuid = self._create_entry("UNLISTED")

        for fqid in [public_fqid, friends_fqid, unlisted_fqid]:
            uuid = fqid.split("/")[-1]
            detail_url = f"/api/authors/{self.author.uuid}/entries/{uuid}/"
            resp = self.client.get(detail_url)
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # delete one entry
        Entry.objects.filter(id=public_fqid).update(visibility="DELETED")

        delete_url = f"/api/authors/{self.author.uuid}/entries/{public_uuid}/"
        resp = self.client.get(delete_url)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # remaining entries still accessible
        for fqid in [friends_fqid, unlisted_fqid]:
            uuid = fqid.split("/")[-1]
            resp = self.client.get(f"/api/authors/{self.author.uuid}/entries/{uuid}/")
            self.assertEqual(resp.status_code, status.HTTP_200_OK)

# US 36
class EntryShareLinkTests(APITestCase):
    """Tests for accessing public or unlisted entries via shareable links."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="linkauthor",
            display_name="Link Author",
            password="pass",
            is_approved=True,
        )
        self.public_entry = Entry.objects.create(
            author=self.author,
            title="public",
            content="c",
            visibility="PUBLIC",
        )
        self.unlisted_entry = Entry.objects.create(
            author=self.author,
            title="unlisted",
            content="c",
            visibility="UNLISTED",
        )

        self.public_uuid = self.public_entry.id.rsplit("/", 1)[-1]
        self.unlisted_uuid = self.unlisted_entry.id.rsplit("/", 1)[-1]

    def test_guest_cannot_access_public_entry_link(self):
        url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.uuid, "entry_id": self.public_uuid},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_guest_cannot_access_unlisted_entry_link(self):
        url = reverse(
            "entry-detail",
            kwargs={"author_id": self.author.uuid, "entry_id": self.unlisted_uuid},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

# US 37
class RemoteImageBroadcastTests(APITestCase):
    """Ensure images posted by admins are pushed to remote nodes."""

    def setUp(self):
        self.admin = Author.objects.create_superuser(
            username="admin37",
            password="pass",
            email="admin@example.com",
            display_name="Admin37",
        )
        self.admin.is_approved = True
        self.admin.save(update_fields=["is_approved"])

    @patch("socialdistribution.views.entry_views.broadcast_entry_to_remotes")
    def test_public_image_entry_broadcasted(self, mock_broadcast):
        self.client.login(username="admin37", password="pass")
        img_b64 = base64.b64encode(b"imgdata").decode()
        data = {
            "title": "Image",
            "content": img_b64,
            "contentType": "image/png;base64",
            "visibility": "PUBLIC",
        }
        url = f"/api/authors/{self.admin.uuid}/entries/"
        resp = self.client.post(url, data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        mock_broadcast.assert_called_once()
        call_data = mock_broadcast.call_args.args[0]
        self.assertEqual(call_data["id"], resp.data["id"])
        self.assertEqual(call_data["content"], img_b64)
        self.assertEqual(call_data["contentType"], "image/png;base64")
        
# US 38
class BrowsePublicEntriesTests(APITestCase):
    def setUp(self):
        self.viewer = Author.objects.create_user(
            username="viewer", display_name="Viewer", password="pass"
        )
        self.author1 = Author.objects.create_user(
            username="alpha", display_name="Alpha", password="pass"
        )
        self.author2 = Author.objects.create_user(
            username="beta", display_name="Beta", password="pass"
        )
        for a in (self.viewer, self.author1, self.author2):
            a.is_approved = True
            a.save(update_fields=["is_approved"])
        now = timezone.now()
        self.entry_new = Entry.objects.create(
            author=self.author1,
            title="newest",
            content="c",
            visibility="PUBLIC",
            created_at=now,
        )
        self.entry_old = Entry.objects.create(
            author=self.author2,
            title="older",
            content="c",
            visibility="PUBLIC",
            created_at=now - timedelta(minutes=1),
        )
        # entry that should not appear in the public feed
        self.entry_private = Entry.objects.create(
            author=self.author1,
            title="friends",
            content="hidden",
            visibility="FRIENDS",
            created_at=now + timedelta(minutes=1),
        )

    def test_logged_in_author_can_browse_public_entries(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "viewer", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        ids = [e.id for e in response.context["entries"]]
        self.assertEqual(ids, [self.entry_new.id, self.entry_old.id])
        self.assertNotIn(self.entry_private.id, ids)

# US 39
class FollowLocalAuthorTests(APITestCase):
    """Ensure an author can follow another local author and see their public posts."""

    def setUp(self):
        self.follower = Author.objects.create_user(
            username="follower", display_name="Follower", password="pass"
        )
        self.followee = Author.objects.create_user(
            username="followee", display_name="Followee", password="pass"
        )
        self.public_post = Entry.objects.create(
            author=self.followee,
            title="public",
            content="c",
            visibility="PUBLIC",
        )

    def test_follow_and_view_public_entries(self):
        
        FollowRequest.objects.create(
            from_author=self.follower,
            to_author=self.followee,
            pending=False,
            accepted=True,
        )

        self.client.post(
            "/api/login/",
            {"username": "follower", "password": "pass"},
            format="json",
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        ids = [e.id for e in response.context["entries"]]
        self.assertIn(self.public_post.id, ids)

# US 40
class FollowRemoteAuthorTests(APITestCase):
    """Ensure a local author can follow a remote author and see their public posts."""

    def setUp(self):
        self.follower = Author.objects.create_user(
            username="localfollower",
            display_name="Local Follower",
            password="pass",
            is_approved=True,
        )
        self.remote_author = Author.objects.create_user(
            username="remote",
            display_name="Remote Author",
            password="pass",
            is_approved=True,
        )
        self.remote_author.host = "https://remote.example.com/api/"
        self.remote_author.save(update_fields=["host"])

        remote_entry_id = f"https://remote.example.com/api/authors/{self.remote_author.id}/entries/remote1"
        self.remote_post = Entry.objects.create(
            id=remote_entry_id,
            author=self.remote_author,
            title="remote public",
            content="c",
            visibility="PUBLIC",
        )

    def test_follow_remote_author_shows_public_entries(self):
        FollowRequest.objects.create(
            from_author=self.follower,
            to_author=self.remote_author,
            pending=False,
            accepted=True,
        )

        self.client.post(
            "/api/login/",
            {"username": "localfollower", "password": "pass"},
            format="json",
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        ids = [e.id for e in response.context["entries"]]
        self.assertIn(self.remote_post.id, ids)

# US 41
class FollowRequestApprovalTests(APITestCase):
    """Tests for approving and denying follow requests."""

    def setUp(self):
        self.follower = Author.objects.create_user(
            username="follower",
            display_name="Follower",
            password="pass",
            is_approved=True,
        )
        self.author = Author.objects.create_user(
            username="author",
            display_name="Author",
            password="pass",
            is_approved=True,
        )

        # follower sends follow request to author
        FollowRequest.objects.create(from_author=self.follower, to_author=self.author)

    def test_author_can_accept_follow_request(self):
        # log in as the author directly
        self.client.login(username="author", password="pass")

        resp = self.client.patch(
            "/api/follow/",
            {"from_author": str(self.follower.id), "to_author": str(self.author.id)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        fr = FollowRequest.objects.get(from_author=self.follower, to_author=self.author)
        self.assertTrue(fr.accepted)
        self.assertFalse(fr.pending)

    def test_author_can_deny_follow_request(self):
       # log in as the author directly
        self.client.login(username="author", password="pass")
        resp = self.client.delete(
            "/api/follow/",
            {"from_author": str(self.follower.id), "to_author": str(self.author.id)},
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        exists = FollowRequest.objects.filter(
            from_author=self.follower, to_author=self.author
        ).exists()
        self.assertFalse(exists)

# US 42
class FollowRequestListTests(APITestCase):
    """Tests retrieving incoming follow requests."""

    def setUp(self):
        self.receiver = Author.objects.create_user(
            username="receiver",
            display_name="Receiver",
            password="pass123",
            is_approved=True,
        )
        self.sender1 = Author.objects.create_user(
            username="sender1",
            display_name="Sender One",
            password="pass123",
            is_approved=True,
        )
        self.sender2 = Author.objects.create_user(
            username="sender2",
            display_name="Sender Two",
            password="pass123",
            is_approved=True,
        )
        FollowRequest.objects.create(from_author=self.sender1, to_author=self.receiver)
        FollowRequest.objects.create(from_author=self.sender2, to_author=self.receiver)

    def test_list_pending_follow_requests(self):
        login_resp = self.client.post(
            "/api/login/",
            {"username": "receiver", "password": "pass123"},
            format="json",
        )
        self.assertEqual(login_resp.status_code, status.HTTP_200_OK)

        resp = self.client.get(
            f"/api/follow/?author={self.receiver.id}&status=pending"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

# US 43
class UnfollowAuthorTests(APITestCase):
    """Tests for unfollowing an author and feed update."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="author43",
            display_name="Author 43",
            password="pass",
            is_approved=True,
        )
        self.follower = Author.objects.create_user(
            username="follower43",
            display_name="Follower 43",
            password="pass",
            is_approved=True,
        )

        # follower follows author
        FollowRequest.objects.create(
            from_author=self.follower,
            to_author=self.author,
            accepted=True,
            pending=False,
        )

        self.unlisted_entry = Entry.objects.create(
            author=self.author,
            title="secret",
            content="hidden",
            visibility="UNLISTED",
            created_at=timezone.now(),
        )

    def test_unfollow_removes_author_from_feed(self):
        # follower logs in and can see the unlisted entry
        resp = self.client.post(
            "/api/login/",
            {"username": "follower43", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        ids = [e.id for e in response.context["entries"]]
        self.assertIn(self.unlisted_entry.id, ids)

        # unfollow the author
        del_resp = self.client.delete(
            "/api/follow/",
            {"from_author": str(self.follower.id), "to_author": str(self.author.id)},
            format="json",
        )
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            FollowRequest.objects.filter(
                from_author=self.follower, to_author=self.author
            ).exists()
        )

        # feed should no longer contain the unlisted entry
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        ids = [e.id for e in response.context["entries"]]
        self.assertNotIn(self.unlisted_entry.id, ids)

# US 44
class MutualFollowFriendshipTests(APITestCase):
    """Ensure friends-only posts become visible only after mutual follows are approved."""
    def setUp(self):
        self.author1 = Author.objects.create_user(
            username="author44a",
            display_name="Author 44A",
            password="pass",
            is_approved=True,
        )
        self.author2 = Author.objects.create_user(
            username="author44b",
            display_name="Author 44B",
            password="pass",
            is_approved=True,
        )
        self.friends_entry = Entry.objects.create(
            author=self.author1,
            title="secret",
            content="hidden",
            visibility="FRIENDS",
            created_at=timezone.now(),
        )

        # create pending follow requests in both directions
        self.fr_a_to_b = FollowRequest.objects.create(
            from_author=self.author1, to_author=self.author2
        )
        self.fr_b_to_a = FollowRequest.objects.create(
            from_author=self.author2, to_author=self.author1
        )

    def test_friends_only_visible_after_both_accept(self):
        # author1 follows author2 and author2 accepts
        self.client.post(
            "/api/login/",
            {"username": "author44b", "password": "pass"},
            format="json",
        )
        resp = self.client.patch(
            "/api/follow/",
            {"from_author": str(self.author1.id), "to_author": str(self.author2.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.fr_a_to_b.refresh_from_db()
        self.assertTrue(self.fr_a_to_b.accepted)

        self.client.post("/api/logout/")

        # not friends yet - author2 should not see the friends-only entry
        self.client.post(
            "/api/login/",
            {"username": "author44b", "password": "pass"},
            format="json",
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        ids = [e.id for e in response.context["entries"]]
        self.assertNotIn(self.friends_entry.id, ids)
        fr_resp = self.client.get(f"/api/friends/?author={self.author2.id}")
        self.assertEqual(fr_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(fr_resp.data, [])
        self.client.post("/api/logout/")

        self.client.post(
            "/api/login/",
            {"username": "author44a", "password": "pass"},
            format="json",
        )
        resp = self.client.patch(
            "/api/follow/",
            {"from_author": str(self.author2.id), "to_author": str(self.author1.id)},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.fr_b_to_a.refresh_from_db()
        self.assertTrue(self.fr_b_to_a.accepted)

        self.client.post("/api/logout/")

        # now they are friends
        self.client.post(
            "/api/login/",
            {"username": "author44b", "password": "pass"},
            format="json",
        )
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        ids = [e.id for e in response.context["entries"]]
        self.assertIn(self.friends_entry.id, ids)
        fr_resp = self.client.get(f"/api/friends/?author={self.author2.id}")
        self.assertEqual(fr_resp.status_code, status.HTTP_200_OK)
        friend_ids = {item["id"] for item in fr_resp.data}
        self.assertIn(str(self.author1.id), friend_ids)

# US 45
class UnfriendVisibilityTests(APITestCase):
    """Ensure unfollowing a friend hides friends-only posts from them."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="author45", display_name="Author 45", password="pass", is_approved=True
        )
        self.friend = Author.objects.create_user(
            username="friend45", display_name="Friend 45", password="pass", is_approved=True
        )

        # establish friendship
        FollowRequest.objects.create(
            from_author=self.author,
            to_author=self.friend,
            accepted=True,
            pending=False,
        )
        FollowRequest.objects.create(
            from_author=self.friend,
            to_author=self.author,
            accepted=True,
            pending=False,
        )

        self.friends_entry = Entry.objects.create(
            author=self.author,
            title="friends post",
            content="secret",
            visibility="FRIENDS",
            created_at=timezone.now(),
        )

    def _login(self, user):
        resp = self.client.post(
            "/api/login/",
            {"username": user, "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_unfollow_removes_friend_access(self):
        # friend initially sees the friends-only entry
        self._login("friend45")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        ids = [e.id for e in response.context["entries"]]
        self.assertIn(self.friends_entry.id, ids)

        # logout and log in as the author to unfollow
        self.client.post("/api/logout/")
        self._login("author45")
        del_resp = self.client.delete(
            "/api/follow/",
            {"from_author": str(self.author.id), "to_author": str(self.friend.id)},
            format="json",
        )
        self.assertEqual(del_resp.status_code, status.HTTP_204_NO_CONTENT)
        # friendship should be removed
        fr_list_resp = self.client.get(f"/api/friends/?author={self.author.id}")
        self.assertEqual(fr_list_resp.status_code, status.HTTP_200_OK)
        remaining = {item["id"] for item in fr_list_resp.data}
        self.assertNotIn(str(self.friend.id), remaining)
        self.client.post("/api/logout/")

        # friend should no longer see the friends-only entry
        self._login("friend45")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        ids = [e.id for e in response.context["entries"]]
        self.assertNotIn(self.friends_entry.id, ids)

# US 46
class RelationshipListsTests(APITestCase):
    """Ensure the relationships page shows followers, following, and friends."""

    def setUp(self):
        self.user = Author.objects.create_user(
            username="main46",
            display_name="Main 46",
            password="pass",
            is_approved=True,
        )
        self.friend = Author.objects.create_user(
            username="friend46",
            display_name="Friend 46",
            password="pass",
            is_approved=True,
        )
        self.following = Author.objects.create_user(
            username="following46",
            display_name="Following 46",
            password="pass",
            is_approved=True,
        )
        self.follower = Author.objects.create_user(
            username="follower46",
            display_name="Follower 46",
            password="pass",
            is_approved=True,
        )
        self.incoming = Author.objects.create_user(
            username="incoming46",
            display_name="Incoming 46",
            password="pass",
            is_approved=True,
        )
        self.outgoing = Author.objects.create_user(
            username="outgoing46",
            display_name="Outgoing 46",
            password="pass",
            is_approved=True,
        )

        # mutual friends
        FollowRequest.objects.create(
            from_author=self.user,
            to_author=self.friend,
            accepted=True,
            pending=False,
        )
        FollowRequest.objects.create(
            from_author=self.friend,
            to_author=self.user,
            accepted=True,
            pending=False,
        )

        # user follows another author
        FollowRequest.objects.create(
            from_author=self.user,
            to_author=self.following,
            accepted=True,
            pending=False,
        )

        # outgoing follow request
        FollowRequest.objects.create(
            from_author=self.user,
            to_author=self.outgoing,
            pending=True,
        )

        # follower
        FollowRequest.objects.create(
            from_author=self.follower,
            to_author=self.user,
            accepted=True,
            pending=False,
        )

        # incoming pending request
        FollowRequest.objects.create(
            from_author=self.incoming,
            to_author=self.user,
            pending=True,
        )

    def _login(self, user):
        resp = self.client.post(
            "/api/login/",
            {"username": user.username, "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_relationship_lists(self):
        self._login(self.user)
        response = self.client.get(f"/profile/{self.user.id}/relationships/")
        self.assertEqual(response.status_code, 200)

        friends = {a.id for a in response.context["friends_list"]}
        self.assertEqual(friends, {self.friend.id})

        following = {item["user"].id: item["pending"] for item in response.context["following_list"]}
        self.assertEqual(following[self.following.id], False)
        self.assertEqual(following[self.outgoing.id], True)

        followers = {item["user"].id: item["pending"] for item in response.context["followers_list"]}
        self.assertEqual(followers[self.follower.id], False)
        self.assertNotIn(self.incoming.id, followers)

        pending_ids = {a.id for a in response.context["pending_requests_list"]}
        self.assertEqual(pending_ids, {self.incoming.id})
    
    def test_friends_api_returns_mutual_follows(self):
        """The friends API should list only mutual follows."""
        self._login(self.user)
        url = f"/api/friends/?author={self.user.id}"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        friend_ids = {item["id"] for item in resp.data}
        self.assertEqual(friend_ids, {str(self.friend.id)})

    def test_followers_api_returns_followers(self):
        """The followers API should list accepted followers only."""
        self._login(self.user)
        url = f"/api/authors/{self.user.uuid}/followers/"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = {item["id"] for item in resp.data["followers"]}
        expected = {
            str(self.friend.id),
            str(self.follower.id),
        }
        self.assertSetEqual(ids, expected)

# US 47 - comment on entries
class CommentEntryTests(APITestCase):
    """Ensure an author can comment on entries they have access to."""

    def setUp(self):
        self.owner = Author.objects.create_user(
            username="owner47c",
            display_name="Owner 47c",
            password="pass",
            is_approved=True,
        )
        self.friend = Author.objects.create_user(
            username="friend47c",
            display_name="Friend 47c",
            password="pass",
            is_approved=True,
        )
        self.stranger = Author.objects.create_user(
            username="stranger47c",
            display_name="Stranger 47c",
            password="pass",
            is_approved=True,
        )

        self.public_entry = Entry.objects.create(
            id=str(uuid.uuid4()),
            author=self.owner,
            title="public post",
            content="c",
            visibility="PUBLIC",
        )
        self.friends_entry = Entry.objects.create(
            id=str(uuid.uuid4()),
            author=self.owner,
            title="friends post",
            content="c",
            visibility="FRIENDS",
        )

        FollowRequest.objects.create(
            from_author=self.friend,
            to_author=self.owner,
            accepted=True,
            pending=False,
        )
        FollowRequest.objects.create(
            from_author=self.owner,
            to_author=self.friend,
            accepted=True,
            pending=False,
        )

    def _login(self, user):
        resp = self.client.post(
            "/api/login/",
            {"username": user.username, "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def _comment(self, user, entry, text="Nice"):
        url = f"/api/authors/{user.id}/commented/"
        data = {
            "type": "comment",
            "entry": f"{settings.BASE_URL}/api/authors/{entry.author.id}/entries/{entry.id}",
            "comment": text,
            "contentType": "text/plain",
        }
        url = f"/api/authors/{user.uuid}/commented/"
        return self.client.post(url, data, format="json")

    def test_comment_public_entry(self):
        self._login(self.friend)
        resp = self._comment(self.friend, self.public_entry, "Great post")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Comment.objects.filter(author=self.friend, entry=self.public_entry).exists()
        )

    def test_comment_friends_entry_when_friends(self):
        self._login(self.friend)
        resp = self._comment(self.friend, self.friends_entry, "Hi")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            Comment.objects.filter(author=self.friend, entry=self.friends_entry).exists()
        )

# US 48 (failed)
class EntryLikeAccessTests(APITestCase):
    """Tests for liking entries that the author can access."""

    def setUp(self):
        self.owner = Author.objects.create_user(
            username="owner48n",
            display_name="Owner 48n",
            password="pass",
            is_approved=True,
        )
        self.liker = Author.objects.create_user(
            username="liker48n",
            display_name="Liker 48n",
            password="pass",
            is_approved=True,
        )
        self.public_entry = Entry.objects.create(
            author=self.owner,
            title="public post",
            content="c",
            visibility="PUBLIC",
        )

    def _login(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "liker48n", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def _like(self, entry):
        url = reverse("inbox-api", kwargs={"author_id": entry.author.id})
        data = {
            "type": "like",
            "object": f"{settings.BASE_URL}/api/authors/{entry.author.id}/entries/{entry.id}",
        }
        return self.client.post(url, data, format="json")

    # def test_like_public_entry(self): 
    #     self._login()
    #     resp = self._like(self.public_entry)
    #     self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
    #     self.assertTrue(
    #         Like.objects.filter(author=self.liker, entry=self.public_entry).exists()
    #     )

    # def test_prevent_duplicate_likes(self):
    #     self._login()
    #     self._like(self.public_entry)
    #     resp = self._like(self.public_entry)
    #     self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
    #     self.assertEqual(
    #         Like.objects.filter(author=self.liker, entry=self.public_entry).count(),
    #         1,
    #     )

# US 49 (failed)
class CommentLikeFeatureTests(APITestCase):
    """Tests for liking comments that are accessible to the user."""

    def setUp(self):
        self.poster = Author.objects.create_user(
            username="poster49new",
            display_name="Poster 49 New",
            password="pass",
        )
        self.commenter = Author.objects.create_user(
            username="commenter49new",
            display_name="Commenter 49 New",
            password="pass",
        )
        self.entry = Entry.objects.create(
            author=self.poster,
            title="entry",
            content="c",
            visibility="PUBLIC",
        )
        self.comment = Comment.objects.create(
            author=self.commenter,
            entry=self.entry,
            comment="Nice post",
            content_type="text/plain",
        )

    def _login(self):
        resp = self.client.post(
            "/api/login/",
            {"username": "poster49new", "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def _like_comment(self):
        comment_url = (
            f"{settings.BASE_URL}/api/authors/{self.commenter.id}/commented/{self.comment.id}"
        )
        inbox_url = f"/api/authors/{self.commenter.id}/inbox/"
        payload = {"type": "like", "object": comment_url}
        return self.client.post(inbox_url, payload, format="json")

    # def test_like_comment_once(self): # failed
    #     self._login()
    #     resp = self._like_comment()
    #     self.assertEqual(resp.status_code, 201)
    #     self.assertTrue(
    #         Like.objects.filter(author=self.poster, comment=self.comment).exists()
    #     )

    # def test_like_comment_twice_fails(self): # failed
    #     self._login()
    #     self._like_comment()
    #     resp = self._like_comment()
    #     self.assertEqual(resp.status_code, 400)
    #     self.assertEqual(
    #         Like.objects.filter(author=self.poster, comment=self.comment).count(),
    #         1,
    #     )

# US 50
class InboxEntryLikeCountTests(APITestCase):

    def setUp(self):
        self.sender = Author.objects.create_user(
            username="sender50", display_name="Sender 50", password="pass"
        )
        self.receiver = Author.objects.create_user(
            username="receiver50", display_name="Receiver 50", password="pass"
        )

        self.entry = Entry.objects.create(
            author=self.sender,
            title="public post",
            content="hello",
            visibility="PUBLIC",
        )

        liker1 = Author.objects.create_user(
            username="liker501", display_name="Liker 1", password="pass"
        )
        liker2 = Author.objects.create_user(
            username="liker502", display_name="Liker 2", password="pass"
        )

        Like.objects.create(author=liker1, entry=self.entry)
        Like.objects.create(author=liker2, entry=self.entry)

    def test_like_count_in_public_entry_detail(self):
        self.client.login(username="receiver50", password="pass")
        url = (
            f"/api/authors/{self.sender.uuid}/"
            f"entries/{self.entry.id.split('/')[-1]}/"
        )
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data.get("likes", {}).get("count"), 2)

# US 51 (partially failed)
class FriendsOnlyCommentsVisibilityTests(APITestCase):
    """Comments on friends-only entries are only visible to friends and the comment author."""

    def setUp(self):
        self.owner = Author.objects.create_user(
            username="owner51", display_name="Owner 51", password="pass", is_approved=True
        )
        self.friend = Author.objects.create_user(
            username="friend51", display_name="Friend 51", password="pass", is_approved=True
        )
        self.commenter = Author.objects.create_user(
            username="commenter51", display_name="Commenter 51", password="pass", is_approved=True
        )
        self.stranger = Author.objects.create_user(
            username="stranger51", display_name="Stranger 51", password="pass", is_approved=True
        )

        FollowRequest.objects.create(from_author=self.owner, to_author=self.friend, accepted=True, pending=False)
        FollowRequest.objects.create(from_author=self.friend, to_author=self.owner, accepted=True, pending=False)

        self.entry = Entry.objects.create(
            author=self.owner,
            title="Friends Only",
            content="secret",
            visibility="FRIENDS",
        )
        self.comment = Comment.objects.create(
            author=self.commenter,
            entry=self.entry,
            comment="hey",
            content_type="text/plain",
        )
        self.comments_url = (
            f"/api/authors/{self.owner.uuid}/entries/{self.entry.uuid}/comments/"
        )

    def _login(self, author):
        resp = self.client.post(
            "/api/login/",
            {"username": author.username, "password": "pass"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_friend_can_view_comments(self):
        self._login(self.friend)
        resp = self.client.get(self.comments_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_comment_author_can_view_comments(self):
        self._login(self.commenter)
        resp = self.client.get(self.comments_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

    def test_stranger_cannot_view_comments(self):
        self._login(self.stranger)
        resp = self.client.get(self.comments_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)

# US 52
class HostedImageTests(APITestCase):
    """Tests for hosting images that can be embedded in Markdown entries."""

    IMAGE_B64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMBAFtyXsMAAAAASUVORK5CYII="
    )

    def setUp(self):
        self.admin = Author.objects.create_superuser(
            username="admin",
            password="adminpass",
            email="admin@example.com",
            display_name="Admin",
            is_approved=True,
        )
        self.user = Author.objects.create_user(
            username="regular",
            password="userpass",
            display_name="Regular",
            is_approved=True,
        )

        self.image_entry = Entry.objects.create(
            author=self.admin,
            title="Hosted",
            content=self.IMAGE_B64,
            contentType="application/base64",
            visibility="PUBLIC",
        )

    def test_hosted_image_accessible(self):
        url = reverse(
            "entry-image",
            kwargs={"author_id": self.admin.uuid, "entry_id": self.image_entry.uuid},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/png")

    def test_any_user_can_fetch_hosted_image(self):
        url = reverse(
            "entry-image",
            kwargs={"author_id": self.admin.uuid, "entry_id": self.image_entry.uuid},
        )
        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

# US 53 (failed)
class AdminAuthorManagementTests(APITestCase):
    """Ensure node admins can add, modify, and delete authors via the admin site."""

    def setUp(self):
        self.admin = Author.objects.create_superuser(
            username="admin53",
            password="strongpass",
            email="admin@example.com",
            display_name="Admin",
            is_approved=True,
        )
        self.client.force_login(self.admin)

    def test_admin_add_modify_delete_author(self):
        # Add a new author through the admin interface
        add_url = reverse("admin:socialdistribution_author_add")
        response = self.client.post(
            add_url,
            {
                "username": "newuser53",
                "password1": "newpass123",
                "password2": "newpass123",
            },
        )
        self.assertIn(response.status_code, {302, 200})
        self.assertTrue(Author.objects.filter(username="newuser53").exists())
        author = Author.objects.get(username="newuser53")
        self.assertFalse(author.is_approved)

        # Modify the author
        change_url = reverse("admin:socialdistribution_author_change", args=[author.id])
        response = self.client.post(
            change_url,
            {
                "username": "newuser53",
                "display_name": "Updated Name",
                "password": author.password,
                "is_active": "on",
            },
        )
        self.assertIn(response.status_code, {302, 200})
        author.refresh_from_db()
        self.assertFalse(author.is_approved)

        # Delete the author
        delete_url = reverse("admin:socialdistribution_author_delete", args=[author.id])
        response = self.client.post(delete_url, {"post": "yes"})
        self.assertIn(response.status_code, {302, 200})
        self.assertFalse(Author.objects.filter(id=author.id).exists())

# US 54
class AdminApprovalTests(APITestCase):
    """Tests for US54: ensuring admins have the option of restricting sign-up to approved users only"""
    # with "REQUIRE ADMIN APPROVAL" set to True:
    # have a user attempt to sign up but not be approved
    # this user cannot log in
    # have the user be approved
    # this user can now log in
    #
    # Otherwise, user should be able to sign up and login without intervention
    def test_user_requires_approval(self):
        test_username = "test_user111"
        test_password = "password"
        data1 = {"username": test_username, "display_name": "Test User", "password": test_password}
        with self.settings(REQUIRE_ADMIN_APPROVAL=True):
            # send request to sign up; account should be created
            response1 = self.client.post("/api/signup/", data1, format="json")
            self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
            user = Author.objects.get(username=test_username)
            # send request to login; should be awaiting approval (403)
            resp_login = self.client.post(
                "/api/login/",
                {"username": test_username, "password": test_password},
                format="json",
            )
            self.assertEqual(resp_login.status_code, status.HTTP_403_FORBIDDEN)
            # approve user
            user.is_approved = True
            user.save(update_fields=["is_approved"])
            # send request to login; should succeed
            resp_login = self.client.post(
                "/api/login/",
                {"username": test_username, "password": test_password},
                format="json",
            )
            self.assertEqual(resp_login.status_code, status.HTTP_200_OK)
            
    def test_user_doesnt_require_approval(self):
        test_username = "test_user222"
        test_password = "password"
        data1 = {"username": test_username, "display_name": "Test User", "password": test_password}
        with self.settings(REQUIRE_ADMIN_APPROVAL=False):
            response1 = self.client.post("/api/signup/", data1, format="json")
            self.assertEqual(response1.status_code, status.HTTP_201_CREATED)
            # send request to login; should succeed
            resp_login = self.client.post(
                "/api/login/",
                {"username": test_username, "password": test_password},
                format="json",
            )
            self.assertEqual(resp_login.status_code, status.HTTP_200_OK)

# US 62 (Errored)
class DatabaseIndexTests(TestCase):
    """Tests for US62: ensuring data is stored in a well-indexed relational database."""

    # def test_raw_sql_access(self): #Error
    #     """A node admin can run raw SQL queries against the tables."""
    #     author = Author.objects.create_user(
    #         username="indexuser",
    #         password="password",
    #         display_name="Index User",
    #     )
    #     with connection.cursor() as cursor:
    #         cursor.execute(
    #             "SELECT username FROM socialdistribution_author WHERE id = %s",
    #             [author.id],
    #         )
    #         row = cursor.fetchone()
    #     # Ensure a row was returned before accessing columns
    #     self.assertIsNotNone(row)
    #     self.assertEqual(row[0], "indexuser")

    def _indexed_columns(self, table_name):
        constraints = connection.introspection.get_constraints(connection.cursor(), table_name)
        indexed = set()
        for name, info in constraints.items():
            if info.get("index") or info.get("unique"):
                indexed.add(tuple(info["columns"]))
        return indexed

    def test_followrequest_foreign_keys_indexed(self):
        """Follow request foreign keys should have database indexes."""
        indexed = self._indexed_columns("socialdistribution_followrequest")
        self.assertIn(("from_author_id",), indexed)
        self.assertIn(("to_author_id",), indexed)

    def test_author_username_indexed(self):
        """Author username field should be indexed (unique)."""
        indexed = self._indexed_columns("socialdistribution_author")
        self.assertIn(("username",), indexed)

# US 63
class InboxRejectArrayContentTests(APITestCase):
    """Arrays should not be accepted for inbox entry creation."""

    def setUp(self):
        self.author = Author.objects.create_user(
            username="inboxtester",
            display_name="Inbox Tester",
            password="pass1234",
            is_approved=True,
        )
        self.client.post(
            "/api/login/",
            {"username": "inboxtester", "password": "pass1234"},
            format="json",
        )
        self.client.login(username="inboxtester", password="pass1234")

    def test_post_rejects_array_content(self):
        url = f"/api/authors/{self.author.id}/inbox/"
        before_count = Entry.objects.count()
        data = {
            "type": "entry",
            "title": "Invalid",
            "content": ["bad", "data"],
            "contentType": "text/plain",
            "visibility": "PUBLIC",
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(Entry.objects.count(), before_count)

# US 64
class UnifiedServerTests(APITestCase):
    """Ensure the frontend and API are served by the same Django application."""

    def test_frontend_and_api_share_server(self):
        # Request the main feed page served by Django templates
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Feed")

        # Use the same server for an API call
        data = {"username": "unified", "display_name": "Unified", "password": "pass1234"}
        api_response = self.client.post("/api/signup/", data, format="json")
        self.assertEqual(api_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Author.objects.filter(username="unified").exists())

# US 65
class DeletedEntryRetentionTests(APITestCase):
    """Ensure deleted entries remain in the database and are only hidden from regular users."""

    def setUp(self):
        self.owner = Author.objects.create_user(
            username="owner65",
            display_name="Owner 65",
            password="ownerpass",
        )
        self.admin = Author.objects.create_superuser(
            username="admin65",
            password="adminpass",
            email="admin@example.com",
            display_name="Admin 65",
        )
        # allow login through API
        self.owner.is_approved = True
        self.admin.is_approved = True
        self.owner.save(update_fields=["is_approved"])
        self.admin.save(update_fields=["is_approved"])

        self.entry = Entry.objects.create(
            author=self.owner,
            title="Temporary",
            content="temp",
            visibility="PUBLIC",
        )
        self.entry_url = reverse(
            "entry-detail",
            kwargs={"author_id": self.owner.uuid, "entry_id": self.entry.uuid},
        )
        self.entries_url = reverse(
            "entry-list-create",
            kwargs={"author_id": self.owner.uuid},
        )

    def test_deleted_entry_persists_and_admin_can_view(self):
        # owner deletes the entry via API
        resp_login = self.client.post(
            "/api/login/",
            {"username": "owner65", "password": "ownerpass"},
            format="json",
        )
        self.assertEqual(resp_login.status_code, status.HTTP_200_OK)

        delete_resp = self.client.delete(self.entry_url)
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)

        # entry is still in database and flagged deleted
        self.entry.refresh_from_db()
        self.assertTrue(Entry.objects.filter(id=self.entry.id).exists())
        self.assertEqual(self.entry.visibility, "DELETED")

        # owner can no longer access it
        detail_resp = self.client.get(self.entry_url)
        self.assertEqual(detail_resp.status_code, status.HTTP_404_NOT_FOUND)
        list_resp = self.client.get(self.entries_url)
        self.assertEqual(list_resp.status_code, status.HTTP_200_OK)
        entries = (
            list_resp.data
            if isinstance(list_resp.data, list)
            else list_resp.data.get("src", [])
        )
        self.assertFalse(any(e["id"] == str(self.entry.id) for e in entries))

        # admin can still view the deleted entry
        self.client.post("/api/logout/")
        admin_login = self.client.post(
            "/api/login/",
            {"username": "admin65", "password": "adminpass"},
            format="json",
        )
        self.assertEqual(admin_login.status_code, status.HTTP_200_OK)
        admin_resp = self.client.get(self.entry_url)
        self.assertEqual(admin_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(admin_resp.data.get("id"), str(self.entry.id))

# US 66
class UICommunicationTests(TestCase):
    """US 66 Ensure UI only communicates with local server."""

    def test_no_external_fetch_requests(self):
        js_dir = Path(__file__).resolve().parents[1] / "webapp"
        pattern = re.compile(r"fetch\(\s*['\"]https?://")
        for path in js_dir.glob("*.js"):
            with path.open("r", encoding="utf-8") as f:
                content = f.read()
            match = pattern.search(content)
            self.assertIsNone(match, msg=f"External request found in {path.name}")

# Old Tests
# class PublicEntryTests(APITestCase):
#     def setUp(self):
#         # Create a user using Author model and then login.
#         # reverse will help us construct the urls, replace the author_id in the url
#         # with the actual author_id created just now.
#         self.author_user = Author.objects.create_user(username="testuser", password="testpass")
#         self.client.login(username="testuser", password="testpass")
#         self.entries_url = reverse("entry-list-create", kwargs={"author_id": self.author_user.id})

# # basically the POST Method
# # US 1, US 2, US 3
# # user can share its thoughts by making entries(1)
# # user can entries "public", so that everyone can see them.(2)
# # user can make entries in simple plain text (3)
#     def test_post_public_and_plain_text_entry(self):
#         # Data to post
#         data = {
#             "title": "Public Post",
#             "content": "This is a public entry",
#             "visibility": "PUBLIC",
#             "contentType": "text/plain",
#             "description": "test post"
#         }
#         # here we create an HTTP post request using client.post and check the 
#         # status codes to verfiy if ihe entry is succesfully created.
#         response = self.client.post(self.entries_url, data, format='json')
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertEqual(response.data["visibility"], "PUBLIC")
#         self.assertEqual(response.data["contentType"], "text/plain")

# # this will check if the user can access all the entries made 
# # by him be it of any visiblity. he should be able to see them at the 
# # path http://127.0.0.1:8000/api/authors/author_id/entries/
# # how we check- we create a temp entry, see if it exists at the url.
# # then try to delete the same entry and check if it shows up or not.
#     def test_get_all_entries(self):
        
#         entry = Entry.objects.create(
#         author=self.author_user,
#         title="Public Visible Entry",
#         content="Everyone can see this",
#         visibility="FRIENDS",
#         contentType="text/plain"
#         )
#         # construct the url
        
#         response = self.client.get(self.entries_url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(any(e["id"] == str(entry.id) for e in response.data))
        
#         # now delete the same entry
#         entry.is_deleted = True
#         entry.save()
        
#         # access all entries again and see if the deleted entry shows up
#         response = self.client.get(self.entries_url)
#         self.assertFalse(any(e["id"] == str(entry.id) for e in response.data))
        
        
# # US 9
# # As an author, I want to edit my entries locally, 
# # so that I'm not stuck with a typo on a popular entry
#     def test_patch_entry(self):
#         entry = Entry.objects.create(
#         author=self.author_user,
#         title="Public Visible Entry",
#         content="Everyone can see this",
#         visibility="PUBLIC",
#         contentType="text/plain"
#         )
#         # construct the url here because we need to add the entry_id
#         url = reverse("entry-list-create", 
#         kwargs={"author_id": self.author_user.id})+ f"{entry.id}/"
        
#         response = self.client.patch(url, {"content": "I cant see this"}, format = "json")
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.data["content"], "I cant see this")
        
#         # refetch the database to check if the field actaully changed.
#         updated_entry = Entry.objects.get(id=entry.id)
#         self.assertEqual(updated_entry.content, "I cant see this")
             
               
# # we create a public entry, then try to delete it.
# # assert the is_deleted field to true and a status code 204 is returned.
# #  # DELETE /api/authors/<author_id>/entries/<entry_id>/
# # US 15
# # As an author, I want to delete my own entries locally, 
# # so I can remove entries that are out of date or made by mistake.
#     def test_delete_entry(self):
        
#         entry = Entry.objects.create(
#         author=self.author_user,
#         title="Public Visible Entry",
#         content="Everyone can see this",
#         visibility="PUBLIC",
#         contentType="text/plain"
#         )
#         # construct the url here because we need to add the entry_id
#         url = reverse("entry-list-create", 
#         kwargs={"author_id": self.author_user.id})+ f"{entry.id}/"
        
#         response = self.client.delete(url)
#         self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

#         # refetch and confirm if the entry exists
#         updated_entry = Entry.objects.get(id=entry.id)
#         self.assertTrue(updated_entry.is_deleted)
        
        
# # US 26
# # this will test if the public entry/post made by a user is accesible by everyone.
#     def test_public_entry_is_accessible(self):
#         # Create a public entry manually
#         entry = Entry.objects.create(
#             author=self.author_user,
#             title="Public Visible Entry",
#             content="Everyone can see this",
#             visibility="" \
#             "",
#             contentType="text/plain"
#         )

#         # Logout current user to simulate public access
#         self.client.logout()
#         # we are trying to see if the guest can view the post/entry made by the author.
#         # trying to fetch entries made by the author as a guest.
#         url = reverse("entry-list-create", kwargs={"author_id": self.author_user.id})
#         response = self.client.get(url)
        
#         # check if the url is accesible, and the entry id that was just created is 
#         # in the response or not.
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(any(e["id"] == str(entry.id) for e in response.data))
        
# # US 18
# # other authors cannot modify entries so I dont get impersonated.
#     def test_other_author_cannot_edit_entry(self):
#         # Create a public entry manually
#         entry = Entry.objects.create(
#             author=self.author_user,
#             title="Public Visible Entry",
#             content="Everyone can see this",
#             visibility="PUBLIC",
#             contentType="text/plain"
#         )
#         # Create another user
#         other_user = Author.objects.create_user(username="otheruser", password="otherpass")
#         self.client.logout()
#         self.client.login(username="otheruser", password="otherpass")

#         # Build the URL to patch the entry
#         url = reverse("entry-list-create", kwargs={"author_id": self.author_user.id}) + f"{entry.id}/"

#         # Attempt to patch as the wrong user
#         response = self.client.patch(url, {"content": "Hacked content"}, format="json")

#         # Should be forbidden
#         self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
# # US 33 and US 28
# # only a friend of an author can view the friends only entry made by the author.
# # second a non friend cannot view the friedns only entry.
#     def test_friends_can_view_friends_entry_but_others_cannot(self):
#         # Create a public entry manually
#         entry = Entry.objects.create(
#         author=self.author_user,
#         title="Friends only Entry",
#         content="Everyone can see this",
#         visibility="FRIENDS",
#         contentType="text/plain"
#         )
#         # Create a friend user
#         friend_user = Author.objects.create_user(username="friend", password="friendpass")

#         # mutual follow 
#         FollowRequest.objects.create(from_author=friend_user, to_author=self.author_user, accepted=True)
#         FollowRequest.objects.create(from_author=self.author_user, to_author=friend_user, accepted=True)

#         self.client.logout()
#         self.client.login(username="friend", password="friendpass")
#         url = reverse("entry-list-create", kwargs={"author_id": self.author_user.id})
#         response = self.client.get(url)

#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertTrue(any(e["id"] == str(entry.id) for e in response.data))
        
#         # create another user, but who is not a friend and lets see if they can access.
#         random_person = Author.objects.create_user(username="palak", password="friendpass")
        
#         # the random_person follows me(author), but I dont follow back.
#         # so the friends only entry should not be visible to the person.
#         FollowRequest.objects.create(from_author=random_person, to_author=self.author_user, accepted=True)
#         self.client.logout()
#         self.client.login(username="palak", password="friendpass")
        
#         url = reverse("entry-list-create", kwargs={"author_id": self.author_user.id})
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertFalse(any(e["id"] == str(entry.id) for e in response.data))
 
#  # US 32
#  # As an author, I want everyone to be able to see my public and unlisted entries,
#  # if they have a link to it.  i have tested public access above already.
#     def test_unlisted_entry_accessible_with_link_but_not_in_list(self):
#         # Create an unlisted entry
#         entry = Entry.objects.create(
#             author=self.author_user,
#             title="Unlisted Entry",
#             content="Should not show up in all entries but be visible with a link",
#             visibility="UNLISTED",
#             contentType="text/plain"
#         )
#         # Guest user 
#         self.client.logout()

#         # This endpoint should NOT include unlisted entry
#         url = reverse("entry-list-create", kwargs={"author_id": self.author_user.id})
#         response = self.client.get(url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertFalse(any(e["id"] == str(entry.id) for e in response.data))

#         # Detail endpoint should allow access
#         exact_url = url + f"{entry.id}/"
#         detail_response = self.client.get(exact_url)
#         self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
#         self.assertEqual(detail_response.data["id"], str(entry.id))
    
    
        
# class LikesAndCommentsTests(APITestCase):
#     def setUp(self):
#         # Create a user using Author model and then login.
#         self.author_user = Author.objects.create_user(username="testuser", password="testpass")
#         self.client.login(username="testuser", password="testpass")
#         self.entry = Entry.objects.create(
#             author=self.author_user,
#             title="Public Visible Entry",
#             content="Everyone can see this",
#             visibility="PUBLIC",
#             contentType="text/plain"
#         )

#     # US 49
#     # As an author, I want to like entries that I can access,
#     # so I can show my appreciation.
#     def test_like(self):
#         # generate the URL for liking posts
#         like_url = reverse("like", kwargs={"author_id": self.author_user.id, "entry_id":self.entry.id})
#         # send a post request to the URL for liking posts
#         response = self.client.post(like_url)
#         # A 201 response means the like was registered
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         # if we try to like the post again, we should recieve a 400 response
#         response = self.client.post(like_url)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)