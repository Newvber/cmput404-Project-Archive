# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework.decorators import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions    import IsAuthenticated
from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from socialdistribution.models import Author, FollowRequest, Entry, Comment
from django.http import HttpResponse, Http404
import base64
import imghdr
from django.urls import reverse
from socialdistribution.serializers import EntryDetailSerializer
from urllib.parse import unquote, urlparse
from socialdistribution.utils import (
    broadcast_entry_to_remotes,
    broadcast_delete_to_remotes,
    broadcast_unlisted_entry_to_followers,
    broadcast_entry_to_friends,
)
from django.shortcuts import redirect

class EntryDetailPageView(TemplateView):
    """
    Renders the detail page for a specific entry, including the comments.

    Template: entry_detail.html

    URL parameters:
        - entry_id (UUID): The ID of the entry to display.
        - author_id (UUID): The ID of the entry's author.

    Context:
        - entry: The Entry object being viewed.
        - comments: A queryset of Comment objects associated with the entry, ordered by creation time (newest first).
    """

    template_name = "entry_detail.html"

    def dispatch(self, request, *args, **kwargs):
        entry_id = unquote(self.kwargs["entry_id"])
        raw_author = self.kwargs["author_id"]
        decoded_author = unquote(str(raw_author)).rstrip("/")

        author_uuid = None
        author_fqid = None

        if str(entry_id).startswith("http"):
            parsed = urlparse(entry_id)
            parts = [p for p in parsed.path.rstrip("/").split("/") if p]
            try:
                idx = parts.index("authors")
                author_uuid = parts[idx + 1]
                author_fqid = f"{parsed.scheme}://{parsed.netloc}/api/authors/{author_uuid}"
            except (ValueError, IndexError):
                author_uuid = None

        if author_uuid is None:
            if decoded_author.startswith("http"):
                author_fqid = decoded_author
                author_uuid = urlparse(decoded_author).path.rstrip("/").split("/")[-1]
            else:
                author_uuid = decoded_author
                author_fqid = f"{settings.BASE_URL}/api/authors/{author_uuid}"

        full_id = f"{settings.BASE_URL}/api/authors/{author_uuid}/entries/{entry_id}"
        lookup_id = entry_id if str(entry_id).startswith("http") else full_id

        entry = get_object_or_404(Entry, id=lookup_id)

        if author_uuid and str(entry.author.uuid) != str(author_uuid):
            raise Http404("Entry does not belong to the specified author")

        # Visibility Restriction: Friends Only
        if entry.visibility == "FRIENDS":
            viewer = request.user

             # Not logged in? Redirect to feed.
            if not viewer.is_authenticated:
                return redirect("feed_page")
            
            # Logged-in user is not the author → check if mutual follow exists
            if viewer != entry.author:
                following_ids = set(
                    FollowRequest.objects.filter(from_author=viewer, accepted=True)
                    .values_list("to_author_id", flat=True)
                )
                follower_ids = set(
                    FollowRequest.objects.filter(to_author=viewer, accepted=True)
                    .values_list("from_author_id", flat=True)
                )
                friend_ids = following_ids.intersection(follower_ids)

                if entry.author_id not in friend_ids:
                    return redirect("feed_page")

        # Save entry for use in context
        self.entry = entry
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        comments = Comment.objects.filter(entry=self.entry).select_related("author").order_by("-created_at")
        context.update({"entry": self.entry, "comments": comments})

        # Set back button link
        referer = self.request.META.get("HTTP_REFERER")
        back_url = reverse("feed_page")

        if referer:
            path = urlparse(referer).path
            author_id = self.kwargs.get("author_id")
            profile_path = reverse("profile_page", args=[str(author_id)])
            if path.startswith(profile_path):
                back_url = profile_path

        context["back_url"] = back_url
        return context
    
