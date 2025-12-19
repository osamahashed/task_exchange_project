from django.contrib.auth import get_user_model
from django.db import models

from apps.assignments.models import Assignment

User = get_user_model()


class Conversation(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conv_as_student")
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="conv_as_teacher")
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("student", "teacher", "assignment"),)
        ordering = ["-created_at"]

    def __str__(self) -> str:
        suffix = f" | {self.assignment.title}" if self.assignment_id else ""
        return f"{self.student.username} ↔ {self.teacher.username}{suffix}"

    def is_participant(self, user) -> bool:
        return bool(user and user.is_authenticated and user.id in (self.student_id, self.teacher_id))


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages_sent")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read_by_student = models.BooleanField(default=False)
    is_read_by_teacher = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"msg#{self.pk} by {self.sender.username}"

    def mark_read_for(self, user) -> None:
        if not user or not user.is_authenticated:
            return
        role = getattr(getattr(user, "profile", None), "role", "student" if not user.is_staff else "teacher")
        if role == "student" and not self.is_read_by_student:
            self.is_read_by_student = True
            self.save(update_fields=["is_read_by_student"])
        elif role != "student" and not self.is_read_by_teacher:
            self.is_read_by_teacher = True
            self.save(update_fields=["is_read_by_teacher"])

    def is_read_for(self, user) -> bool:
        role = getattr(getattr(user, "profile", None), "role", "student" if not user.is_staff else "teacher")
        return self.is_read_by_student if role == "student" else self.is_read_by_teacher
