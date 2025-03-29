from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from accounts.models import UserProfile

class Command(BaseCommand):
    help = 'Tworzy brakujące profile użytkowników'

    def handle(self, *args, **options):
        users_without_profile = User.objects.filter(profile__isnull=True)
        created_count = 0
        
        for user in users_without_profile:
            UserProfile.objects.create(user=user)
            created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Pomyślnie utworzono {created_count} brakujących profili użytkowników'
            )
        ) 