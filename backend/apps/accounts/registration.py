import re
from django.contrib.auth import password_validation
from django.db import transaction
from django.utils.text import slugify
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .models import College, User


class CollegeRegistrationSerializer(serializers.Serializer):
    college_name = serializers.CharField(max_length=180)
    college_code = serializers.RegexField(r"^(?=.*[A-Za-z0-9])[A-Za-z0-9-]{3,24}$")
    admin_name = serializers.CharField(max_length=150)
    username = serializers.RegexField(r"^[A-Za-z0-9@.+_-]{3,150}$")
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=10, trim_whitespace=False)

    def validate(self, attrs):
        code = attrs["college_code"].upper()
        slug = slugify(code)
        if College.objects.filter(code=code).exists() or College.objects.filter(slug=slug).exists():
            raise serializers.ValidationError({"college_code": "This college code is already registered."})
        if User.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "This username is already in use."})
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})
        password_validation.validate_password(attrs["password"])
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        college = College.objects.create(
            name=validated_data["college_name"],
            code=validated_data["college_code"].upper(),
            slug=slugify(validated_data["college_code"]),
            email=validated_data["email"],
        )
        name = validated_data["admin_name"].strip().split(" ", 1)
        user = User.objects.create_user(
            username=validated_data["username"], email=validated_data["email"],
            password=validated_data["password"], first_name=name[0],
            last_name=name[1] if len(name) > 1 else "", role=User.Role.COLLEGE_ADMIN,
            college=college,
        )
        return college, user


class CollegeRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "college_registration"

    def post(self, request):
        serializer = CollegeRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        college, user = serializer.save()
        return Response({
            "detail": "College workspace created. Sign in with the college administrator account.",
            "college": {"id": college.id, "name": college.name, "code": college.code, "slug": college.slug},
            "user": {"id": user.id, "username": user.username, "email": user.email, "role": user.role},
        }, status=status.HTTP_201_CREATED)
