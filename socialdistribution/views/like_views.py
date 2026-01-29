# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from socialdistribution.models import Entry, Author, Like
from socialdistribution.serializers import LikeSerializer
import requests
from django.conf import settings
from urllib.parse import unquote, urlparse

class LikeAPIView(APIView):
    """
    API endpoint for liking and retrieving likes on an entry.

    Methods:
    - GET: Retrieve all likes for a specific entry.
    - POST: Like a specific entry by the given author (only once).

    URL parameters:
    - author_id (UUID): The ID of the author performing the like.
    - entry_id (UUID): The ID of the entry being liked.
    """

    def get(self, request, author_id, entry_id):
        entry = get_object_or_404(Entry, id=entry_id)
        likes = Like.objects.filter(entry=entry)
        serializer = LikeSerializer(likes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, author_id, entry_id):
        entry = get_object_or_404(Entry, id=entry_id)
        author = get_object_or_404(Author, uuid=author_id)

        if Like.objects.filter(entry=entry, author=author).exists():
            return Response({"detail": "Already liked."}, status=status.HTTP_400_BAD_REQUEST)

        like = Like.objects.create(entry=entry, author=author)
        serializer = LikeSerializer(like)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class EntryLikesListAPIView(APIView):
    """
    GET /api/authors/{author_id}/entries/{entry_id}/likes/
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request, author_id, entry_id):

        author = get_object_or_404(Author, uuid=author_id)

        page = int(request.query_params.get('page', 1))
        size = int(request.query_params.get('size', 50))

        entry_id_str = str(entry_id)        
        decoded = unquote(entry_id_str)
        if decoded.startswith(('http://', 'https://')):

            remote_url = decoded.rstrip('/') + '/likes/'
            try:
                resp = requests.get(
                    remote_url,
                    params={'page': page, 'size': size},
                    headers={'Accept': 'application/json'}
                )
                return Response(resp.json(), status=resp.status_code)
            except requests.RequestException as e:
                return Response(
                    {'error': 'Failed to fetch remote likes', 'detail': str(e)},
                    status=status.HTTP_502_BAD_GATEWAY
                )

        entry = Entry.objects.filter(
            id__in=[
                decoded,
                f"{settings.BASE_URL.rstrip('/')}/api/authors/{author_id}/entries/{decoded}",
            ],
            author=author,
        ).first()

        if not entry:

            def _normalize(url: str) -> str:
                url = url.rstrip('/')
                return url[:-4] if url.endswith('/api') else url

            local_base = _normalize(request.build_absolute_uri('/'))
            author_host_raw = author.host.rstrip('/')
            author_host = _normalize(author_host_raw)

            if author_host and author_host != local_base:
                if author_host_raw.endswith('/api'):
                    remote_url = (
                        f"{author_host_raw}/authors/{author_id}/entries/{decoded}/likes/"
                    )
                else:
                    remote_url = (
                        f"{author_host_raw}/api/authors/{author_id}/entries/{decoded}/likes/"
                    )
                try:
                    resp = requests.get(
                        remote_url,
                        params={'page': page, 'size': size},
                        headers={'Accept': 'application/json'}
                    )
                    return Response(resp.json(), status=resp.status_code)
                except requests.RequestException as e:
                    return Response(
                        {'error': 'Failed to fetch remote likes', 'detail': str(e)},
                        status=status.HTTP_502_BAD_GATEWAY
                    )

            return Response({'detail': 'No Entry matches the given query.'}, status=status.HTTP_404_NOT_FOUND)

        qs = Like.objects.filter(entry=entry).order_by('-created_at') 
        total = qs.count()
        start = (page - 1) * size
        end = start + size
        page_qs = qs[start:end]

        serializer = LikeSerializer(page_qs, many=True, context={'request': request})

        base = request.build_absolute_uri(f'/api/authors/{author_id}/entries/{decoded}')
        likes_obj = {
            "type": "likes",
            "id": f"{base}/likes/",
            "web": request.build_absolute_uri(f'/authors/{author_id}/entries/{decoded}/'),
            "page_number": page,
            "size": size,
            "count": total,
            "src": serializer.data,
        }
        return Response(likes_obj, status=status.HTTP_200_OK)

class GlobalEntryLikesAPIView(APIView):
    """
    GET /api/entries/{entry_fqid}/likes/
      - LOCAL only
      return a "likes" object
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request, entry_fqid):

        decoded = unquote(entry_fqid)

        entry = get_object_or_404(Entry, id=decoded)

        page = int(request.query_params.get('page', 1))
        size = int(request.query_params.get('size', 50))

        qs = Like.objects.filter(entry=entry).order_by('-created_at')
        total = qs.count()
        start = (page - 1) * size
        end = start + size
        page_qs = qs[start:end]

        serializer = LikeSerializer(page_qs, many=True, context={'request': request})

        base_api = request.build_absolute_uri(f'/api/entries/{entry.id}')
        likes_obj = {
            "type": "likes",
            "id": f"{base_api}/likes/",
            "web": request.build_absolute_uri(f'/entries/{entry.id}/'),
            "page_number": page,
            "size": size,
            "count": total,
            "src": serializer.data,
        }
        return Response(likes_obj, status=status.HTTP_200_OK)

