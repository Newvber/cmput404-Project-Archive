# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-23
import requests
from django.conf import settings
from django.db.models import Q
from .models import RemoteNode, Entry, Comment, Like, Author, FollowRequest
from .serializers.entrydetailserializer import EntryDetailSerializer
from .serializers.commentserializer import CommentSerializer
from .serializers.likeserializer import LikeSerializer
from requests.auth import HTTPBasicAuth
from urllib.parse import urlparse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import uuid
import threading

def _remote_nodes():
    """Yield (base_url, auth) for each configured remote node."""
    db_nodes = list(RemoteNode.objects.all())
    if db_nodes:
        for node in db_nodes:
            auth = None
            if node.username and node.password:
                auth = HTTPBasicAuth(node.username, node.password)
            yield node.base_url.rstrip("/") + "/", auth
    else:
        for item in getattr(settings, "REMOTE_NODES", []):
            if isinstance(item, str):
                yield item.rstrip("/") + "/", None
            else:
                base = item.get("base_url") or item.get("url") or ""
                auth = None
                if item.get("username") and item.get("password"):
                    auth = HTTPBasicAuth(item["username"], item["password"])
                yield base.rstrip("/") + "/", auth

def _get_auth_for_url(url: str):
    """Return Basic auth for a given remote URL if configured."""
    for base, auth in _remote_nodes():
        if url.startswith(base):
            return auth
    return None

