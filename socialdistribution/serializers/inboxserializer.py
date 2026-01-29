# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework import serializers
from socialdistribution.models import FollowRequest, Like, Comment, Entry
from socialdistribution.serializers import EntryDetailSerializer, FollowRequestSerializer, LikeSerializer, CommentSerializer

class InboxItemSerializer(serializers.Serializer):
    """
    Polymorphic serializer for inbox items.
    """
    def to_representation(self, instance):
        if isinstance(instance, Entry):
            return EntryDetailSerializer(instance, context=self.context).data
        if isinstance(instance, FollowRequest):
            return FollowRequestSerializer(instance, context=self.context).data
        if isinstance(instance, Like):
            return LikeSerializer(instance, context=self.context).data
        if isinstance(instance, Comment):
            return CommentSerializer(instance, context=self.context).data
        raise serializers.ValidationError(
            f'Unsupported inbox item type: {type(instance)}'
        )

        
