from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile użytkowników'

# Rozszerzenie standardowego UserAdmin, aby zawierał profil
class CustomUserAdmin(UserAdmin):
    inlines = (UserProfileInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_fridge_name')
    
    def get_fridge_name(self, obj):
        return obj.profile.fridge_name if hasattr(obj, 'profile') else ""
    get_fridge_name.short_description = 'Nazwa lodówki'

# Wyrejestrowanie standardowego UserAdmin
admin.site.unregister(User)
# Zarejestrowanie naszego CustomUserAdmin
admin.site.register(User, CustomUserAdmin)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'fridge_name', 'favorite_cuisine')
    search_fields = ('user__username', 'fridge_name', 'favorite_cuisine')
    list_filter = ('favorite_cuisine',)
