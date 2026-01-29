# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18

from rest_framework import serializers
from socialdistribution.models import Like, Entry, Author, Comment
from django.shortcuts import get_object_or_404
from .authorserializer import AuthorSerializer

class LikeSerializer(serializers.Serializer):
    type      = serializers.CharField()
    author    = serializers.SerializerMethodField()
    published = serializers.DateTimeField(source='created_at', read_only=True)
    id        = serializers.CharField(required=False)
    object    = serializers.CharField()

    def get_author(self, obj):
        """Return the full serialized author object."""
        return AuthorSerializer(obj.author, context=self.context).data

    def validate(self, attrs):
        """
        check if a user likes a comment or entry twice
        """
        user = self.context.get('author') or self.context['request'].user
        obj_url = attrs.get('object', '')

        if '/commented/' in obj_url:
            comment_url = obj_url.rstrip('/')
            comment = Comment.objects.filter(id=comment_url).first()
            if comment is None:
                comment_id = comment_url.split('/')[-1]
                comment = Comment.objects.filter(uuid=comment_id).first()
            if comment is None:
                raise serializers.ValidationError("Comment not found.")
            if Like.objects.filter(author=user, comment=comment).exists():
                raise serializers.ValidationError("You have already liked this comment.")
        else:
            entry = get_object_or_404(Entry, id=obj_url.rstrip('/'))
            if Like.objects.filter(author=user, entry=entry).exists():
                raise serializers.ValidationError("You have already liked this entry.")
        return attrs
        
    def create(self, validated_data):
        user = self.context.get('author') or self.context['request'].user
        obj_url = validated_data['object']
        # Determine whether the object is an Entry or Comment

        provided_id = validated_data.get('id')
        like_kwargs = {
            'author': user,
            'object_url': obj_url,
        }

        if provided_id:
            # Extract the UUID portion of the provided ID if it is a full URL
            import uuid
            like_id = str(provided_id).rstrip('/').split('/')[-1]
            try:
                like_kwargs['uuid'] = uuid.UUID(like_id)
            except ValueError:
                pass

        if '/commented/' in obj_url:
            # It's a comment URL
            comment_url = obj_url.rstrip('/')
            comment = Comment.objects.filter(id=comment_url).first()
            if comment is None:
                comment_id = comment_url.split('/')[-1]
                comment = get_object_or_404(Comment, uuid=comment_id)
            like_kwargs['comment'] = comment
        else:
            entry = get_object_or_404(Entry, id=obj_url.rstrip('/'))
            like_kwargs['entry'] = entry

        like = Like.objects.create(**like_kwargs)
        return like

    def to_representation(self, instance):
        author = instance.author
        # Choose object target
        if instance.object_url:
            object_url = instance.object_url
        elif instance.comment:
            target = instance.comment
            object_url = target.id
        else:
            target = instance.entry
            object_url = target.id

        return {
            'type': 'like',
            'author': AuthorSerializer(author, context=self.context).data,
            'published': instance.created_at.isoformat(),
            'id':        instance.id,
            'object':    object_url,
        }
