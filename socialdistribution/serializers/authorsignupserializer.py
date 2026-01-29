# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework import serializers
from socialdistribution.models import Author
from django.conf import settings

class AuthorSignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only = True,
        min_length = 8,
        max_length = 32,
        style = {"input_type": "password"},
        error_messages = {
            "min_length": "Password must be at least 8 characters long.",
            "max_length": "Password must be no more than 32 characters long.",
        })
    
    class Meta:
        model = Author
        fields = ["username", "display_name", "password"]

    def create(self, validated_data):
        """
        Create a new Author instance with hashed password.
        
        Args:
            validated_data (dict): Validated fields from the signup request.

        Returns:
            Author: The created Author instance.
        """
        password = validated_data.pop("password")   # password is a plaintext
        
        validated_data['is_approved'] = not settings.REQUIRE_ADMIN_APPROVAL
        author = Author(**validated_data)
        base = settings.BASE_URL.rstrip('/')
        author.host = f"{base}/api/"
        author.set_password(password)               # Author.password is hashed
        author.save()                               # store in DB
        return author