def get_or_create_remote_author(data, default_host=None):
    """Create or update a local Author entry from remote data."""
    author_url = data.get("id") if isinstance(data, dict) else None
    if not author_url:
        return None

    author_fqid = str(author_url).rstrip("/")
    author_uuid = author_fqid.split("/")[-1]

    if default_host:
        base = default_host.rstrip("/")
    else:
        parsed = urlparse(author_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

    host = base.rstrip('/')
    if host.endswith('/api'):
        host = host + '/'
    else:
        host = host + '/api/'
    defaults = {
        "username": author_uuid[:60],
        "display_name": data.get("displayName", author_uuid),
        "host": host,
        "profile_image": data.get("profileImage", data.get("profile_image", "")),
        "github_link": data.get("github", ""),
        "uuid": author_uuid,
    }

    author = Author.objects.filter(uuid=author_uuid).first()
    if not author:
        author = Author.objects.filter(id=author_fqid).first()

    if author is None:
        author = Author(id=author_fqid, **defaults)
        author.set_unusable_password()
        author.is_approved = True
        author.save()
        return author

    updates = []
    local_host = settings.BASE_URL.rstrip('/') + '/api/'
    if author.host != host and author.host.rstrip('/') != local_host.rstrip('/'):
        author.host = host
        updates.append("host")
    display_name = data.get("displayName")
    profile_image = data.get("profileImage") or data.get("profile_image")
    github_link = data.get("github")
    if display_name and author.display_name != display_name:
        author.display_name = display_name
        updates.append("display_name")
    if profile_image and author.profile_image != profile_image:
        author.profile_image = profile_image
        updates.append("profile_image")
    if github_link and author.github_link != github_link:
        author.github_link = github_link
        updates.append("github")
    if updates:
        author.save(update_fields=updates)
    return author


def sync_remote_authors(remote_node):
    """Fetch authors from a remote node and ensure local copies exist."""
    base = remote_node.base_url.rstrip("/") + "/"
    auth = None
    if remote_node.username and remote_node.password:
        auth = HTTPBasicAuth(remote_node.username, remote_node.password)
    try:
        res = requests.get(f"{base}api/authors/?size=100", timeout=5, auth=auth)
        res.raise_for_status()
        authors = res.json().get("authors", [])
    except requests.RequestException:
        print(f"Failed to fetch authors from {base}")
        return []

    for item in authors:
        get_or_create_remote_author(item, default_host=base)
    return authors


def broadcast_entry_to_remotes(entry_data):
    def send_to_author(author, base, auth):
        author_id = str(author.get('id', '')).rstrip('/').split('/')[-1]
        inbox_url = f"{base}api/authors/{author_id}/inbox/"
        try:
            requests.post(
                inbox_url,
                json=entry_data,
                headers={"Content-Type": "application/json"},
                timeout=5,
                auth=auth,
            )
        except requests.RequestException:
            pass

    for base, auth in _remote_nodes():
        try:
            res = requests.get(f"{base}api/authors/?size=100", timeout=5, auth=auth)
            res.raise_for_status()
            authors = res.json().get('authors', [])
        except requests.RequestException:
            continue
        for author in authors:
            threading.Thread(target=send_to_author, args=(author, base, auth)).start()

def broadcast_like_to_remotes(like_data):
    """Send a like object to all remote node inboxes in parallel."""

    def send_to_author(author, base, auth):
        author_id = str(author.get('id', '')).rstrip('/').split('/')[-1]
        inbox_url = f"{base}api/authors/{author_id}/inbox/"
        try:
            requests.post(
                inbox_url,
                json=like_data,
                headers={"Content-Type": "application/json"},
                timeout=5,
                auth=auth,
            )
        except requests.RequestException:
            pass

    for base, auth in _remote_nodes():
        try:
            res = requests.get(f"{base}api/authors/?size=100", timeout=5, auth=auth)
            res.raise_for_status()
            authors = res.json().get('authors', [])
        except requests.RequestException:
            continue

        for author in authors:
            threading.Thread(target=send_to_author, args=(author, base, auth)).start()

def broadcast_comment_to_remotes(comment_data):
    """Send a comment object to all remote node inboxes in parallel."""
    origin_host = ""
    author = comment_data.get("author")
    if isinstance(author, dict):
        origin_host = author.get("host") or author.get("id", "")
    if not origin_host:
        origin_host = comment_data.get("id", "")
    origin_netloc = urlparse(origin_host).netloc

    def send_to_author(author, base, auth):
        author_id = str(author.get('id', '')).rstrip('/').split('/')[-1]
        inbox_url = f"{base}api/authors/{author_id}/inbox/"
        try:
            requests.post(
                inbox_url,
                json=comment_data,
                headers={"Content-Type": "application/json"},
                timeout=5,
                auth=auth,
            )
        except requests.RequestException:
            pass

    for base, auth in _remote_nodes():
        # Skip sending back to the originating host
        if origin_netloc and urlparse(base).netloc == origin_netloc:
            continue
        try:
            res = requests.get(f"{base}api/authors/?size=100", timeout=5, auth=auth)
            res.raise_for_status()
            authors = res.json().get('authors', [])
        except requests.RequestException:
            continue

        for author in authors:
            threading.Thread(target=send_to_author, args=(author, base, auth)).start()

def broadcast_delete_to_remotes(entry_data):
    """Notify remote nodes that an entry has been deleted."""

    data = dict(entry_data)
    data["visibility"] = "DELETED"

    def send_to_author(author, base, auth):
        author_id = str(author.get('id', '')).rstrip('/').split('/')[-1]
        inbox_url = f"{base}api/authors/{author_id}/inbox/"
        try:
            requests.post(
                inbox_url,
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=5,
                auth=auth,
            )
        except requests.RequestException:
            pass

    for base, auth in _remote_nodes():
        try:
            res = requests.get(f"{base}api/authors/?size=100", timeout=5, auth=auth)
            res.raise_for_status()
            authors = res.json().get('authors', [])
        except requests.RequestException:
            continue

        for author in authors:
            threading.Thread(target=send_to_author, args=(author, base, auth)).start()

def broadcast_follow_to_remotes(follow_data):
    def send_to_author(author, base, auth):
        author_id = str(author.get('id', '')).rstrip('/').split('/')[-1]
        inbox_url = f"{base}api/authors/{author_id}/inbox/"
        try:
            requests.post(
                inbox_url,
                json=follow_data,
                headers={"Content-Type": "application/json"},
                timeout=5,
                auth=auth,
            )
        except requests.RequestException:
            pass

    for base, auth in _remote_nodes():
        try:
            res = requests.get(f"{base}api/authors/?size=100", timeout=5, auth=auth)
            res.raise_for_status()
            authors = res.json().get('authors', [])
        except requests.RequestException:
            continue
        for author in authors:
            threading.Thread(target=send_to_author, args=(author, base, auth)).start()

def send_all_to_new_remote(remote_node):
    """Send all local public entries, comments and likes to a new remote."""
    base = remote_node.base_url.rstrip('/') + '/'
    auth = None
    if remote_node.username and remote_node.password:
        auth = HTTPBasicAuth(remote_node.username, remote_node.password)
    authors = sync_remote_authors(remote_node)
    if not authors:
        return

    entries = Entry.objects.filter(visibility="PUBLIC")
    comments = Comment.objects.filter(entry__visibility="PUBLIC")
    likes = Like.objects.filter(
        Q(entry__visibility="PUBLIC") |
        Q(comment__entry__visibility="PUBLIC")
        )

    for author in authors:
        author_id = str(author.get('id', '')).rstrip('/').split('/')[-1]
        inbox_url = f"{base}api/authors/{author_id}/inbox/"

        for entry in entries:
            entry_data = EntryDetailSerializer(entry).data
            try:
                requests.post(
                    inbox_url,
                    json=entry_data,
                    headers={"Content-Type": "application/json"},
                    timeout=5,
                    auth=auth,
                )
            except requests.RequestException:
                continue

        for comment in comments:
            comment_data = CommentSerializer(comment).data
            try:
                requests.post(
                    inbox_url,
                    json=comment_data,
                    headers={"Content-Type": "application/json"},
                    timeout=5,
                    auth=auth,
                )
            except requests.RequestException:
                continue

        for like in likes:
            like_data = LikeSerializer(like).data
            try:
                requests.post(
                    inbox_url,
                    json=like_data,
                    headers={"Content-Type": "application/json"},
                    timeout=5,
                    auth=auth,
                )
            except requests.RequestException:
                continue

def import_remote_entry(entry_data, default_host=None):
    """Create or update an Entry object from remote data."""

    entry_id = entry_data.get("id")
    author_info = entry_data.get("author")
    if not entry_id or not author_info:
        return None

    author = get_or_create_remote_author(author_info, default_host=default_host)
    if author is None:
        return None

    defaults = {
        "author": author,
        "title": entry_data.get("title", ""),
        "content": entry_data.get("content", ""),
        "contentType": entry_data.get("contentType", "text/plain"),
        "description": entry_data.get("description", ""),
        "visibility": entry_data.get("visibility", "PUBLIC"),
    }

    published = entry_data.get("published")
    if published:
        dt = parse_datetime(published)
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.utc)
            defaults["created_at"] = dt
            defaults["updated_at"] = dt

    Entry.objects.update_or_create(id=entry_id, defaults=defaults)
    return True

