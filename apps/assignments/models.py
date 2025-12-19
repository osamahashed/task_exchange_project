from django.db import models

from apps.courses.models import Course


class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="assignments", verbose_name="المقرر")
    title = models.CharField("عنوان الواجب", max_length=255)
    due_date = models.DateTimeField("موعد التسليم")
    description = models.TextField("وصف الواجب", blank=True)
    attachment = models.FileField(upload_to="assignment_files/", blank=True, null=True)
    external_link = models.URLField(blank=True)

    def __str__(self) -> str:
        return f"{self.title} ({self.course.name})"

    class Meta:
        ordering = ["-due_date"]
        verbose_name = "واجب"
        verbose_name_plural = "واجبات"
