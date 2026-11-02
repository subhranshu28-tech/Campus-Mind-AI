from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers

User = get_user_model()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def save(self):
        email = self.validated_data["email"].strip().lower()
        # Always return the same public response to avoid account enumeration.
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            return
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        frontend_url = __import__("os").getenv("PASSWORD_RESET_URL", "")
        if not frontend_url:
            return
        separator = "&" if "?" in frontend_url else "?"
        reset_url = f"{frontend_url}{separator}uid={uid}&token={token}"
        send_mail(
            subject="Reset your CampusMind password",
            message=f"Use this link to reset your password. It expires when the token becomes invalid:\n\n{reset_url}\n\nIf you did not request this, ignore this email.",
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
        )


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=10, write_only=True)

    def validate(self, attrs):
        try:
            user_id = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=user_id, is_active=True)
        except (ValueError, TypeError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"detail": "Invalid or expired reset link."})
        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"detail": "Invalid or expired reset link."})
        attrs["user"] = user
        return attrs

    def validate_new_password(self, value):
        validate_password(value, self.validated_data.get("user"))
        return value

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
