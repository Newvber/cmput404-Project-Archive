# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework.decorators import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework import parsers
from socialdistribution.models import Author
from socialdistribution.models.author import FIELD_MAX_LENGTH
from socialdistribution.serializers import AuthorSignupSerializer, AuthorSerializer
from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import base64

class AuthorSignupAPIView(APIView):
    """
        API endpoint for user signup.

        Accepts a POST request with 'username', 'display_name', and 'password',
        creates a new Author

        Example request:
        {
            "username": "user1",
            "display_name": "user1",
            "password": "12345678"
        }
    """
    def post(self, request):
        serializer = AuthorSignupSerializer(data = request.data)
        if serializer.is_valid():
            author = serializer.save()
            message = (
                "Your account was created and is awaiting approval by the admin."
                if not author.is_approved else
                "Your account was created and you can now log in."
            )
            return Response({
                "id": str(author.id),
                "username": author.username,
                "display_name": author.display_name,
                "message": message
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# go to localhost:8000/api/login/
# {
#   "username": "registered_user_in_db",
#   "password": "registered_user_in_db",
# }

class AuthorLoginAPIView(APIView):
    """
    API endpoint for user login.

    Accepts a POST request with 'username' and 'password'.
    If credentials are valid, logs in the user and returns profile info.
    """
    def post(self, request):
        # If a user is already logged in, log them out so a new login can occur
        if request.user.is_authenticated:
            logout(request)
        
        # Get username and password value from the request's data
        username = request.data.get("username")
        password = request.data.get("password")

        author = authenticate(username = username, password = password)
        if author:
            if not author.is_approved:
                return Response(
                {"error": "Your account is not approved yet. Please wait for admin approval."},
                status=status.HTTP_403_FORBIDDEN
                )
            login(request, author)
            return Response({
                "id": str(author.id),
                "username": author.username,
                "display_name": author.display_name,
            }, status = status.HTTP_200_OK)
        return Response({"error": "Invalid credentials"},
                        status = status.HTTP_401_UNAUTHORIZED)

class AuthorLogoutAPIView(APIView):
    """
    API endpoint for user logout.

    Accepts a POST request and logs out the currently authenticated user.
    """
    def post(self, request):
        logout(request)
        return Response({"message": "Logged out successfully."}, status = status.HTTP_200_OK)
    
# renders auth/login.html when called
class LoginPageView(TemplateView):
    """
    Renders the login page template.

    Redirects authenticated users to the homepage.
    """
    template_name = "auth/login.html"

    def dispatch(self, request, *args, **kwargs):
        # If the user is already logged in and tries to access /login, they are redirected to the homepage (/).
        if request.user.is_authenticated:
            return redirect("/")
        # lets unauthenticated users proceed to render the login page by continuing the normal TemplateView flow.
        return super().dispatch(request, *args, **kwargs)

class SignupPageView(TemplateView):
    """
    Renders the signup page template.

    Redirects authenticated users to the homepage.
    """
    template_name = "auth/signup.html"

    def dispatch(self, request, *args, **kwargs):
        # If the user is already logged in and tries to access /signup, they are redirected to the homepage (/).
        if request.user.is_authenticated:
            return redirect("/")
        # lets unauthenticated users proceed to render the login page by continuing the normal TemplateView flow.
        return super().dispatch(request, *args, **kwargs)


class AuthorProfileEditAPIView(APIView):
    """
    API endpoint to edit profile fields for the currently authenticated user.

    Supports PATCH requests to update exactly one of:
    - 'display_name'
    - 'username'
    - 'password'
    - 'github_link'
    -'description'

    Includes validation for duplication and length.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        author = request.user
        data = request.data

        allowed = {"display_name", "username", "password", "github_link", "profile_image","description"}
        provided = [field for field in allowed if field in data or field in request.FILES]

        if len(provided) != 1:
            return Response({"error": "Provide exactly one field to update."}, status=status.HTTP_400_BAD_REQUEST)

        field = provided[0]

        if field == "profile_image":
            file = request.FILES.get("profile_image")
            if file:
                data = b"".join(chunk for chunk in file.chunks())
                mime = file.content_type or "application/octet-stream"
                b64 = base64.b64encode(data).decode()
                author.profile_image = f"data:{mime};base64,{b64}"
            else:
                url = data.get("profile_image", "").strip()
                if not url:
                    return Response({"error": "No file or URL provided."}, status=status.HTTP_400_BAD_REQUEST)
                author.profile_image = url
            author.save(update_fields=["profile_image"])
            return Response({"profile_image": author.profile_image}, status=status.HTTP_200_OK)

        value = data.get(field, "").strip()

        if not value:
            return Response({"error": "Value cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)

        if field in {"display_name", "username"}:
            if value == getattr(author, field):
                return Response({"error": f"{field} is unchanged."}, status=status.HTTP_400_BAD_REQUEST)
            if len(value) > FIELD_MAX_LENGTH:
                return Response({"error": f"{field} too long."}, status=status.HTTP_400_BAD_REQUEST)
            if Author.objects.filter(**{field: value}).exclude(id=author.id).exists():
                return Response({"error": f"{field.replace('_', ' ').capitalize()} already exists."}, status=status.HTTP_400_BAD_REQUEST)

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
            return Response({"github_link": value}, status=status.HTTP_200_OK)

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
                return Response({"error": "Description is unchanged."}, status=status.HTTP_400_BAD_REQUEST)
            if len(value) > 500:
                return Response({"error": "Description too long."}, status=status.HTTP_400_BAD_REQUEST)
            author.description = value
            author.save(update_fields=["description"])
            return Response({"description": value}, status=status.HTTP_200_OK)
        

        return Response({"error": "Invalid field."}, status=status.HTTP_400_BAD_REQUEST)

class AuthorsAPIView(APIView):
    """
    GET /api/authors/?page=<page_number>&size=<size>
    Return {
        "type": "authors",
        "authors": [ …AuthorSerializer… ]
    }
    """

    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page_param = request.query_params.get('page', None)
        size_param = request.query_params.get('size', None)

        authors_queryset = Author.objects.all().order_by('id')
        
        if page_param is not None and size_param is not None:
            try:
                page = int(page_param)
                size = int(size_param)
            except (ValueError, TypeError):
                return Response({"error": "Page and size must be valid integers."}, status=400)

            paginator = Paginator(authors_queryset, size)
            try:
                authors_to_serialize = paginator.page(page).object_list
            except (EmptyPage, PageNotAnInteger):
                authors_to_serialize = []
        else:
            authors_to_serialize = authors_queryset

        serializer = AuthorSerializer(
            authors_to_serialize,
            many=True,
            context={'request': request}
        )
        return Response({
            'type': 'authors',
            'authors': serializer.data
        })
