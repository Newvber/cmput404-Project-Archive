# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework import serializers
from socialdistribution.models import FollowRequest, Author

class FollowRequestSerializer(serializers.Serializer):
    """
    Serializer for FollowRequest objects in Inbox API, independent of model fields.
    """
    type    = serializers.CharField()
    summary = serializers.CharField()
    actor   = serializers.JSONField(source='actor_data')
    object  = serializers.JSONField(source='object_data')
    state   = serializers.SerializerMethodField()

    def get_type(self, obj):
        return 'follow'
        
    def get_state(self, obj):
        if obj.accepted:
            return 'accepted'
        if obj.pending:
            return 'requesting'
        return 'rejected'

    def create(self, validated_data):
        # Pop write-only 'type'
        validated_data.pop('type', None)
        # If save() was called with from/to author IDs, use those; otherwise fallback to context
        from_author_id = validated_data.pop('from_author_id', None) or self.context['request'].user.id
        to_author_id   = validated_data.pop('to_author_id',   None) or self.context['view'].kwargs.get('author_id')

        # Ensure ``to_author_id`` references the fully qualified author id.
        to_author = None
        try:
            to_author = Author.objects.get(id=to_author_id)
        except Author.DoesNotExist:
            # ``author_id`` from URL is a UUID; look up by uuid and use its fqid
            try:
                to_author = Author.objects.get(uuid=to_author_id)
                to_author_id = to_author.id
            except Author.DoesNotExist:
                pass

        actor_data  = validated_data.get('actor_data', {})
        object_data = validated_data.get('object_data', {})

        if to_author:
            canonical = f"{to_author.host.rstrip('/api')}/api/authors/{to_author.uuid}"
            if isinstance(object_data, dict):
                object_data['id'] = canonical
            else:
                object_data = canonical

        fr, _ = FollowRequest.objects.update_or_create(
            from_author_id=from_author_id,
            to_author_id=to_author_id,
            defaults={
                'summary': validated_data.get('summary', ''),
                'actor_data': actor_data,
                'object_data': object_data,
                'pending': True,
                'accepted': False,
            },
        )
        return fr

    def to_representation(self, instance):
        # Build output JSON matching desired shape
        return {
            'type':    self.get_type(instance),
            'summary': instance.summary,
            # 'state':   self.get_state(instance),
            'actor':   instance.actor_data,
            'object':  instance.object_data,
        }






