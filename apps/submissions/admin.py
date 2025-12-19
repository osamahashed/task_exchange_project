from django.contrib import admin

from .models import Submission, SubmissionAttachment


class SubmissionAttachmentInline(admin.TabularInline):
    model = SubmissionAttachment
    extra = 0
    readonly_fields = ("size_bytes", "sha256")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "assignment", "user", "grade", "created_at")
    list_filter = ("assignment", "user", "grade")
    search_fields = ("user__username", "assignment__title")
    inlines = [SubmissionAttachmentInline]


@admin.register(SubmissionAttachment)
class SubmissionAttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "size_bytes", "sha256")
    search_fields = ("submission__user__username", "sha256")