def sync_remote_entries(remote_node):
    """Fetch existing entries from a remote node."""

    base = remote_node.base_url.rstrip("/") + "/"
    auth = None
    if remote_node.username and remote_node.password:
        auth = HTTPBasicAuth(remote_node.username, remote_node.password)

    try:
        res = requests.get(f"{base}api/authors/?size=100", timeout=5, auth=auth)
        res.raise_for_status()
        authors = res.json().get("authors", [])
    except requests.RequestException:
        print(f"Failed to fetch authors from {base}")
        return

    for item in authors:
        author = get_or_create_remote_author(item, default_host=base)
        if not author:
            continue
        try:
            resp = requests.get(
                f"{base}api/authors/{author.uuid}/entries/",
                timeout=5,
                auth=auth,
            )
            resp.raise_for_status()
            entries = resp.json()
        except requests.RequestException:
            continue

        if isinstance(entries, dict):
            entries = (
                entries.get("src")
                or entries.get("items")
                or entries.get("results")
                or entries.get("entries")
                or []
            )

        for e in entries:
            import_remote_entry(e, default_host=base)

def import_remote_comment(comment_data, default_host=None):
    """Create or update a Comment object from remote data."""

    comment_id = comment_data.get("id")
    author_info = comment_data.get("author")
    entry_url = comment_data.get("entry")
    if not comment_id or not author_info or not entry_url:
        return None

    author = get_or_create_remote_author(author_info, default_host=default_host)
    if author is None:
        return None

    entry = Entry.objects.filter(id=entry_url).first()
    if entry is None:
        return None

    defaults = {
        "entry": entry,
        "author": author,
        "comment": comment_data.get("comment", ""),
        "content_type": comment_data.get("contentType", "text/plain"),
    }

    uuid_value = comment_data.get("uuid")
    if uuid_value:
        defaults["uuid"] = uuid_value

    published = comment_data.get("published")
    if published:
        dt = parse_datetime(published)
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.utc)
            defaults["created_at"] = dt

    Comment.objects.update_or_create(id=comment_id, defaults=defaults)
    return True

