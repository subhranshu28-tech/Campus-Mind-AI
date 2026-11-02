import os
import secrets

from django.core.management.base import BaseCommand

from apps.accounts.models import College, User

DEFAULT_ACCOUNTS = [
    {
        "username": "admin",
        "env_password": "DEFAULT_ADMIN_PASSWORD",
        "fallback_password": "ChangeMe!Admin123",
        "email": "admin@smartcampus.local",
    },
    {
        "username": "superadmin",
        "env_password": "DEFAULT_SUPERADMIN_PASSWORD",
        "fallback_password": "ChangeMe!SuperAdmin123",
        "email": "superadmin@smartcampus.local",
    },
]


class Command(BaseCommand):
    help = (
        "Creates default admin and superadmin accounts if they don't already exist. "
        "Intended for local/dev setup only -- change the passwords immediately after "
        "first login, and never run this against a public-facing production database."
    )

    def handle(self, *args, **options):
        college, _ = College.objects.get_or_create(code="LEGACY", defaults={"name": "Legacy Campus", "slug": "legacy-campus"})
        for account in DEFAULT_ACCOUNTS:
            username = account["username"]
            if User.objects.filter(username=username).exists():
                self.stdout.write(self.style.WARNING(f"User '{username}' already exists, skipping."))
                continue

            password = os.getenv(account["env_password"]) or secrets.token_urlsafe(14)
            generated = not os.getenv(account["env_password"])
            user = User.objects.create_superuser(
                username=username,
                email=account["email"],
                password=password,
                college=college,
            )
            user.role = User.Role.SUPER_ADMIN
            user.save(update_fields=["role"])

            self.stdout.write(self.style.SUCCESS(f"Created '{username}' with role super_admin."))
            if generated:
                self.stdout.write(self.style.WARNING(f"  Generated password for '{username}': {password}  (shown once - store it, or set {account['env_password']}).")) 
