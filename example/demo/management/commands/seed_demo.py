"""
seed_demo — create demo data idempotently.

Creates:
  - superuser admin/admin (username=admin, password=admin)

Idempotent: safe to call multiple times; never duplicates the user.

Log in at http://localhost:8000/accounts/login/ (admin / admin), or visit
http://localhost:8000/__login__/ to log in without a password prompt.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Seed the demo project with a demo superuser (idempotent)."

    def handle(self, *args, **options):
        User = get_user_model()

        username = "admin"
        email = "admin@example.com"
        password = "admin"

        user, created = User.objects.get_or_create(
            **{User.USERNAME_FIELD: username},
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        if created:
            user.set_password(password)
            user.save(update_fields=["password"])
            self.stdout.write(
                self.style.SUCCESS(f"Created superuser: {username} / {password}")
            )
        else:
            self.stdout.write(
                self.style.NOTICE(f"Superuser {username!r} already exists.")
            )

        self.stdout.write(
            self.style.SUCCESS("Auto-login URL: http://localhost:8000/__login__/")
        )