def sync_remote_comments(remote_node):
    """Fetch existing comments from a remote node."""

    base = remote_node.base_url.rstrip("/") + "/"
    auth = None
    if remote_node.username and remote_node.password:
        auth = HTTPBasicAuth(remote_node.username, remote_node.password)

    try:
        res = requests.get(f"{base}api/authors/?size=100", timeout=5, auth=auth)
        res.raise_for_status()
        authors = res.json().get("authors", [])
    except requests.RequestException:
        print(f"Failed to fetch authors from {base}")
        return

    for item in authors:
        author = get_or_create_remote_author(item, default_host=base)
        if not author:
            continue
        try:
            resp = requests.get(
                f"{base}api/authors/{author.uuid}/entries/",
                timeout=5,
                auth=auth,
            )
            resp.raise_for_status()
            entries = resp.json()
        except requests.RequestException:
            continue

        if isinstance(entries, dict):
            entries = (
                entries.get("src")
                or entries.get("items")
                or entries.get("results")
                or entries.get("entries")
                or []
            )

        for e in entries:
            entry_id = str(e.get("id", ""))
            if not entry_id:
                continue
            entry_uuid = entry_id.rstrip("/").split("/")[-1]
            comments_url = f"{base}api/authors/{author.uuid}/entries/{entry_uuid}/comments/"
            try:
                c_resp = requests.get(comments_url, timeout=5, auth=auth)
                c_resp.raise_for_status()
                comments_obj = c_resp.json()
            except requests.RequestException:
                continue

            if isinstance(comments_obj, dict):
                comments = comments_obj.get("src") or comments_obj.get("comments") or comments_obj.get("items") or comments_obj.get("results") or []
            else:
                comments = comments_obj

            for c in comments:
                import_remote_comment(c, default_host=base)

def import_remote_like(like_data, default_host=None):
    """Create or update a Like object from remote data."""

    like_id = like_data.get("id")
    author_info = like_data.get("author")
    obj_url = like_data.get("object")
    if not like_id or not author_info or not obj_url:
        return None

    author = get_or_create_remote_author(author_info, default_host=default_host)
    if author is None:
        return None

    defaults = {
        "author": author,
        "object_url": obj_url,
    }

    last = str(like_id).rstrip('/').split('/')[-1]
    try:
        defaults["uuid"] = uuid.UUID(last)
    except ValueError:
        pass

    published = like_data.get("published")
    if published:
        dt = parse_datetime(published)
        if dt:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.utc)
            defaults["created_at"] = dt

    if "/commented/" in obj_url:
        comment = Comment.objects.filter(id=obj_url).first()
        if comment is None:
            cid = obj_url.rstrip('/').split('/')[-1]
            comment = Comment.objects.filter(uuid=cid).first()
        if comment is None:
            return None
        defaults["comment"] = comment
    else:
        entry = Entry.objects.filter(id=obj_url).first()
        if entry is None:
            eid = obj_url.rstrip('/').split('/')[-1]
            entry = Entry.objects.filter(id__endswith=eid).first()
        if entry is None:
            return None
        defaults["entry"] = entry

    Like.objects.update_or_create(id=like_id, defaults=defaults)
    return True


