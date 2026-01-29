# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from socialdistribution.models import Comment, Entry, Author
from socialdistribution.serializers import CommentSerializer
from django.shortcuts import get_object_or_404
from urllib.parse import unquote, urlparse
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from socialdistribution.utils import broadcast_comment_to_remotes, _get_auth_for_url
import requests
from django.conf import settings

class CommentAPIView(APIView):
    """
    API endpoint to retrieve or create comments for an entry.

    URL params:
      - author_uuid: UUID of the entry's author
      - entry_uuid: UUID of the entry
      - comment_uuid: (optional) UUID of a specific comment
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, author_uuid, entry_uuid, comment_uuid=None):
        # Retrieve a single comment
        if comment_uuid:
            comment = get_object_or_404(
                Comment,
                uuid=comment_uuid,
                entry__id__in=[
                    entry_uuid,
                    f"{settings.BASE_URL.rstrip('/')}/api/authors/{author_uuid}/entries/{entry_uuid}"
                ],
                entry__author__uuid=author_uuid
            )
            serializer = CommentSerializer(comment, context={'request': request})
            return Response(serializer.data)

        # Retrieve list of comments for the entry
        qs = Comment.objects.filter(
            entry__id__in=[
                entry_uuid,
                f"{settings.BASE_URL.rstrip('/')}/api/authors/{author_uuid}/entries/{entry_uuid}"
            ],
            entry__author__uuid=author_uuid
        ).order_by('-created_at')
        serializer = CommentSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request, author_uuid, entry_uuid, comment_uuid=None):
        """Create a new comment on the given entry."""

        # Disallow POSTing to a specific comment URL
        if comment_uuid is not None:
            return Response(
                {"detail": "Cannot POST to a specific comment."},
                status=status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        # Validate entry existence (allow both UUID and full URL)
        candidate_ids = [
            entry_uuid,
            f"{settings.BASE_URL.rstrip('/')}/api/authors/{author_uuid}/entries/{entry_uuid}",
        ]
        entry = get_object_or_404(Entry, id__in=candidate_ids, author__uuid=author_uuid)

        data = request.data or {}
        text = data.get("comment") or data.get("content")
        if not text:
            return Response(
                {"detail": "Missing comment text."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        content_type = data.get("contentType", "text/plain")

        comment = Comment.objects.create(
            author=request.user,
            entry=entry,
            comment=text,
            content_type=content_type,
        )

        serializer = CommentSerializer(comment, context={"request": request})

        # Broadcast to any configured remote nodes
        broadcast_comment_to_remotes(serializer.data)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

class CommentsListAPIView(APIView):
    """
    GET /api/authors/{author_id}/entries/{entry_id}/comments/
      - LOCAL: entry_id is UUID, return comments object
      - REMOTE: entry_id is percent-encoded URL
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, author_id, entry_id):
        decoded = unquote(str(entry_id)).rstrip('/')

        author = get_object_or_404(Author, uuid=author_id)
        if decoded.startswith('http'):
            lookup_id = decoded
        else:
            host = author.host.rstrip('/')
            lookup_id = f"{host}/authors/{author_id}/entries/{decoded}"

        entry = Entry.objects.filter(id=lookup_id, author__uuid=author_id).first()
        if entry is None:
            parsed = urlparse(lookup_id)

            if parsed.scheme in ('http', 'https'):
                base_netloc = urlparse(settings.BASE_URL).netloc
                if parsed.netloc and parsed.netloc != base_netloc:
                    remote_url = lookup_id.rstrip('/') + '/comments/'
                    try:
                        resp = requests.get(remote_url, headers={'Accept': 'application/json'})
                        data = resp.json()
                    except (requests.RequestException, ValueError) as e:
                        return Response(
                            {'error': 'Failed to fetch remote comments', 'detail': str(e)},
                            status=status.HTTP_502_BAD_GATEWAY,
                        )
                    return Response(data, status=resp.status_code)

            entry = get_object_or_404(Entry, id=lookup_id, author__uuid=author_id)

        page = int(request.query_params.get('page', 1))
        qs = Comment.objects.filter(entry=entry).order_by('-created_at')
        total = qs.count()
        size = int(request.query_params.get('size', total))
        start = (page - 1) * size
        end = start + size
        page_qs = qs[start:end]

        serializer = CommentSerializer(page_qs, many=True, context={'request': request})

        base_api = request.build_absolute_uri(f'/api/authors/{author_id}/entries/{decoded}')
        comments_obj = {
            "type": "comments",
            "id": request.build_absolute_uri(f'/api/authors/{author_id}/entries/{decoded}/comments/'),
            "web": request.build_absolute_uri(f'/authors/{author_id}/entries/{decoded}/'),
            "page_number": page,
            "size": size,
            "count": total,
            "src": serializer.data,
        }
        return Response(comments_obj, status=status.HTTP_200_OK)

