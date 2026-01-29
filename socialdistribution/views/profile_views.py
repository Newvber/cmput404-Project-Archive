# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.generic import TemplateView
from rest_framework import status
from django.db.models import Q
import base64
from django.contrib.auth import logout
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from socialdistribution.models.author import FIELD_MAX_LENGTH
from socialdistribution.models import Author, FollowRequest, Entry
from socialdistribution.serializers import AuthorSerializer

import requests
from urllib.parse import unquote

class ProfilePageView(TemplateView):
    """
    Renders a user's profile page.

    Shows author info, follower/following counts, and visible posts based on
    user authentication and relationship.

    Template: profile.html
    """
    template_name = "profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        encoded = kwargs["pk"]
        fqid = unquote(encoded)
        author_uuid = fqid.rstrip("/").split("/")[-1]
        profile_author = get_object_or_404(Author, uuid=author_uuid)
        
        follower_count = FollowRequest.objects.filter(
            to_author=profile_author, accepted=True
        ).count()
        following_count = FollowRequest.objects.filter(
            from_author=profile_author, accepted=True
        ).count()

        user = self.request.user
        is_self = (user == profile_author)
        if user.is_authenticated:
            context["display_name"] = user.display_name
            context["username"] = user.username
            context["is_authenticated"] = True
            context["user_id"] = str(user.id)

            if is_self:
                relationship = "self"
            else:
                fr = FollowRequest.objects.filter(
                    from_author=user, to_author=profile_author
                ).first()
                if fr and fr.accepted:
                    relationship = "following"
                elif fr and fr.pending:
                    relationship = "pending"
                else:
                    relationship = "none"
        else:
            context["display_name"] = "Guest"
            context["username"] = None
            context["is_authenticated"] = False
            context["user_id"] = None
            relationship = "none"

        context.update({
            "profile_author": profile_author,
            "follower_count": follower_count,
            "following_count": following_count,
            "relationship": relationship,
            "is_self": is_self,
        })

        entries = Entry.objects.filter(author=profile_author).exclude(visibility="DELETED")

        if is_self:
            context["posts"] = entries.order_by("-created_at")
            return context

        if user.is_authenticated:
            following_ids = set(
                FollowRequest.objects.filter(
                    from_author=user, accepted=True
                ).values_list("to_author_id", flat=True)
            )
            follower_ids = set(
                FollowRequest.objects.filter(
                    to_author=user, accepted=True
                ).values_list("from_author_id", flat=True)
            )
        else:
            following_ids = set()
            follower_ids = set()

        friend_ids = following_ids & follower_ids

        visible_entries = entries.filter(
            Q(visibility="PUBLIC")
            | Q(visibility="UNLISTED", author_id__in=following_ids)
            | Q(visibility="FRIENDS", author_id__in=friend_ids)
        ).order_by("-created_at")

        context["posts"] = visible_entries
        return context

class ProfileStatsAPIView(APIView):
    """
    API endpoint to retrieve follower and following counts for a given author.

    """
    def get(self, request, pk):
        author_id = unquote(pk)
        profile_author = get_object_or_404(Author, uuid=author_id)
        follower_count = FollowRequest.objects.filter(
            to_author=profile_author, accepted=True
        ).count()
        following_count = FollowRequest.objects.filter(
            from_author=profile_author, accepted=True
        ).count()
        return Response({
            "follower_count": follower_count,
            "following_count": following_count,
        })

class SingleAuthorAPIView(APIView):
    """
    GET /api/authors/{pk}/  — open profile to any users
    PUT /api/authors/{pk}/  — only allow authors to edit their profiles by themselves
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'GET':
            return []
        return [IsAuthenticated()]

    def get(self, request, pk):
        """Return the author with the given UUID."""
        author = get_object_or_404(Author, uuid=str(pk))
        serializer = AuthorSerializer(author, context={'request': request})
        return Response(serializer.data)

    def put(self, request, pk):
        if request.user.uuid != pk:
            return Response({'detail': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        author = request.user
        data = request.data
    

        allowed = {"display_name", "username", "password", "github_link", "profile_image", "description"}
        provided = [f for f in allowed if f in data or f == "profile_image" and request.FILES.get("profile_image")]

        if len(provided) != 1:
            return Response(
                {"error": "Provide exactly one field to update."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        field = provided[0]

        if field == "profile_image":
            file = request.FILES.get("profile_image")
            if file:
                raw = b"".join(chunk for chunk in file.chunks())
                mime = file.content_type or "application/octet-stream"
                b64 = base64.b64encode(raw).decode()
                author.profile_image = f"data:{mime};base64,{b64}"
            else:
                url = data.get("profile_image", "").strip()
                if not url:
                    return Response({"error": "No file or URL provided."}, status=status.HTTP_400_BAD_REQUEST)
                author.profile_image = url
            author.save(update_fields=["profile_image"])
            return Response({"profileImage": author.profile_image}, status=status.HTTP_200_OK)

        value = data.get(field, "").strip()
        if not value:
            return Response({"error": "Value cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        if field in {"display_name", "username"}:
            if value == getattr(author, field):
                return Response({"error": f"{field} is unchanged."}, status=status.HTTP_400_BAD_REQUEST)
            if len(value) > FIELD_MAX_LENGTH:
                return Response({"error": f"{field} too long."}, status=status.HTTP_400_BAD_REQUEST)
            if Author.objects.filter(**{field: value}).exclude(id=author.id).exists():
                return Response(
                    {"error": f"{field.replace('_',' ').capitalize()} already exists."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            setattr(author, field, value)
            author.save(update_fields=[field])
            return Response({field: value}, status=status.HTTP_200_OK)

        if field == "github_link":
            current = author.github_link or ""
            if value == current:
                return Response({"error": "github_link is unchanged."}, status=status.HTTP_400_BAD_REQUEST)
            if len(value) > 200:
                return Response({"error": "github_link too long."}, status=status.HTTP_400_BAD_REQUEST)
            author.github_link = value
            author.save(update_fields=["github_link"])
            return Response({"github": value}, status=status.HTTP_200_OK)

        if field == "password":
            if len(value) < 8 or len(value) > 16:
                return Response({"error": "Password must be 8-16 characters."}, status=status.HTTP_400_BAD_REQUEST)
            if author.check_password(value):
                return Response({"error": "Password is unchanged."}, status=status.HTTP_400_BAD_REQUEST)
            author.set_password(value)
            author.save(update_fields=["password"])
            logout(request)
            return Response({"message": "Password updated."}, status=status.HTTP_200_OK)

        if field == "description":
            current = author.description or ""
            if value == current:
                return Response({"error": "description is unchanged."}, status=status.HTTP_400_BAD_REQUEST)
            if len(value) > 500:
                return Response({"error": "description too long."}, status=status.HTTP_400_BAD_REQUEST)
            author.description = value
            author.save(update_fields=["description"])
            return Response({"description": value}, status=status.HTTP_200_OK)

        return Response({"error": "Invalid field."}, status=status.HTTP_400_BAD_REQUEST)


class RemoteSingleAuthorAPIView(APIView):
    """
    GET /api/authors/{percent_encoded_FQID}/
    """
    authentication_classes = [BasicAuthentication]   
    permission_classes = [IsAuthenticated]       

    def get(self, request, fqid):
        author_url = unquote(fqid)

        try:
            resp = requests.get(author_url, headers={'Accept': 'application/json'})
        except requests.RequestException as e:
            return Response(
                {'error': 'Failed to fetch remote author', 'detail': str(e)},
                status=status.HTTP_502_BAD_GATEWAY
            )

        return Response(resp.json(), status=resp.status_code)