def sync_remote_likes(remote_node):
    """Fetch likes from a remote node for entries and comments."""

    base = remote_node.base_url.rstrip('/') + '/'
    auth = None
    if remote_node.username and remote_node.password:
        auth = HTTPBasicAuth(remote_node.username, remote_node.password)

    try:
        res = requests.get(f"{base}api/authors/?size=100", timeout=5, auth=auth)
        res.raise_for_status()
        authors = res.json().get("authors", [])
    except requests.RequestException:
        return

    for item in authors:
        author = get_or_create_remote_author(item, default_host=base)
        if not author:
            continue
        try:
            resp = requests.get(
                f"{base}api/authors/{author.uuid}/entries/",
                timeout=5,
                auth=auth,
            )
            resp.raise_for_status()
            entries = resp.json()
        except requests.RequestException:
            continue

        if isinstance(entries, dict):
            entries = (
                entries.get("src")
                or entries.get("items")
                or entries.get("results")
                or entries.get("entries")
                or []
            )

        for e in entries:
            entry_id = str(e.get("id", ""))
            if not entry_id:
                continue
            entry_uuid = entry_id.rstrip('/').split('/')[-1]

            likes_url = f"{base}api/authors/{author.uuid}/entries/{entry_uuid}/likes/"
            try:
                l_resp = requests.get(likes_url, timeout=5, auth=auth)
                l_resp.raise_for_status()
                likes_obj = l_resp.json()
            except requests.RequestException:
                likes_obj = None
            if isinstance(likes_obj, dict):
                likes = likes_obj.get("src") or likes_obj.get("items") or likes_obj.get("results") or []
            else:
                likes = likes_obj or []
            for l in likes:
                import_remote_like(l, default_host=base)

            comments_url = f"{base}api/authors/{author.uuid}/entries/{entry_uuid}/comments/"
            try:
                c_resp = requests.get(comments_url, timeout=5, auth=auth)
                c_resp.raise_for_status()
                comments_obj = c_resp.json()
            except requests.RequestException:
                continue

            if isinstance(comments_obj, dict):
                comments = comments_obj.get("src") or comments_obj.get("comments") or comments_obj.get("items") or comments_obj.get("results") or []
            else:
                comments = comments_obj

            for c in comments:
                comment_id = str(c.get("id", ""))
                if not comment_id:
                    continue
                comment_uuid = comment_id.rstrip('/').split('/')[-1]
                c_likes_url = f"{base}api/authors/{author.uuid}/entries/{entry_uuid}/comments/{comment_uuid}/likes/"
                try:
                    cl_resp = requests.get(c_likes_url, timeout=5, auth=auth)
                    cl_resp.raise_for_status()
                    comment_likes_obj = cl_resp.json()
                except requests.RequestException:
                    comment_likes_obj = None
                if isinstance(comment_likes_obj, dict):
                    comment_likes = comment_likes_obj.get("src") or comment_likes_obj.get("items") or comment_likes_obj.get("results") or []
                else:
                    comment_likes = comment_likes_obj or []
                for l in comment_likes:
                    import_remote_like(l, default_host=base)

