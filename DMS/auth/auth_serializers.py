from rest_framework import serializers
from .auth_views import *
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)
    confirm_password = serializers.CharField(required=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError(
                "The new passwords do not match.")
        return data

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            user = User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                "User with this email does not exist.")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    token = serializers.CharField()
    uid = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        uid = force_str(urlsafe_base64_decode(data.get("uid")))
        try:
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid UID")

        token = data.get("token")
        if not default_token_generator.check_token(user, token):
            raise serializers.ValidationError("Invalid token")

        if data.get("new_password") != data.get("confirm_password"):
            raise serializers.ValidationError("Passwords do not match")

        return data

    def save(self):
        uid = self.validated_data["uid"]
        user = User.objects.get(pk=uid)
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save()
        return user
