# The following written with completion assistance from Microsoft, Copilot/ ChatGPT, OpenAI 2025-06-18
from rest_framework import serializers
from socialdistribution.models import Entry

class EntrySerializer(serializers.ModelSerializer):
    """
    Serializer for the Entry model.

    Serializes all fields of an Entry

    Fields:
        author (Author): The read-only creator of the entry.
    """
    class Meta:
        model  = Entry
        # fields = [
        #     "id",
        #     "title",
        #     "content",
        #     "contentType",
        #     "description",
        #     "author",
        #     "created_at",
        #     "updated_at",
        #     "visibility",
        #     "is_deleted",
        # ]
        read_only_fields = ["author"]