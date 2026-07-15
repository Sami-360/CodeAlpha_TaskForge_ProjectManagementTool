from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = [
        'username',
        'email',
        'first_name',
        'last_name',
        'is_active',
        'is_staff',
        'date_joined',
    ]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    ordering = ['username']
    readonly_fields = [*UserAdmin.readonly_fields, 'date_joined', 'updated_at']
    fieldsets = [
        *UserAdmin.fieldsets,
        ('Profile', {'fields': ('avatar', 'bio', 'updated_at')}),
    ]
    add_fieldsets = [
        *UserAdmin.add_fieldsets,
        (
            'Personal information',
            {
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'avatar',
                    'bio',
                )
            },
        ),
    ]
