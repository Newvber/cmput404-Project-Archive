# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from socialdistribution.models import Author, FollowRequest
from socialdistribution.serializers import FollowRequestSerializer, AuthorSerializer
from rest_framework.views import APIView
from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404, render
from urllib.parse import unquote, urlparse
import requests
from django.conf import settings
from socialdistribution.utils import (
    send_unlisted_entries_to_follower,
    send_friends_entries_to_friend,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect

class FollowManagerAPIView(APIView):
    """
        API endpoint for managing follow requests.

        Methods:
        - POST: Send a follow request from one user to another.
        - PATCH: Accept a pending follow request.
        - DELETE: Reject or cancel a follow request.
        - GET: Retrieve incoming follow requests for a given user.

        Parameters:
        - author (UUID): Required. The ID of the author receiving follow requests.
        - status (optional): 'pending' or 'accepted' to filter request status.
    """
    def patch(self, request):
        from_id = request.data.get("from_author")
        to_id = request.data.get("to_author")

        # Look up the follow request from DB; return 404 if it doesn't exist
        follow_request = get_object_or_404(FollowRequest, from_author_id = from_id, to_author_id = to_id)

        # Mark the request as accepted and no longer pending
        follow_request.accepted = True
        follow_request.pending = False
        follow_request.save()

        follower = follow_request.from_author
        local_host = settings.BASE_URL.rstrip('/') + '/api'
        follower_netloc = urlparse(follower.host.rstrip('/')).netloc
        local_netloc = urlparse(local_host.rstrip('/')).netloc
        if follower_netloc != local_netloc:
            send_unlisted_entries_to_follower(follow_request.to_author, follower)
            if FollowRequest.objects.filter(
                from_author=follow_request.to_author,
                to_author=follower,
                accepted=True
            ).exists():
                send_friends_entries_to_friend(follow_request.to_author, follower)

        return Response(FollowRequestSerializer(follow_request).data)

    # used when user 2 wants to reject request from user 1
    def delete(self, request):
        from_id = request.data.get("from_author")
        to_id = request.data.get("to_author")

        follow_request = FollowRequest.objects.filter(from_author_id = from_id, to_author_id = to_id).first()

        if follow_request:
            follow_request.delete()
            return Response(status = 204)
        
        return Response({"detail": "Not found."}, status = 404)
    
    # localhost:8000/api/follow/?author=uuid to get all the INCOMING follow requests involving the user
    # localhost:8000/api/follow/?author=uuid&status=pending to get all the INCOMING & PENDING follow requests
    # localhost:8000/api/follow/?author=uuid&status=accepted to get all the INCOMING & ACCEPTED follow requests
    def get(self, request):
        author_id = request.GET.get("author")
        status = request.GET.get("status")

        if not author_id:
            return Response({"error": "The 'author' query parameter is required."}, status = 400)

        follow_requests = FollowRequest.objects.filter(to_author_id=author_id)

        if status == "pending":
            follow_requests = follow_requests.filter(pending = True)
        elif status == "accepted":
            follow_requests = follow_requests.filter(pending = False, accepted = True)

        serializer = FollowRequestSerializer(follow_requests, many=True)
        return Response(serializer.data)
    
# query localhost:8000/api/friends/?author=uuid
class FriendListAPIView(APIView):
    """
    API endpoint to retrieve mutual friendships.

    Returns a list of users who have both sent and accepted a follow request with the given user.

    Parameters:
    - author (UUID): Required. The user whose friends you want to retrieve.
    """
    
    permission_classes = [IsAuthenticated]

    def get(self, request):
        author_id = request.query_params.get("author")
        author = get_object_or_404(Author, id = author_id)

        # retrieve people that I'm following, and people that are following me.
        followings = author.followings.filter(accepted = True).values_list("to_author_id", flat = True)
        followers = author.followers.filter(accepted = True).values_list("from_author_id", flat = True)
        
        mutual_ids = set(followings).intersection(set(followers))
        friends = Author.objects.filter(id__in = mutual_ids)

        return Response([{"id": str(f.id), "username": f.username} for f in friends])

# class RelationshipsPageView(TemplateView):
class RelationshipsPageView(LoginRequiredMixin, TemplateView):
    """
    Renders the relationships.html page showing:

    - Friends (mutual follows)
    - Following list
    - Followers list
    - Incoming pending follow requests

    URL parameter:
    - pk (UUID): The ID of the current user whose relationships are being displayed.

    Template: relationships.html
    """
    template_name = "relationships.html"
    login_url = "/"     # if not loged in, then redirect to feed

    def dispatch(self, request, *args, **kwargs):
        # if it's not me, then redirect to feed
        author_id = unquote(str(kwargs.get("pk")))
        if str(request.user.id) != author_id:
            return redirect("feed_page")
        self.kwargs["pk"] = author_id
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        author_id = self.kwargs.get("pk")
        current_user = get_object_or_404(Author, id=author_id)

        all_requests = FollowRequest.objects.all()
        friends_set = set()
        followers = []
        following = []
        pending_requests = []

        pending_sent = set(
            FollowRequest.objects.filter(from_author=current_user, pending=True)
            .values_list("to_author_id", flat=True)
        )

        from_to_map = {(str(fr.from_author_id), str(fr.to_author_id)): fr for fr in all_requests}

        for fr in all_requests:
            from_id = str(fr.from_author_id)
            to_id = str(fr.to_author_id)

            if from_id == str(current_user.id):
                if fr.accepted:
                    reverse_fr = from_to_map.get((to_id, from_id))
                    if reverse_fr and reverse_fr.accepted:
                        friends_set.add(fr.to_author)
                    else:
                        following.append({"user": fr.to_author, "pending": False})
                elif fr.pending:
                    following.append({"user": fr.to_author, "pending": True})

            elif to_id == str(current_user.id):
                pending = fr.from_author.id in pending_sent
                if fr.accepted:
                    reverse_fr = from_to_map.get((to_id, from_id))
                    if reverse_fr and reverse_fr.accepted:
                        friends_set.add(fr.from_author)
                    else:
                        followers.append({"user": fr.from_author, "pending": pending})
                elif fr.pending:
                    pending_requests.append(fr.from_author)

        context.update({
            "author_id": author_id,
            "friends_list": list(friends_set),
            "following_list": following,
            "followers_list": followers,
            "pending_requests_list": pending_requests,
        })
        return context

class FollowersListAPIView(APIView):
    """
    GET /api/authors/{pk}/followers/
    Return JSON {
        "type": "followers",
        "followers": [ …AuthorSerializer… ]
    }
    """
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        author = get_object_or_404(Author, uuid=pk)
        author_id = author.id

        frs = FollowRequest.objects.filter(
            to_author_id=author_id,
            accepted=True
        )

        followers = [fr.from_author for fr in frs]

        serializer = AuthorSerializer(
            followers,
            many=True,
            context={'request': request}
        )

        return Response({
            'type': 'followers',
            'followers': serializer.data
        }, status=status.HTTP_200_OK)

class FollowerDetailAPIView(APIView):
    """
    GET    /api/authors/{pk}/followers/{fqid}/  
    PUT    /api/authors/{pk}/followers/{fqid}/ 
    DELETE /api/authors/{pk}/followers/{fqid}/ 
    """
    def get_authenticators(self):
        if self.request.method == 'GET':
            return [SessionAuthentication(), BasicAuthentication()]
        return [SessionAuthentication()]

    def get_permissions(self):
        if self.request.method in ('PUT', 'DELETE'):
            return [IsAuthenticated()]
        return []


    def _parse_fqid(self, fqid):
        """
        Return (decoded_url, foreign_id)
        foreign_id is from the last part of the url.
        """
        decoded = unquote(fqid)
        path = urlparse(decoded).path
        parts = [p for p in path.split('/') if p]

        foreign_id = parts[-1] if len(parts) >= 2 and parts[-2] == 'authors' else None
        return decoded, foreign_id

    def get(self, request, pk, fqid):
        decoded_url, foreign_id = self._parse_fqid(fqid)

        local_base = request.build_absolute_uri('/api/authors/').rstrip('/')
        target = get_object_or_404(Author, uuid=pk)
        target_id = target.id

        if decoded_url.startswith(local_base):

            if not FollowRequest.objects.filter(
                from_author_id=foreign_id,
                to_author_id=target_id,
                accepted=True
            ).exists():
                return Response(status=status.HTTP_404_NOT_FOUND)
            author = get_object_or_404(Author, id=foreign_id)
            serializer = AuthorSerializer(author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        try:
            resp = requests.get(decoded_url, headers={'Accept': 'application/json'})
            data = resp.json()
        except requests.RequestException as e:
            return Response(
                {'error': 'Failed to fetch remote author', 'detail': str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )
        return Response(data, status=resp.status_code)

    def put(self, request, pk, fqid):
        if str(request.user.uuid) != str(pk):
            return Response(status=status.HTTP_403_FORBIDDEN)

        _, foreign_id = self._parse_fqid(fqid)
        target = get_object_or_404(Author, uuid=pk)
        target_id = target.id
        fr, created = FollowRequest.objects.get_or_create(
            from_author_id=foreign_id,
            to_author_id=target_id,
            defaults={'pending': False, 'accepted': True}
        )
        if not created and not fr.accepted:
            fr.accepted = True
            fr.pending = False
            fr.save(update_fields=['accepted', 'pending'])
        follower = fr.from_author
        local_host = settings.BASE_URL.rstrip('/') + '/api'
        follower_netloc = urlparse(follower.host.rstrip('/')).netloc
        local_netloc = urlparse(local_host.rstrip('/')).netloc
        if follower_netloc != local_netloc:
            send_unlisted_entries_to_follower(fr.to_author, follower)
            if FollowRequest.objects.filter(
                from_author=fr.to_author,
                to_author=follower,
                accepted=True
            ).exists():
                send_friends_entries_to_friend(fr.to_author, follower)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def delete(self, request, pk, fqid):
        if str(request.user.uuid) != str(pk):
            return Response(status=status.HTTP_403_FORBIDDEN)

        _, foreign_id = self._parse_fqid(fqid)
        fr = FollowRequest.objects.filter(
            from_author_id=foreign_id,
            to_author_id=get_object_or_404(Author, uuid=pk).id
        ).first()
        if fr:
            fr.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)