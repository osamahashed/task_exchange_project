import hashlib
import os

from django.contrib.auth import get_user_model
from django.db import models

from apps.assignments.models import Assignment

User = get_user_model()

ALLOWED_EXTS = {".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".zip"}
MAX_BYTES = 10 * 1024 * 1024


def _sha256_file(file_obj) -> str:
    hasher = hashlib.sha256()
    for chunk in file_obj.chunks():
        hasher.update(chunk)
    return hasher.hexdigest()


class Submission(models.Model):
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
        verbose_name="الواجب",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="submissions",
        verbose_name="الطالب",
    )
    file = models.FileField("ملف مرفق", upload_to="submission_files/", blank=True, null=True)
    grade = models.IntegerField("التقدير", blank=True, null=True)
    feedback = models.TextField("ملاحظات", blank=True)
    created_at = models.DateTimeField("تاريخ الإرسال", auto_now_add=True)

    def __str__(self) -> str:
        return f"Submission #{self.pk} by {self.user.username} for {self.assignment.title}"

    class Meta:
        verbose_name = "تسليم"
        verbose_name_plural = "تسليمات"
        ordering = ["-created_at"]


class SubmissionAttachment(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="submission_files/")
    size_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True)

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.file and self.file.size > MAX_BYTES:
            raise ValidationError("حجم الملف يتجاوز 10MB.")
        ext = os.path.splitext(self.file.name)[1].lower()
        if ext not in ALLOWED_EXTS:
            raise ValidationError("نوع الملف غير مسموح. المسموح: pdf/doc/docx/txt/png/jpg/jpeg/zip")

    def save(self, *args, **kwargs):
        if self.file and not self.sha256:
            self.size_bytes = self.file.size
            self.file.seek(0)
            self.sha256 = _sha256_file(self.file)
            self.file.seek(0)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Attachment #{self.pk} for submission {self.submission_id}"

    class Meta:
        ordering = ["-id"]
        verbose_name = "ملف مرفق"
        verbose_name_plural = "ملفات مرفقة"
