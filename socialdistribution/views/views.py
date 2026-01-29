# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework.decorators import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.views.generic import TemplateView
from django.db.models import Q
from django.shortcuts import get_object_or_404
from socialdistribution.models import Author, FollowRequest, Entry, Like, Comment, RemoteNode
from socialdistribution.models.entry import Entry
from socialdistribution.serializers import EntryDetailSerializer, FollowRequestSerializer, LikeSerializer, InboxItemSerializer, CommentSerializer
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import IntegrityError
from urllib.parse import unquote, urlparse
from django.utils.crypto import get_random_string
import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth
import uuid
from socialdistribution.utils import (
    broadcast_like_to_remotes,
    broadcast_comment_to_remotes,
    _get_auth_for_url,
    send_friends_entries_to_friend,
)

# to test it, create an author mnanually in the signup page or use an existing
# in the admin panel. copy the uuid of the author, and send a POST request 
# using postman to /service/api/authors/author id copied/inbox. ALso set content-type.
class InboxAPIView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication,]
    permission_classes = [IsAuthenticated]

    def _get_or_create_author(self, data, default_host=None):
        """Return an Author instance from the payload."""
        author_url = data.get('id') if isinstance(data, dict) else None
        if not author_url:
            return None

        author_fqid = str(author_url).rstrip('/')
        author_uuid = author_fqid.split('/')[-1]
        if default_host:
            base = default_host.rstrip('/')
        else:
            parsed = urlparse(author_url)
            base = f"{parsed.scheme}://{parsed.netloc}"
        host = base.rstrip('/')
        if host.endswith('/api'):
            host = host + '/'
        else:
            host = host + '/api/'
        defaults = {
            'username': author_uuid[:60],
            'display_name': data.get('displayName', author_uuid),
            'host': host,
            'profile_image': data.get('profileImage', data.get('profile_image', '')),
        }
        defaults['uuid'] = author_uuid
        
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
            updates.append('host')
        display_name = data.get('displayName')
        profile_image = data.get('profileImage') or data.get('profile_image')
        if display_name and author.display_name != display_name:
            author.display_name = display_name
            updates.append('display_name')
        if profile_image and author.profile_image != profile_image:
            author.profile_image = profile_image
            updates.append('profile_image')
        if updates:
            author.save(update_fields=updates)
        return author


    def post(self, request, author_id):
        remote_node = RemoteNode.objects.filter(service_account=request.user).first()
        if not request.auth and remote_node is None and not request.user.is_authenticated:
            return Response({"detail": "Unknown remote node."}, status=status.HTTP_403_FORBIDDEN)
        payload  = request.data
        obj_type = payload.get('type')

        if obj_type == 'entry':
            print(payload)
            payload_id = payload.get("id")
            entry = None
            if payload_id:
                entry = Entry.objects.filter(id=payload_id).first()
            entry_author = self._get_or_create_author(payload.get('author', {})) or request.user
            if entry is not None:
                serializer = EntryDetailSerializer(entry, data=payload, partial=True)
                status_code = status.HTTP_200_OK
                serializer.is_valid(raise_exception=True)
                entry = serializer.save()
            else:
                serializer = EntryDetailSerializer(data=payload)
                serializer.is_valid(raise_exception=True)
                entry = Entry.objects.create(
                    id=payload_id or f"{entry_author.host.rstrip('/')}/api/authors/{entry_author.id}/entries/{get_random_string(10)}",
                    author=entry_author,
                    **serializer.validated_data,
                )
                status_code = status.HTTP_201_CREATED
            return Response(EntryDetailSerializer(entry).data, status=status_code)
        elif obj_type == 'comment':
            serializer = CommentSerializer(data=payload, context={'request': request})
        elif obj_type == 'like':
            print(payload)
            raw_object = payload.get('object', '')
            entry_url  = unquote(raw_object).rstrip('/')
            payload['object'] = entry_url

            like_author = self._get_or_create_author(payload.get('author', {})) or request.user
            serializer = LikeSerializer(data=payload, context={'request': request, 'view': self, 'author': like_author})
        elif obj_type == 'follow':
            follow_author = self._get_or_create_author(payload.get('actor', {})) or request.user
            serializer = FollowRequestSerializer(data=payload, context={'request': request, 'view': self})
        else:
            return Response(
                {'detail': f'Unknown type "{obj_type}"'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer.is_valid(raise_exception=True)

        try:
            if obj_type == 'follow':
                # ``author_id`` from the URL is a UUID. Convert it to the
                # fully-qualified author ID when saving the follow request.
                try:
                    target_author = Author.objects.get(uuid=author_id)
                    target_id = target_author.id
                except Author.DoesNotExist:
                    target_id = author_id

                fr = serializer.save(
                    from_author_id=follow_author.id,
                    to_author_id=target_id
                )
                follow_data = FollowRequestSerializer(fr).data

                object_host = follow_data.get('object', {}).get('host')
                object_host = object_host.rstrip('/')
                if object_host.endswith('/api'):
                    object_host = object_host + '/'
                else:
                    object_host = object_host + '/api/'

                local_host = settings.BASE_URL.rstrip('/') + '/api'
                obj_netloc = urlparse(object_host.rstrip('/')).netloc if object_host else ''
                local_netloc = urlparse(local_host.rstrip('/')).netloc
                if object_host and obj_netloc != local_netloc:
                    inbox_url = f"{object_host.rstrip('/')}/authors/{author_id}/inbox/"
                    try:
                        requests.post(
                            inbox_url,
                            json=follow_data,
                            headers={'Content-Type': 'application/json'},
                            auth=_get_auth_for_url(inbox_url),
                        )
                    except requests.RequestException:
                        pass

                    # Locally mark the relationship as accepted without
                    # notifying the remote node again
                    fr.accepted = True
                    fr.pending = False
                    fr.save(update_fields=['accepted', 'pending'])
                    follow_data = FollowRequestSerializer(fr).data

                    if FollowRequest.objects.filter(
                        from_author_id=target_id,
                        to_author_id=follow_author.id,
                        accepted=True,
                    ).exists():
                        send_friends_entries_to_friend(follow_author, fr.to_author)

                # broadcast_follow_to_remotes(follow_data)
                return Response(
                    follow_data,
                    status=status.HTTP_201_CREATED
                )

            elif obj_type == 'like':
                like = serializer.save(author=like_author)
                like_data = serializer.to_representation(like)

                target = like.entry or like.comment.entry
                entry_host = urlparse(target.id).scheme + '://' + urlparse(target.id).netloc
                local_host = request.build_absolute_uri('/').rstrip('/')
                if entry_host and entry_host != local_host:
                    author_uuid = str(target.author.id).rstrip('/').split('/')[-1]
                    inbox_url = f"{entry_host}/api/authors/{author_uuid}/inbox/"
                    try:
                        requests.post(
                            inbox_url,
                            json=like_data,
                            headers={'Content-Type': 'application/json'},
                            auth=_get_auth_for_url(inbox_url),
                        )
                    except requests.RequestException:
                        pass

                broadcast_like_to_remotes(like_data)

                return Response(like_data, status=status.HTTP_201_CREATED)

            elif obj_type == 'comment':
                raw_url = payload.get('entry') or payload.get('object')
                entry_url = unquote(raw_url).rstrip('/')
                entry = Entry.objects.filter(id=entry_url).first()
                if entry is None:
                    parsed = urlparse(entry_url)
                    parts = parsed.path.strip('/').split('/')
                    try:
                        idx = parts.index('authors')
                        entry_author_id = parts[idx + 1]
                    except (ValueError, IndexError):
                        return Response({'detail': 'Invalid entry URL.'}, status=status.HTTP_400_BAD_REQUEST)

                    entry_author = self._get_or_create_author({'id': f'{parsed.scheme}://{parsed.netloc}/api/authors/{entry_author_id}/',
                                                           'displayName': entry_author_id},
                                                           default_host=f'{parsed.scheme}://{parsed.netloc}')
                    entry = Entry.objects.create(
                        id=entry_url,
                        author=entry_author,
                        title='Remote Entry',
                        content='',
                        visibility='PUBLIC'
                    )
                comment_author = self._get_or_create_author(payload.get('author', {})) or request.user
                comment_url = payload.get('id', '')
                comment_uuid = None
                if comment_url:
                    try:
                        comment_uuid = urlparse(comment_url).path.rstrip('/').split('/')[-1]
                    except Exception:
                        comment_uuid = None

                comment = Comment(
                    id=comment_url or None,
                    author=comment_author,
                    entry=entry,
                    comment=payload.get('comment', ''),
                    content_type=payload.get('contentType', 'text/plain'),
                )
                if comment_uuid:
                    try:
                        uuid.UUID(str(comment_uuid))
                        comment.uuid = comment_uuid
                    except ValueError:
                        pass

                comment.save()
                comment_data = CommentSerializer(comment, context={'request': request}).data
                broadcast_comment_to_remotes(comment_data)
                return Response(comment_data, status=status.HTTP_201_CREATED)

            else:
                obj = serializer.save()
        except IntegrityError:
            return Response(
                {'detail': f'{obj_type.capitalize()} already exists.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FeedPageView(TemplateView):
    """
    Renders the main feed page for logged-in users.

    Shows entries (posts) based on visibility rules:
    - User's own posts
    - Public posts
    - Friends-only or unlisted posts if applicable

    Template: feed.html
    """
    template_name = "feed.html"

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_authenticated:
            context['display_name'] = user.display_name
            context['username'] = user.username

            # Build base queryset
            entries = Entry.objects.all()
            entries = entries.exclude(visibility="DELETED")

            # Determine follower and friend relationships
            following_ids = set(
                FollowRequest.objects.filter(from_author=user, accepted=True)
                .values_list("to_author_id", flat=True)
            )
            follower_ids = set(
                FollowRequest.objects.filter(to_author=user, accepted=True)
                .values_list("from_author_id", flat=True)
            )
            friend_ids = following_ids.intersection(follower_ids)

            # Filter entries based on visibility rules
            entries = entries.filter(
                Q(author=user)
                | Q(visibility="PUBLIC")
                | Q(visibility="UNLISTED", author_id__in=following_ids)
                | Q(visibility="FRIENDS", author_id__in=friend_ids)
            ).order_by("-created_at")

            context['entries'] = entries

        else:
            context['display_name'] = "Guest"
            context['username'] = None
            context['entries'] = Entry.objects.filter(
                visibility="PUBLIC"
            ).exclude(visibility="DELETED").order_by("-created_at")
        return context

class WritePostPageView(TemplateView):
    """
    Renders the write-new-post page for a given author.

    Template: write_new_post.html
    """
    template_name = "write_new_post.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['author_id'] = kwargs['pk'] 
        return context
