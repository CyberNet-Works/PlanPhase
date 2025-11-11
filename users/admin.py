from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Show all fields except password
    list_display = (
        "id",
        "username",
        "email",
        "first_name",
        "last_name",
        "phone",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
        "date_joined",
        "status",
        "campaign_id",  # if FK
        "campaign_name",
    )

    # ✅ Searchable fields (text-based)
    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name",
        "phone",
        "status",
        "allowed_ips",  # if text/JSON
        "campaign_id",
        "campaign_name",  # if FK has name field
    )

    # ✅ Side filters for quick filtering
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "status",  # custom status
        "roles",
        "teams",  # ManyToMany
        "campaign_id",  # foreign key
        "campaign_name",
        "date_joined",
        "last_login",
    )

    # ✅ Read only but visible timestamps
    readonly_fields = ("last_login", "date_joined")

    ordering = ("id",)