class EditEntryPageView(TemplateView):
    """Render a page to edit an existing entry."""

    template_name = "edit_entry.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entry_id = unquote(self.kwargs["entry_id"])
        raw_author = self.kwargs["author_id"]

        # Convert the provided author UUID into the stored fully qualified ID
        author_uuid = unquote(str(raw_author)).rstrip("/")
        author_fqid = f"{settings.BASE_URL}/api/authors/{author_uuid}"

        # If the entry_id is not a full URL, build the fully qualified ID
        full_entry_id = (
            entry_id
            if str(entry_id).startswith("http")
            else f"{settings.BASE_URL}/api/authors/{author_uuid}/entries/{entry_id}"
        )

        entry = get_object_or_404(Entry, id=full_entry_id, author_id=author_fqid)
        context["entry"] = entry
        return context

class EntryAPIView(APIView):
    """
    API endpoint to manage posts (entries) by a given author.

    Methods:
    - GET to list all visible entries
    - GET to retrieve entry detail
    - POST to create new entry
    - PUT to edit entry
    - DELETE to soft delete entry

    Visibility rules are enforced for unauthenticated or non-owner users.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_authenticators(self):
        if self.request.method == 'GET':
            return [SessionAuthentication(), BasicAuthentication()]
        return [SessionAuthentication()]

    def get(self, request, author_id, entry_id=None):
        # GET /api/authors/<author_id>/entries/ → list
        if entry_id is not None:
            entry_id = str(entry_id)

        if entry_id is None:
            viewer = request.user
            author = get_object_or_404(Author, uuid=author_id)

            entries = Entry.objects.filter(author=author)

            if not viewer.is_staff:
                entries = entries.exclude(visibility="DELETED")

                if viewer != author:
                    following_ids = set(
                        FollowRequest.objects.filter(from_author=viewer, accepted=True)
                        .values_list("to_author_id", flat=True)
                    ) if viewer.is_authenticated else set()
                    follower_ids = set(
                        FollowRequest.objects.filter(to_author=viewer, accepted=True)
                        .values_list("from_author_id", flat=True)
                    ) if viewer.is_authenticated else set()
                    friend_ids = following_ids.intersection(follower_ids)

                    if author.id in friend_ids:
                        pass
                    elif author.id in following_ids:
                        entries = entries.filter(visibility__in=["PUBLIC", "UNLISTED"])
                    elif viewer.is_authenticated:
                        entries = entries.filter(visibility="PUBLIC")
                    else:
                        entries = entries.filter(visibility="PUBLIC")
                else:
                    pass

            entries = entries.order_by("-created_at")

            page = int(request.query_params.get("page", 1))
            size = int(request.query_params.get("size", 5))
            total = entries.count()
            start, end = (page - 1) * size, page * size
            page_qs = entries[start:end]

            serializer = EntryDetailSerializer(page_qs, many=True, context={"request": request})

            entries_obj = {
                "type": "entries",
                "id": request.build_absolute_uri(),
                "page_number": page,
                "size": size,
                "count": total,
                "src": serializer.data,
            }
            return Response(entries_obj, status=status.HTTP_200_OK)
        
        # GET /api/authors/<author_id>/entries/<entry_id>/ → detail
        author_obj = get_object_or_404(Author, uuid=author_id)
        author_host = author_obj.host.rstrip('/')
        host = author_host if author_host.endswith('/api') else f"{author_host}/api"
        decoded_id = unquote(str(entry_id))
        uuid_str = decoded_id.rstrip('/').split('/')[-1]
        full_id = f"{host}/authors/{author_obj.uuid}/entries/{uuid_str}"
        lookup_id = entry_id if str(entry_id).startswith('http') else full_id
        entry = get_object_or_404(Entry, id=lookup_id)
        viewer = request.user
        if entry.visibility == "DELETED" and not viewer.is_staff:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if not (viewer.is_staff or viewer == entry.author):
            following_ids = set(
                FollowRequest.objects.filter(from_author=viewer, accepted=True)
                .values_list("to_author_id", flat=True)
            ) if viewer.is_authenticated else set()
            follower_ids = set(
                FollowRequest.objects.filter(to_author=viewer, accepted=True)
                .values_list("from_author_id", flat=True)
            ) if viewer.is_authenticated else set()
            friend_ids = following_ids.intersection(follower_ids)

            allowed = (
                entry.visibility == "PUBLIC"
                or entry.visibility == "UNLISTED" 
                or (entry.visibility == "FRIENDS" and entry.author_id in friend_ids)
            )
            if not allowed:
                return Response(status=status.HTTP_403_FORBIDDEN)
   
        serializer = EntryDetailSerializer(entry)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, author_id, entry_id=None):

        if entry_id is not None:
            return Response(
                {"detail": 'Method "POST" not allowed on detail endpoint.'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        author = get_object_or_404(Author, uuid=author_id)

        # serializer = EntryDetailSerializer(data=request.data)
        payload_id = request.data.get("id")
        entry = None
        entry_uuid = None

        if payload_id:
            entry_uuid = str(payload_id).rstrip('/').split('/')[-1]
            entry = Entry.objects.filter(id=entry_uuid).first()
        
        if entry is not None:
            serializer = EntryDetailSerializer(entry, data=request.data, partial=True)
            status_code = status.HTTP_200_OK
        else:
            data = dict(request.data)
            if entry_uuid:
                data["id"] = entry_uuid
            serializer = EntryDetailSerializer(data=data)
            status_code = status.HTTP_201_CREATED

        if serializer.is_valid():
            saved_entry = serializer.save(author=author)
            data = EntryDetailSerializer(saved_entry, context={'request': request}).data
            visibility = data.get('visibility')
            if visibility == 'PUBLIC':
                broadcast_entry_to_remotes(data)
            elif visibility == 'UNLISTED':
                broadcast_unlisted_entry_to_followers(data)
            elif visibility == 'FRIENDS':
                broadcast_entry_to_friends(data)
            return Response(data, status=status_code)
            # serializer.save(author=author)
            # return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, author_id, entry_id=None):
        if entry_id is None:
            return Response(
                {"detail": 'Method "PUT" not allowed on detail endpoint.'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        author_obj = get_object_or_404(Author, uuid=author_id)
        author_host = author_obj.host.rstrip('/')
        host = author_host if author_host.endswith('/api') else f"{author_host}/api"
        decoded_id = unquote(str(entry_id))
        uuid_str = decoded_id.rstrip('/').split('/')[-1]
        full_id = f"{host}/authors/{author_obj.uuid}/entries/{uuid_str}"
        lookup_id = entry_id if str(entry_id).startswith('http') else full_id
        entry = get_object_or_404(Entry, id=lookup_id)

        if entry.visibility == "DELETED" and not request.user.is_staff:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if request.user != entry.author:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = EntryDetailSerializer(entry, data=request.data, partial=True)
        if serializer.is_valid():
            saved_entry = serializer.save()
            data = EntryDetailSerializer(saved_entry, context={'request': request}).data
            visibility = data.get('visibility')
            if visibility == 'PUBLIC':
                broadcast_entry_to_remotes(data)
            elif visibility == 'UNLISTED':
                broadcast_unlisted_entry_to_followers(data)
            elif visibility == 'FRIENDS':
                broadcast_entry_to_friends(data)
            return Response(data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, author_id, entry_id=None):
        if entry_id is None:
            return Response(
                {"detail": 'Method "DELETE" not allowed on detail endpoint.'},
                status=status.HTTP_405_METHOD_NOT_ALLOWED
            )

        # DELETE /api/authors/<author_id>/entries/<entry_id>/
        full_id = f"{settings.BASE_URL}/api/authors/{author_id}/entries/{entry_id}"
        lookup_id = entry_id if str(entry_id).startswith('http') else full_id
        entry = get_object_or_404(Entry, id=lookup_id)

        if request.user != entry.author:
            return Response({"detail": "Forbidden"}, status=status.HTTP_403_FORBIDDEN)

        serializer = EntryDetailSerializer(entry, data={"visibility": "DELETED"}, partial=True)
        if serializer.is_valid():
            saved_entry = serializer.save()
            data = EntryDetailSerializer(saved_entry, context={'request': request}).data
            broadcast_delete_to_remotes(data)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EntryImageAPIView(APIView):
    """Return a public image entry as binary data."""

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [permissions.AllowAny]

    def get(self, request, author_id=None, entry_id=None, entry_fqid=None):
        if entry_fqid is not None:
            # /api/entries/<entry_fqid>/image/
            entry_id = entry_fqid
            author_id = None
        elif entry_id is None:
            entry_id = author_id
            author_id = None

        decoded_id = unquote(str(entry_id))
        lookup_id = decoded_id
        uuid_str = decoded_id.rstrip('/').split('/')[-1]
        if not decoded_id.startswith('http'):
            if author_id is None:
                return Response(status=status.HTTP_400_BAD_REQUEST)
            try:
                author_obj = Author.objects.get(uuid=author_id)
            except Author.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

            host = author_obj.host.rstrip('/')
            lookup_id = f"{host}/authors/{author_id}/entries/{uuid_str}"


        entry = get_object_or_404(Entry, id=lookup_id)

        if author_id and str(entry.author.uuid) != str(author_id):
            return Response(status=status.HTTP_404_NOT_FOUND)

        if entry.visibility == "DELETED":
            return Response(status=status.HTTP_404_NOT_FOUND)

        viewer = request.user
        if entry.visibility == "FRIENDS":
            if not viewer.is_authenticated:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
            following_ids = set(
                FollowRequest.objects.filter(from_author=viewer, accepted=True)
                .values_list("to_author_id", flat=True)
            )
            follower_ids = set(
                FollowRequest.objects.filter(to_author=viewer, accepted=True)
                .values_list("from_author_id", flat=True)
            )
            friend_ids = following_ids.intersection(follower_ids)
            if viewer != entry.author and entry.author_id not in friend_ids and not viewer.is_staff:
                return Response(status=status.HTTP_403_FORBIDDEN)
        elif entry.visibility not in ("PUBLIC", "UNLISTED"):
            if not (viewer.is_staff or viewer == entry.author):
                return Response(status=status.HTTP_403_FORBIDDEN)

        if not (
            entry.contentType.startswith("image/") and entry.contentType.endswith(";base64")
            or entry.contentType == "application/base64"
        ):
            return Response(status=status.HTTP_404_NOT_FOUND)

        try:
            data = base64.b64decode(entry.content)
        except Exception:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if entry.contentType == "application/base64":
            kind = imghdr.what(None, data)
            if kind:
                mime = f"image/{kind}"
            else:
                mime = "application/octet-stream"
        else:
            mime = entry.contentType.replace(";base64", "")

        return HttpResponse(data, content_type=mime)

class GlobalEntryDetailAPIView(APIView):
    """Return a single entry referenced by its FQID."""

    authentication_classes = [SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, entry_fqid):
        decoded = unquote(entry_fqid)

        path = urlparse(decoded).path.rstrip('/')
        parts = [seg for seg in path.split('/') if seg]
        try:
            idx_authors = parts.index('authors')
            _ = parts[idx_authors + 1]
            idx_entries = parts.index('entries', idx_authors + 2)
            _ = parts[idx_entries + 1]
        except (ValueError, IndexError):
            return Response({'detail': 'Invalid entry FQID.'}, status=status.HTTP_400_BAD_REQUEST)

        entry = get_object_or_404(Entry, id=decoded)

        if entry.visibility == "DELETED":
            return Response(status=status.HTTP_404_NOT_FOUND)

        viewer = request.user

        if entry.visibility == 'FRIENDS':
            if not viewer.is_authenticated:
                return Response(status=status.HTTP_401_UNAUTHORIZED)
            following_ids = set(
                FollowRequest.objects.filter(from_author=viewer, accepted=True)
                .values_list('to_author_id', flat=True)
            )
            follower_ids = set(
                FollowRequest.objects.filter(to_author=viewer, accepted=True)
                .values_list('from_author_id', flat=True)
            )
            friend_ids = following_ids.intersection(follower_ids)
            if viewer != entry.author and entry.author_id not in friend_ids and not viewer.is_staff:
                return Response(status=status.HTTP_403_FORBIDDEN)
        elif entry.visibility not in ('PUBLIC', 'UNLISTED'):
            if not (viewer.is_staff or viewer == entry.author):
                return Response(status=status.HTTP_403_FORBIDDEN)

        serializer = EntryDetailSerializer(entry, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
