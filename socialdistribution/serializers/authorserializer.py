# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-07-09
from rest_framework import serializers
from socialdistribution.models import Author
from urllib.parse import quote
from django.conf import settings

class AuthorSerializer(serializers.ModelSerializer):
    type        = serializers.SerializerMethodField()
    id          = serializers.SerializerMethodField()
    host        = serializers.SerializerMethodField()
    displayName = serializers.CharField(source="display_name")
    github      = serializers.URLField(source="github_link")
    profileImage= serializers.URLField(source="profile_image", required=False)
    web         = serializers.SerializerMethodField()

    class Meta:
        model  = Author
        fields = ["type", "id", "host", "displayName", "github", "profileImage", "web"]

    def get_type(self, obj):
        return "author"

    def get_host(self, obj):
        return obj.host

    def get_id(self, obj):
        return obj.id

    def get_web(self, obj):
        base = settings.BASE_URL.rstrip('/')
        encoded = quote(obj.id, safe='')
        return f"{base}/authors/{encoded}/"
