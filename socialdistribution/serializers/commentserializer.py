# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework import serializers
from django.conf import settings
from socialdistribution.models import Comment, Like
from .authorserializer import AuthorSerializer
from urllib.parse import quote

class CommentSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    author = AuthorSerializer(read_only=True)
    comment = serializers.CharField()
    contentType = serializers.CharField(source='content_type')
    published = serializers.DateTimeField(source='created_at', format="%Y-%m-%dT%H:%M:%S%z")
    id = serializers.CharField()
    uuid = serializers.UUIDField(write_only=True, required=False)
    entry = serializers.SerializerMethodField()
    likes = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            'type',
            'author',
            'comment',
            'contentType',
            'published',
            'id',
            'uuid',
            'entry',
            'likes']

    def get_type(self, obj):
        return 'comment'


    def get_id(self, obj):
        return obj.id

    def get_entry(self, obj):
        # URL of the entry commented on
        return obj.entry.id

    def _entry_path(self, entry):
        """Return the path component for the given entry."""
        local_prefix = f"{settings.BASE_URL.rstrip('/')}/api/"
        entry_id = str(entry.id).rstrip('/')
        if entry_id.startswith(local_prefix):
            return entry_id.split('/')[-1]
        return quote(entry_id, safe='')

    def get_likes(self, obj):
        qs = Like.objects.filter(comment=obj).order_by("-created_at")
        count = qs.count()
        size = 5
        data = []
        for l in qs[:size]:
            host = l.author.host.rstrip('/')
            id_host = host if host.endswith('/api') else f"{host}/api"
            data.append({
                'type': 'like',
                'author': AuthorSerializer(l.author).data,
                'published': l.created_at.isoformat(),
                'id': l.id,
                'object': self.get_id(obj)
            })

        entry_path = self._entry_path(obj.entry)
        comment_path = quote(self.get_id(obj), safe='')

        return {
            'type': 'likes',
            'web': f"{settings.BASE_URL}/authors/{obj.entry.author.uuid}/entries/{entry_path}/",
            'id': f"{settings.BASE_URL}/api/authors/{obj.entry.author.uuid}/entries/{entry_path}/comments/{comment_path}/likes/",
            'page_number': 1,
            'size': size,
            'count': count,
            'src': data,
        }