def broadcast_unlisted_entry_to_followers(entry_data):
    """Send an unlisted entry to remote followers' inboxes."""

    author_url = entry_data.get('author', {}).get('id')
    if not author_url:
        return

    try:
        author_id = str(author_url).rstrip('/').split('/')[-1]
        author = Author.objects.get(uuid=author_id)
    except (Author.DoesNotExist, Exception):
        return

    local_base = settings.BASE_URL.rstrip('/')

    follower_ids = FollowRequest.objects.filter(
        to_author=author, accepted=True
    ).values_list('from_author_id', flat=True)

    for follower in Author.objects.filter(id__in=follower_ids):
        host = follower.host.rstrip('/')
        if not host.endswith('/api'):
            host = host + '/api'
        if host.rstrip('/') == local_base.rstrip('/'):
            continue
        inbox_url = f"{host}/authors/{follower.uuid}/inbox/"
        try:
            requests.post(
                inbox_url,
                json=entry_data,
                headers={"Content-Type": "application/json"},
                timeout=5,
                auth=_get_auth_for_url(inbox_url),
            )
        except requests.RequestException:
            continue

def send_unlisted_entries_to_follower(author: Author, follower: Author):
    """Send all existing unlisted entries from `author` to a follower's inbox."""

    host = follower.host.rstrip('/')
    if not host.endswith('/api'):
        host = host + '/api'
    if host.rstrip('/') == settings.BASE_URL.rstrip('/') + '/api':
        return

    inbox_url = f"{host}/authors/{follower.uuid}/inbox/"

    for entry in Entry.objects.filter(author=author, visibility='UNLISTED'):
        entry_data = EntryDetailSerializer(entry).data
        try:
            requests.post(
                inbox_url,
                json=entry_data,
                headers={"Content-Type": "application/json"},
                timeout=5,
                auth=_get_auth_for_url(inbox_url),
            )
        except requests.RequestException:
            continue

def send_friends_entries_to_friend(author: Author, friend: Author):
    """Send all existing friends-only entries from `author` to a friend's inbox."""

    host = friend.host.rstrip('/')
    if not host.endswith('/api'):
        host = host + '/api'
    if host.rstrip('/') == settings.BASE_URL.rstrip('/') + '/api':
        return

    inbox_url = f"{host}/authors/{friend.uuid}/inbox/"

    for entry in Entry.objects.filter(author=author, visibility='FRIENDS'):
        entry_data = EntryDetailSerializer(entry).data
        try:
            requests.post(
                inbox_url,
                json=entry_data,
                headers={"Content-Type": "application/json"},
                timeout=5,
                auth=_get_auth_for_url(inbox_url),
            )
        except requests.RequestException:
            continue

def broadcast_entry_to_friends(entry_data):
    """Send a friends-only entry to remote friends' inboxes."""

    author_url = entry_data.get('author', {}).get('id')
    if not author_url:
        return

    try:
        author_id = str(author_url).rstrip('/').split('/')[-1]
        author = Author.objects.get(uuid=author_id)
    except (Author.DoesNotExist, Exception):
        return

    following_ids = set(
        FollowRequest.objects.filter(from_author=author, accepted=True)
        .values_list("to_author_id", flat=True)
    )
    follower_ids = set(
        FollowRequest.objects.filter(to_author=author, accepted=True)
        .values_list("from_author_id", flat=True)
    )
    friend_ids = following_ids.intersection(follower_ids)

    local_base = settings.BASE_URL.rstrip('/') + '/api'

    for friend in Author.objects.filter(id__in=friend_ids):
        host = friend.host.rstrip('/')
        if not host.endswith('/api'):
            host = host + '/api'
        if host.rstrip('/') == local_base.rstrip('/'):
            continue
        inbox_url = f"{host}/authors/{friend.uuid}/inbox/"
        try:
            requests.post(
                inbox_url,
                json=entry_data,
                headers={"Content-Type": "application/json"},
                timeout=5,
                auth=_get_auth_for_url(inbox_url),
            )
        except requests.RequestException:
            continue