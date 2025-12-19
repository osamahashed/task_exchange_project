from functools import wraps

from django.contrib import messages
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse

from apps.accounts.utils import is_student_activated


def teacher_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse("accounts:login")
            return redirect(f"{login_url}?{REDIRECT_FIELD_NAME}={request.path}")
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        profile = getattr(request.user, "profile", None)
        if not profile or profile.role != "teacher":
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            login_url = reverse("accounts:login")
            return redirect(f"{login_url}?{REDIRECT_FIELD_NAME}={request.path}")
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return _wrapped


def admin_gate_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.session.get("admin_gate_ok"):
            return redirect("web:admin_access")
        return view_func(request, *args, **kwargs)

    return _wrapped


def student_verified_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        if profile and profile.role == "student" and not is_student_activated(request.user):
            request.session["activation_redirect"] = request.get_full_path()
            messages.warning(
                request,
                "يجب تفعيل الحساب برمز دعوة قبل المتابعة.",
            )
            return redirect("web:invite_accept")
        return view_func(request, *args, **kwargs)

    return _wrapped
