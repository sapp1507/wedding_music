import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update the deployment superuser from environment variables."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")
        email = os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")

        if not password:
            raise CommandError("DJANGO_SUPERUSER_PASSWORD is required.")

        User = get_user_model()
        force_password = os.getenv("DJANGO_SUPERUSER_FORCE_PASSWORD", "0") == "1"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        if created or force_password:
            user.set_password(password)
        user.save()

        action = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Superuser {username!r} {action}."))
        self.stdout.write("Admin login data:")
        self.stdout.write(f"  URL: {os.getenv('PUBLIC_ADMIN_URL', '/admin/')}")
        self.stdout.write(f"  username: {username}")
        if created or force_password:
            self.stdout.write(f"  password: {password}")
        else:
            self.stdout.write("  password: unchanged; use the current password or set DJANGO_SUPERUSER_FORCE_PASSWORD=1")
