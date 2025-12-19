from django.contrib import admin

from .models import Invitation, InvitationUsage, Profile, SiteSetting


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "is_verified_student")
    search_fields = ("user__username", "role")
    list_filter = ("role", "is_verified_student")


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ("teacher_code", "admin_access_code", "updated_at", "updated_by")
    readonly_fields = ("updated_at", "updated_by")


class InvitationUsageInline(admin.TabularInline):
    model = InvitationUsage
    extra = 0
    can_delete = False
    readonly_fields = ("user", "used_at")


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ("code", "created_by", "is_active", "uses_count", "max_uses", "expires_at", "created_at")
    list_filter = ("is_active", "expires_at", "created_at")
    search_fields = ("code", "created_by__username")
    readonly_fields = ("uses_count", "created_at")
    ordering = ("-created_at",)
    inlines = [InvitationUsageInline]


__all__ = [
    "ProfileAdmin",
    "SiteSettingAdmin",
    "InvitationAdmin",
]
