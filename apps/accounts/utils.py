from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model

UserModel = get_user_model()


def is_student_activated(user: Optional[UserModel]) -> bool:
    profile = getattr(user, "profile", None)
    return bool(profile and profile.role == "student" and profile.is_verified_student)


def normalize_invite_code(value: str) -> str:
    return (value or "").strip().upper()


__all__ = [
    "is_student_activated",
    "normalize_invite_code",
]