class GlobalEntryCommentsAPIView(APIView):
    """
    GET /api/entries/{entry_fqid}/comments/
      - LOCAL: entry_fqid is UUID
      - REMOTE: entry_fqid is percent-encoded URL
    Return a "comments" object
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, entry_fqid):
        decoded = unquote(entry_fqid).rstrip('/')

        parsed = urlparse(decoded)
        if parsed.scheme in ("http", "https"):
            base_netloc = urlparse(settings.BASE_URL).netloc
            if parsed.netloc and parsed.netloc != base_netloc:
                urls_to_try = [
                    decoded + '/comments',
                    decoded + '/comments/' 
                ]
                last_exception = None

                for url in urls_to_try:
                    try:
                        auth = _get_auth_for_url(url)
                        resp = requests.get(url, headers={'Accept': 'application/json'}, auth=auth)
                        resp.raise_for_status() 
                        data = resp.json()
                        return Response(data, status=resp.status_code)
                    except (requests.RequestException, ValueError) as e:
                        last_exception = e
                        continue

                return Response(
                    {'error': 'Failed to fetch remote comments', 'detail': str(last_exception)},
                    status=status.HTTP_502_BAD_GATEWAY
                )

        entry = get_object_or_404(Entry, id=decoded)

        page = int(request.query_params.get('page', 1))
        qs = Comment.objects.filter(entry=entry).order_by('-created_at')
        total = qs.count()
        size = int(request.query_params.get('size', total))
        start = (page - 1) * size
        end = start + size
        page_qs = qs[start:end]

        serializer = CommentSerializer(page_qs, many=True, context={'request': request})

        comments_obj = {
            "type": "comments",
            "id": request.build_absolute_uri(f'/api/entries/{entry.id}/comments/'),
            "web": request.build_absolute_uri(f'/entries/{entry.id}/'),
            "page_number": page,
            "size": size,
            "count": total,
            "src": serializer.data,
        }
        return Response(comments_obj, status=status.HTTP_200_OK)

class EntryCommentDetailAPIView(APIView):
    """
    GET /api/authors/{author_id}/entries/{entry_id}/comment/{comment_fqid}/
      — LOCAL: get the local Comment and Return
      — REMOTE: send to remote Comment API
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, author_id, entry_id, comment_fqid):
        decoded = unquote(comment_fqid)

        local_prefix = settings.BASE_URL.rstrip('/')
        if decoded.startswith(local_prefix):

            path = urlparse(decoded).path.rstrip('/')
            comment_id = path.split('/')[-1]

            comment = get_object_or_404(
                Comment,
                uuid=comment_id,
                entry__id__in=[
                    entry_id,
                    f"{settings.BASE_URL.rstrip('/')}/api/authors/{author_id}/entries/{entry_id}"
                ],
                entry__author__uuid=author_id
            )
            serializer = CommentSerializer(comment, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        try:
            resp = requests.get(decoded, headers={'Accept': 'application/json'})
            data = resp.json()
            return Response(data, status=resp.status_code)
        except (requests.RequestException, ValueError) as e:
            return Response(
                {'error': 'Failed to fetch remote comment', 'detail': str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

class AuthorCommentListAPIView(APIView):
    """
    GET /api/authors/{author_fqid}/commented/
    local node: return all comments of a author commented on this node
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, author_fqid):

        decoded = unquote(author_fqid)

        path = urlparse(decoded).path.rstrip('/')
        parts = path.split('/')
        try:
            idx = parts.index('authors')
            author_id = parts[idx + 1]
        except (ValueError, IndexError):
            return Response(
                {'detail': 'Invalid author FQID.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        author = get_object_or_404(Author, uuid=author_id)

        comments_qs = Comment.objects.filter(author=author).order_by('-created_at')
        serializer = CommentSerializer(comments_qs, many=True, context={'request': request})

        return Response(serializer.data, status=status.HTTP_200_OK)

class GlobalCommentDetailAPIView(APIView):
    """
    GET /api/commented/{comment_fqid}/
      — LOCAL: get local Comment, and return its JSON
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request, comment_fqid):
        decoded = unquote(comment_fqid)

        path = urlparse(decoded).path.rstrip('/')
        segments = path.split('/')
        if not segments or segments[-2] != 'commented':
            return Response({'detail': 'Invalid comment FQID.'},
                            status=status.HTTP_400_BAD_REQUEST)
        comment_id = segments[-1]

        comment = get_object_or_404(Comment, uuid=comment_id)

        serializer = CommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class CommentLikesListAPIView(APIView):
    """
    GET /api/authors/{author_id}/entries/{entry_id}/comments/{comment_fqid}/likes/
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, author_id, entry_id, comment_fqid):

        decoded = unquote(comment_fqid)

        local_base = request.build_absolute_uri('/').rstrip('/')
        if not decoded.startswith('http'):
            comment_id = decoded
        elif decoded.startswith(local_base):

            path = urlparse(decoded).path.rstrip('/')
            comment_id = path.split('/')[-1]

        else:
            remote_url = decoded.rstrip('/') + '/likes/'
            try:
                resp = requests.get(remote_url, headers={'Accept': 'application/json'})
                data = resp.json()
                return Response(data, status=resp.status_code)
            except (requests.RequestException, ValueError) as e:
                return Response(
                    {'error': 'Failed to fetch remote comment likes', 'detail': str(e)},
                    status=status.HTTP_502_BAD_GATEWAY
                )

        comment = get_object_or_404(
            Comment,
            uuid=comment_id,
            entry__id__in=[
                entry_id,
                f"{settings.BASE_URL.rstrip('/')}/api/authors/{author_id}/entries/{entry_id}"
            ],
            entry__author__uuid=author_id
        )

        serializer = CommentSerializer(comment, context={'request': request})
        likes_obj = serializer.get_likes(comment)
        return Response(likes_obj, status=status.HTTP_200_OK)

class AuthorCommentDetailAPIView(APIView):
    """
    GET /api/authors/{author_id}/commented/{comment_id}/
      - LOCAL: return a single Comment object made by the author on any entry
      - REMOTE: proxy to {author.host}/api/authors/{author_id}/commented/{comment_id}/
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request, author_id, comment_id):
        # Retrieve the author to determine local vs remote
        author = get_object_or_404(Author, uuid=author_id)
        # Base URLs without trailing slash

        local_comment = Comment.objects.filter(uuid=comment_id, author__uuid=author_id).first()
        if local_comment is not None:
            serializer = CommentSerializer(local_comment, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Proxy to remote host if this author belongs to another node
        req_netloc = urlparse(request.build_absolute_uri()).netloc
        author_url = author.host.rstrip('/')
        if author_url.endswith('/api'):
            author_url = author_url[:-4]
        author_netloc = urlparse(author_url).netloc

        if author_url and author_netloc and author_netloc not in (req_netloc, 'localhost', '127.0.0.1'):

            # build the exact same path the client requested
            remote_url = f"{author_url}{request.path}"
            try:
                resp = requests.get(
                    remote_url,
                    headers={'Accept': 'application/json'},
                    timeout=5
                )
                resp.raise_for_status()
                return Response(resp.json(), status=resp.status_code)

            except requests.RequestException as e:
                return Response(
                    {'error': 'Failed to fetch remote comment', 'detail': str(e)},
                    status=status.HTTP_502_BAD_GATEWAY
                )


        return Response({'detail': 'No Comment matches the given query.'}, status=status.HTTP_404_NOT_FOUND)

class AuthorCommentListCreateAPIView(APIView):
    """
    GET    /api/authors/{author_id}/commented/   — list comments by author (local & remote)
    POST   /api/authors/{author_id}/commented/   — create a new comment (local)
    """
    permission_classes = [IsAuthenticated]

    def get_authenticators(self):
        if self.request.method == 'GET':
            return [SessionAuthentication(), BasicAuthentication()]
        return [SessionAuthentication()]


    def get(self, request, author_id):
        # Determine author
        # parse percent-encoded or UUID
        from urllib.parse import urlparse
        fqid = author_id
        fqid_str = str(fqid)            
        decoded = unquote(fqid_str)
        # extract id if needed
        if decoded.startswith('http://') or decoded.startswith('https://'):
            # remote: proxy GET to author's host
            # Only public/unlisted entries
            # simply forward
            remote_url = decoded.rstrip('/') + '/commented/'
            try:
                resp = requests.get(remote_url, params=request.query_params, headers={'Accept': 'application/json'})
                data = resp.json()
                return Response(data, status=resp.status_code)
            except (requests.RequestException, ValueError) as e:
                return Response({'error': 'Failed to fetch remote comments', 'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        else:
            # local: list comments on any entry
            author = get_object_or_404(Author, uuid=decoded)
            qs = Comment.objects.filter(author=author).order_by('-created_at')
            # pagination
            page = int(request.query_params.get('page', 1))
            size = int(request.query_params.get('size', 5))
            start = (page - 1) * size
            end = start + size
            total = qs.count()
            page_qs = qs[start:end]

            serializer = CommentSerializer(page_qs, many=True, context={'request': request})
            base = request.build_absolute_uri(f'/api/authors/{author.id}/commented')
            comments_obj = {
                'type': 'comments',
                'id': f'{base}/',
                'page_number': page,
                'size': size,
                'count': total,
                'src': serializer.data,
            }
            return Response(comments_obj)

    def post(self, request, author_id):
        # Only local: create comment
        author = request.user
        # validate type
        data = request.data
        if data.get('type') != 'comment':
            return Response({'error': 'Invalid type, must be "comment".'}, status=status.HTTP_400_BAD_REQUEST)
        entry_url = data.get('entry')
        if not entry_url:
            return Response({'error': 'Missing entry field.'}, status=status.HTTP_400_BAD_REQUEST)
        # resolve entry local
        # assume entry_url is full URL or percent-encoded
        from urllib.parse import urlparse, unquote
        decoded_entry = unquote(entry_url)
        # extract entry id
        path = urlparse(decoded_entry).path.rstrip('/')
        entry_id = path.split('/')[-1]
        entry = get_object_or_404(Entry, id=entry_id)
        # create comment
        comment = Comment.objects.create(
            author=author,
            entry=entry,
            comment=data.get('comment',''),
            content_type=data.get('contentType','text/plain')
        )
        serializer = CommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
