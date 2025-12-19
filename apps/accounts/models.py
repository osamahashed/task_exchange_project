import secrets

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

User = get_user_model()


class Profile(models.Model):
    ROLE_CHOICES = [
        ("student", "\u0637\u0627\u0644\u0628"),
        ("teacher", "\u0645\u0639\u0644\u0645"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="student")
    is_verified_student = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Profile({self.user.username})"

    class Meta:
        ordering = ["user__username"]
        verbose_name = "\u0645\u0644\u0641 \u0645\u0633\u062a\u062e\u062f\u0645"
        verbose_name_plural = "\u0645\u0644\u0641\u0627\u062a \u0627\u0644\u0645\u0633\u062a\u062e\u062f\u0645\u064a\u0646"


class SiteSetting(models.Model):
    teacher_code = models.CharField(max_length=64, default="TEACH-2025")
    admin_access_code = models.CharField(max_length=64, default="ROOT-2025")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )

    def __str__(self) -> str:
        return "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0646\u0638\u0627\u0645"

    class Meta:
        verbose_name = "\u0625\u0639\u062f\u0627\u062f \u0627\u0644\u0646\u0638\u0627\u0645"
        verbose_name_plural = "\u0625\u0639\u062f\u0627\u062f\u0627\u062a \u0627\u0644\u0646\u0638\u0627\u0645"
        ordering = ["-updated_at"]


class Invitation(models.Model):
    code = models.CharField(max_length=16, unique=True, db_index=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="invite_codes",
        verbose_name="\u0623\u0646\u0634\u0626 \u0628\u0648\u0627\u0633\u0637\u0629",
    )
    is_active = models.BooleanField(default=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    uses_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    @staticmethod
    def generate_code() -> str:
        return secrets.token_hex(4).upper()

    def __str__(self) -> str:
        teacher_name = getattr(self.created_by, "username", "")
        return f"{self.code} by {teacher_name}"

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "\u0631\u0645\u0632 \u0627\u0644\u062f\u0639\u0648\u0629"
        verbose_name_plural = "\u0631\u0645\u0648\u0632 \u0627\u0644\u062f\u0639\u0648\u0629"

    @property
    def remaining_uses(self):
        if self.max_uses is None:
            return None
        return max(self.max_uses - self.uses_count, 0)

    def is_expired(self) -> bool:
        return bool(self.expires_at and self.expires_at <= timezone.now())

    def can_be_used(self) -> bool:
        if not self.is_active:
            return False
        if self.is_expired():
            return False
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            return False
        return True

    @transaction.atomic
    def consume_code(self, user: User):
        profile = getattr(user, "profile", None)
        if not profile or profile.role != "student":
            raise ValidationError("\u0647\u0630\u0627 \u0627\u0644\u0631\u0645\u0632 \u0645\u062e\u0635\u0635 \u0644\u0644\u0637\u0644\u0627\u0628 \u0641\u0642\u0637.")
        if not self.can_be_used():
            raise ValidationError("\u0631\u0645\u0632 \u0627\u0644\u062f\u0639\u0648\u0629 \u063a\u064a\u0631 \u0645\u062a\u0627\u062d \u0644\u0644\u0627\u0633\u062a\u062e\u062f\u0627\u0645.")
        usage_exists = self.usages.filter(user=user).exists()
        if usage_exists:
            raise ValidationError("\u0644\u0642\u062f \u0627\u0633\u062a\u062e\u062f\u0645\u062a \u0631\u0645\u0632 \u062f\u0639\u0648\u0629 \u0645\u0646 \u0642\u0628\u0644.")
        usage = InvitationUsage.objects.create(invitation=self, user=user)
        self.uses_count += 1
        if self.max_uses is not None and self.uses_count >= self.max_uses:
            self.is_active = False
        self.save(update_fields=["uses_count", "is_active"])
        if not profile.is_verified_student:
            profile.is_verified_student = True
            profile.save(update_fields=["is_verified_student"])
        return usage

    @staticmethod
    @transaction.atomic
    def consume_code_static(raw_code: str, user: User):
        if not raw_code:
            raise ValidationError("\u064a\u0631\u062c\u0649 \u0625\u062f\u062e\u0627\u0644 \u0631\u0645\u0632 \u0627\u0644\u062f\u0639\u0648\u0629.")
        code = raw_code.strip().upper()
        invitation = (
            Invitation.objects.select_for_update()
            .filter(code=code)
            .first()
        )
        if not invitation:
            raise ValidationError("\u0631\u0645\u0632 \u0627\u0644\u062f\u0639\u0648\u0629 \u063a\u064a\u0631 \u0635\u062d\u064a\u062d.")
        return invitation.consume_code(user)


class InvitationUsage(models.Model):
    invitation = models.ForeignKey(
        Invitation,
        on_delete=models.CASCADE,
        related_name="usages",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="invite_code_usages",
    )
    used_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("invitation", "user")
        ordering = ["-used_at"]
        verbose_name = "\u0627\u0633\u062a\u062e\u062f\u0627\u0645 \u0631\u0645\u0632 \u062f\u0639\u0648\u0629"
        verbose_name_plural = "\u0627\u0633\u062a\u062e\u062f\u0627\u0645\u0627\u062a \u0631\u0645\u0648\u0632 \u0627\u0644\u062f\u0639\u0648\u0629"

    def __str__(self) -> str:
        return f"{self.user.username} -> {self.invitation.code}"


__all__ = [
    "Profile",
    "SiteSetting",
    "Invitation",
    "InvitationUsage",
]
