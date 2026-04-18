from rest_framework import serializers
from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "phone", "gender"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class GoogleLoginSerializer(serializers.Serializer):
    token = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "phone", "gender", "rating", "rating_count"]


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["phone", "gender"]

    def validate_phone(self, value):
        phone = (value or "").strip()
        if not phone:
            return None
        existing = User.objects.filter(phone=phone).exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError("This phone number is already in use.")
        return phone

    def validate_gender(self, value):
        gender = (value or "").strip()
        return gender or None


class OTPRequestSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=["email", "phone"])
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        channel = attrs.get("channel")
        email = (attrs.get("email") or "").strip().lower()
        phone = (attrs.get("phone") or "").strip()

        if channel == "email" and not email:
            raise serializers.ValidationError({"email": ["Email is required for email OTP."]})
        if channel == "phone" and not phone:
            raise serializers.ValidationError({"phone": ["Phone number is required for mobile OTP."]})

        attrs["email"] = email
        attrs["phone"] = phone
        return attrs
