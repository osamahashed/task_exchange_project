from django.db import models


class Course(models.Model):
    name = models.CharField("اسم المقرر", max_length=200)
    description = models.TextField("الوصف", blank=True)

    def __str__(self) -> str:
        return self.name

    class Meta:
        verbose_name = "مقرر"
        verbose_name_plural = "مقررات"
        ordering = ["name"]