class AuthorLikedListAPIView(APIView):
    """
    GET /api/authors/{author_id}/liked/
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, author_id):

        author = get_object_or_404(Author, uuid=author_id)

        page = int(request.query_params.get('page', 1))
        size = int(request.query_params.get('size', 50))

        def _normalize(url: str) -> str:
            url = url.rstrip('/')
            return url[:-4] if url.endswith('/api') else url

        local_base = _normalize(request.build_absolute_uri('/'))
        author_base_raw = author.host.rstrip('/')
        author_base = _normalize(author_base_raw)

        if author_base != local_base:

            if author_base_raw.endswith('/api'):
                remote_url = f"{author_base_raw}/authors/{author.id}/liked/"
            else:
                remote_url = f"{author_base_raw}/api/authors/{author.id}/liked/"
            try:
                resp = requests.get(
                    remote_url,
                    params={'page': page, 'size': size},
                    headers={'Accept': 'application/json'}
                )
                return Response(resp.json(), status=resp.status_code)
            except requests.RequestException as e:
                return Response(
                    {'error': 'Failed to fetch remote liked', 'detail': str(e)},
                    status=status.HTTP_502_BAD_GATEWAY
                )

        qs = Like.objects.filter(author=author).order_by('-created_at')
        total = qs.count()
        start, end = (page - 1) * size, page * size
        page_qs = qs[start:end]

        serializer = LikeSerializer(page_qs, many=True, context={'request': request})

        base_api = request.build_absolute_uri(f'/api/authors/{author_id}')
        likes_obj = {
            "type": "likes",
            "id": f"{base_api}/liked/",
            "web": request.build_absolute_uri(f'/authors/{author_id}/liked/'),
            "page_number": page,
            "size": size,
            "count": total,
            "src": serializer.data,
        }
        return Response(likes_obj, status=status.HTTP_200_OK)

class AuthorLikeDetailAPIView(APIView):
    """
    GET /api/authors/{author_id}/liked/{like_id}/
      - LOCAL: return a single Like object for the given author and like IDs
      - REMOTE: proxy request to remote node based on author.host
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, author_id, like_id):
        # Fetch the author to determine local vs remote
        author = get_object_or_404(Author, uuid=author_id)
        def _normalize(url: str) -> str:
            url = url.rstrip('/')
            return url[:-4] if url.endswith('/api') else url

        local_base = _normalize(request.build_absolute_uri('/'))
        author_host_raw = author.host.rstrip('/')
        author_host = _normalize(author_host_raw)

        # Remote proxy if host differs
        if author_host and author_host != local_base:
            if author_host_raw.endswith('/api'):
                remote_url = f"{author_host_raw}/authors/{author_id}/liked/{like_id}/"
            else:
                remote_url = f"{author_host_raw}/api/authors/{author_id}/liked/{like_id}/"
            try:
                resp = requests.get(remote_url, headers={'Accept': 'application/json'})
                return Response(resp.json(), status=resp.status_code)
            except requests.RequestException as e:
                return Response(
                    {'error': 'Failed to fetch remote like', 'detail': str(e)},
                    status=status.HTTP_502_BAD_GATEWAY
                )

        # Local retrieval
        like = get_object_or_404(Like, uuid=like_id, author=author)
        serializer = LikeSerializer(like, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

class GlobalAuthorLikedListAPIView(APIView):
    """
    GET /api/authors/{author_fqid}/liked/
      - LOCAL only
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, author_fqid):

        decoded = unquote(author_fqid)

        path = urlparse(decoded).path.rstrip('/')
        parts = [seg for seg in path.split('/') if seg]
        try:
            idx = parts.index('authors')
            author_id = parts[idx + 1]
        except (ValueError, IndexError):
            return Response(
                {'detail': 'Invalid author FQID.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        qs = Like.objects.filter(author__uuid=author_id).order_by('-created_at')
        total = qs.count()

        page = int(request.query_params.get('page', 1))
        size = int(request.query_params.get('size', 50))
        start, end = (page - 1) * size, page * size
        page_qs = qs[start:end]

        serializer = LikeSerializer(page_qs, many=True, context={'request': request})

        base_api = request.build_absolute_uri(f'/api/authors/{author_id}')
        likes_obj = {
            "type": "likes",
            "id": f"{base_api}/liked/",
            "web": request.build_absolute_uri(f'/authors/{author_id}/liked/'),
            "page_number": page,
            "size": size,
            "count": total,
            "src": serializer.data,
        }
        return Response(likes_obj, status=status.HTTP_200_OK)

class GlobalLikeDetailAPIView(APIView):
    """
    GET /api/liked/{like_fqid}/
      - LOCAL only: return a single Like object for the given like FQID
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, like_fqid):

        decoded = unquote(like_fqid)

        path = urlparse(decoded).path.rstrip('/')
        parts = [seg for seg in path.split('/') if seg]
        try:
            idx = parts.index('liked')
            like_id = parts[idx + 1]
        except (ValueError, IndexError):
            return Response({'detail': 'Invalid like FQID.'}, status=status.HTTP_400_BAD_REQUEST)
        # Fetch the local Like object
        like = get_object_or_404(Like, uuid=like_id)
        serializer = LikeSerializer(like, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)