from rest_framework import serializers
from django.conf import settings
from socialdistribution.models import Entry, Comment, Like
from .authorserializer import AuthorSerializer
from urllib.parse import quote

class EntryDetailSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()
    web = serializers.SerializerMethodField()
    author = AuthorSerializer(read_only=True)
    comments = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()
    published = serializers.DateTimeField(
        source="created_at",
        format="%Y-%m-%dT%H:%M:%S%z",
        required=False,
    )

    class Meta:
        model = Entry
        fields = [
            "type",
            "title",
            "id",
            "web",
            "description",
            "contentType",
            "content",
            "author",
            "comments",
            "likes",
            "published",
            "visibility",
        ]

    def get_type(self, obj):
        return "entry"

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)

    def _entry_path(self, obj):
        """Return the path segment for this entry's web URL."""
        local_prefix = f"{settings.BASE_URL.rstrip('/')}/api/"
        entry_id = str(obj.id).rstrip('/')
        if entry_id.startswith(local_prefix):
            return entry_id.split('/')[-1]
        return quote(entry_id, safe='')

    def get_id(self, obj):
        return obj.id

    def get_web(self, obj):
        entry_path = self._entry_path(obj)
        return f"{settings.BASE_URL}/authors/{obj.author.uuid}/entries/{entry_path}/"

    def get_comments(self, obj):
        qs = Comment.objects.filter(entry=obj).order_by("-created_at")
        entry_path = self._entry_path(obj)
        count = qs.count()
        size = 5
        data = []
        for c in qs[:size]:
            host = c.author.host.rstrip('/')
            id_host = host if host.endswith('/api') else f"{host}/api"
            like_qs = Like.objects.filter(comment=c).order_by("-created_at")
            like_data = []
            for l in like_qs[:5]:
                l_host = l.author.host.rstrip('/')
                l_id_host = l_host if l_host.endswith('/api') else f"{l_host}/api"
                like_data.append({
                    "type": "like",
                    "author": AuthorSerializer(l.author).data,
                    "published": l.created_at.isoformat(),
                    "id": l.id,
                    "object": c.id,
                })

            data.append({
                "type": "comment",
                "author": AuthorSerializer(c.author).data,
                "comment": c.comment,
                "contentType": "text/plain",
                "published": c.created_at.isoformat(),
                "id": c.id,
                "entry": obj.id,
                # "web": f"{settings.BASE_URL}/authors/{obj.author.uuid}/entries/{entry_path}/",
                "likes": {
                    "type": "likes",
                    "id": f"{settings.BASE_URL}/api/authors/{obj.author.uuid}/entries/{entry_path}/comments/{quote(c.id, safe='')}/likes",
                    "web": f"{settings.BASE_URL}/authors/{obj.author.uuid}/entries/{entry_path}/",
                    "page_number": 1,
                    "size": 5,
                    "count": like_qs.count(),
                    "src": like_data,
                },
            })
        host_raw = obj.author.host.rstrip('/')
        id_host = host_raw if host_raw.endswith('/api') else f"{host_raw}/api"
        web_host = host_raw[:-4] if host_raw.endswith('/api') else host_raw
        entry_web = self.get_web(obj)
        return {
            "type": "comments",
            "web": entry_web,
            "id": f"{id_host}/authors/{obj.author.uuid}/entries/{entry_path}/comments",
            "page_number": 1,
            "size": size,
            "count": count,
            "src": data,
        }

    def get_likes(self, obj):
        qs = Like.objects.filter(entry=obj).order_by("-created_at")
        entry_path = self._entry_path(obj)
        count = qs.count()
        size = 5
        data = []
        for l in qs[:size]:
            host = l.author.host.rstrip('/')
            id_host = host if host.endswith('/api') else f"{host}/api"
            data.append({
                "type": "like",
                "author": AuthorSerializer(l.author).data,
                "published": l.created_at.isoformat(),
                "id": l.id,
                "object": obj.id,
            })

        host_raw = obj.author.host.rstrip('/')
        id_host = host_raw if host_raw.endswith('/api') else f"{host_raw}/api"
        web_host = host_raw[:-4] if host_raw.endswith('/api') else host_raw
        entry_web = self.get_web(obj)
        return {
            "type": "likes",
            "web": entry_web,
            "id": f"{id_host}/authors/{obj.author.uuid}/entries/{entry_path}/likes",
            "page_number": 1,
            "size": size,
            "count": count,
            "src": data,
        }
