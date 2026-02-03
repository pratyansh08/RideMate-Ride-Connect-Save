from rest_framework import serializers

from .models import Message


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.ReadOnlyField(source="sender.id")
    attachment_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "trip", "sender", "message", "attachment", "attachment_url", "created_at"]

    def get_attachment_url(self, obj):
        if obj.attachment:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.attachment.url)
            return obj.attachment.url
        return None

    def validate(self, attrs):
        message = attrs.get("message", "")
        attachment = attrs.get("attachment")
        if not message and not attachment:
            raise serializers.ValidationError("Message or attachment is required.")
        return attrs
