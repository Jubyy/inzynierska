from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, UserFollowing

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile użytkowników'

# Rozszerzenie standardowego UserAdmin, aby zawierał profil
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff')

# Wyrejestrowanie standardowego UserAdmin
admin.site.unregister(User)
# Zarejestrowanie naszego CustomUserAdmin
admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'favorite_cuisine')
    search_fields = ('user__username', 'favorite_cuisine')
    list_filter = ('favorite_cuisine',)

@admin.register(UserFollowing)
class UserFollowingAdmin(admin.ModelAdmin):
    list_display = ('user', 'followed_user', 'created_at')
    search_fields = ('user__username', 'followed_user__username')
    list_filter = ('created_at',)
