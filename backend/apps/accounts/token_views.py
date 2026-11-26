"""Authentication views with college-aware access and refresh-token revocation."""
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView


class CollegeAwareTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Reject users whose college workspace has been deactivated."""

    def validate(self, attrs):
        data = super().validate(attrs)
        college = getattr(self.user, "college", None)
        if college is not None and not college.is_active:
            raise serializers.ValidationError(
                {"detail": "This college workspace is inactive. Contact your administrator."}
            )
        return data


class CollegeAwareTokenObtainPairView(TokenObtainPairView):
    serializer_class = CollegeAwareTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class LogoutView(APIView):
    """Blacklist the submitted refresh token so it cannot be replayed."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token_refresh"

    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                token = RefreshToken(refresh)
            except TokenError:
                # Already invalid or expired: logout should still succeed.
                token = None
            if token is not None and str(token.payload.get("user_id")) != str(request.user.id):
                return Response({"detail": "Refresh token does not belong to this session."}, status=status.HTTP_400_BAD_REQUEST)
            if token is not None:
                try:
                    token.blacklist()
                except TokenError:
                    pass
        return Response({"detail": "Signed out."}, status=status.HTTP_200_OK)
