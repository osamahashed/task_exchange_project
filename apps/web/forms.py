from __future__ import annotations

import os

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.forms.widgets import ClearableFileInput

from django.utils import timezone
from apps.accounts.models import Invitation, SiteSetting

from apps.accounts.utils import normalize_invite_code
try:
    from apps.courses.models import Course
except Exception:  # pragma: no cover - يحمي الاستيراد من الفشل في البيئات الناقصة
    Course = None

try:
    from apps.assignments.models import Assignment
except Exception:  # pragma: no cover
    Assignment = None

try:
    from apps.submissions.models import Submission, SubmissionAttachment, ALLOWED_EXTS, MAX_BYTES
except Exception:  # pragma: no cover
    Submission = None
    SubmissionAttachment = None
    ALLOWED_EXTS = {".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".zip"}
    MAX_BYTES = 10 * 1024 * 1024

UserModel = get_user_model()


class MultiFileInput(ClearableFileInput):
    allow_multiple_selected = True

    def __init__(self, attrs: dict | None = None):
        base_attrs = {"multiple": True, "class": "form-control", "name": "files"}
        if attrs:
            base_attrs.update(attrs)
        super().__init__(attrs=base_attrs)

    def format_value(self, value):
        return []


class SystemSettingForm(forms.ModelForm):
    admin_password = forms.CharField(
        label="كلمة مرور المشرف",
        widget=forms.PasswordInput(attrs={"class": "form-control"}),
    )

    class Meta:
        model = SiteSetting
        fields = ["teacher_code", "admin_access_code"]
        widgets = {
            "teacher_code": forms.TextInput(attrs={"class": "form-control"}),
            "admin_access_code": forms.TextInput(attrs={"class": "form-control"}),
        }
        labels = {
            "teacher_code": "رمز المعلم",
            "admin_access_code": "رمز الوصول الإداري",
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

    def clean_admin_password(self) -> str:
        password = self.cleaned_data.get("admin_password", "")
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated or not user.check_password(password):
            raise forms.ValidationError("كلمة المرور الإدارية غير صحيحة.")
        return password

    def save(self, commit: bool = True) -> SiteSetting:
        instance = super().save(commit=False)
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            instance.updated_by = user
        if commit:
            instance.save()
        return instance


class AdminAccessForm(forms.Form):
    code = forms.CharField(
        label="رمز التحقق",
        max_length=128,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "off"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._settings = SiteSetting.objects.first()

    def clean_code(self) -> str:
        value = self.cleaned_data.get("code", "").strip()
        expected = getattr(self._settings, "admin_access_code", "")
        if not value or value != expected:
            raise forms.ValidationError("الرمز غير صحيح، يرجى المحاولة مجدداً.")
        return value


if Course is not None:
    class CourseForm(forms.ModelForm):
        class Meta:
            model = Course
            fields = "__all__"
            widgets = {
                "name": forms.TextInput(attrs={"class": "form-control"}),
                "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            }
else:  # pragma: no cover
    class CourseForm(forms.Form):
        pass


if Assignment is not None:
    class AssignmentCreateForm(forms.ModelForm):
        class Meta:
            model = Assignment
            fields = ["course", "title", "due_date", "description", "attachment", "external_link"]
            widgets = {
                "title": forms.TextInput(attrs={"class": "form-control"}),
                "due_date": forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control"}),
                "description": forms.Textarea(attrs={"rows": 4, "class": "form-control"}),
                "external_link": forms.URLInput(attrs={"class": "form-control"}),
            }

        def clean_attachment(self):
            file_obj = self.cleaned_data.get("attachment")
            if not file_obj:
                return file_obj
            ext = os.path.splitext(file_obj.name)[1].lower()
            if ext not in ALLOWED_EXTS:
                raise forms.ValidationError("صيغة الملف غير مدعومة. الصيغ المسموح بها: pdf/doc/docx/txt/png/jpg/jpeg/zip")
            if file_obj.size > MAX_BYTES:
                raise forms.ValidationError("حجم الملف كبير. الحد الأعلى 10MB.")
            return file_obj
else:  # pragma: no cover
    class AssignmentCreateForm(forms.Form):
        pass


class SubmissionUploadForm(forms.Form):
    files = forms.FileField(
        label="الملفات",
        required=False,
        widget=MultiFileInput(),
        help_text="الامتدادات المسموح بها: pdf/doc/docx/txt/png/jpg/jpeg/zip بحد أقصى 10MB لكل ملف.",
    )

    _default_allowed = {".pdf", ".doc", ".docx", ".txt", ".png", ".jpg", ".jpeg", ".zip"}
    _no_files_message = "يجب رفع ملف واحد على الأقل."
    _generic_error_message = "يرجى تصحيح الملفات المحددة ثم إعادة المحاولة."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        allowed_pool = ALLOWED_EXTS if isinstance(ALLOWED_EXTS, (set, tuple, list)) else self._default_allowed
        self.allowed_exts = {
            ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
            for ext in allowed_pool
        } or set(self._default_allowed)
        self.allowed_label = '/'.join(sorted(ext.strip('.') for ext in self.allowed_exts))
        max_bytes = MAX_BYTES if isinstance(MAX_BYTES, int) and MAX_BYTES > 0 else 10 * 1024 * 1024
        self.max_bytes = max_bytes
        size_mb = max(1, round(self.max_bytes / (1024 * 1024)))
        self.size_label = f"{size_mb}MB"
        self.fields['files'].help_text = (
            f"الامتدادات المسموح بها: {self.allowed_label} "
            f"بحد أقصى {self.size_label} لكل ملف."
        )

    def clean(self):
        cleaned = super().clean()
        field_key = self.add_prefix('files')
        uploaded = []
        if hasattr(self.files, 'getlist'):
            uploaded = [f for f in self.files.getlist(field_key) if f]
        if not uploaded:
            self.add_error('files', self._no_files_message)
            raise forms.ValidationError(self._no_files_message)

        errors: list[str] = []
        for file_obj in uploaded:
            name = (getattr(file_obj, 'name', '') or '').strip() or "بدون اسم"
            ext = os.path.splitext(name)[1].lower()
            size = getattr(file_obj, 'size', 0) or 0
            if ext not in self.allowed_exts:
                errors.append(
                    f"الملف {name} غير مسموح به. الصيغ المقبولة: {self.allowed_label}."
                )
            if size > self.max_bytes:
                errors.append(
                    f"الملف {name} يتجاوز الحد المسموح ({self.size_label})."
                )
        for message in errors:
            self.add_error('files', message)
        if errors:
            raise forms.ValidationError(self._generic_error_message)
        cleaned['files_list'] = uploaded
        return cleaned


class InviteCreateForm(forms.ModelForm):
    code = forms.CharField(
        label="رمز الدعوة (اختياري)",
        max_length=16,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "أدخل أحرفاً أو أرقام", "autocomplete": "off"}
        ),
    )
    max_uses = forms.IntegerField(
        label="عدد الاستخدامات",
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 1}),
    )
    expires_at = forms.DateTimeField(
        label="تاريخ الانتهاء",
        required=False,
        widget=forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
    )
    is_active = forms.BooleanField(
        label="مفعل",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Invitation
        fields = ["code", "max_uses", "expires_at", "is_active"]

    def clean_code(self) -> str:
        value = normalize_invite_code(self.cleaned_data.get("code", ""))
        if not value:
            return ""
        if Invitation.objects.filter(code=value).exists():
            raise forms.ValidationError("رمز الدعوة من تقدم موجود.")
        return value

    def clean_expires_at(self):
        value = self.cleaned_data.get("expires_at")
        if not value:
            return None
        if timezone.is_naive(value):
            value = timezone.make_aware(value, timezone.get_current_timezone())
        if value <= timezone.now():
            raise forms.ValidationError("رمز الدعوة يجب ألا يكون منتهياً.")
        return value

    def save(self, created_by=None, commit: bool = True):
        instance = super().save(commit=False)
        code = self.cleaned_data.get("code")
        instance.code = code or Invitation.generate_code()
        if created_by is not None:
            instance.created_by = created_by
        if instance.max_uses == 0:
            instance.max_uses = None
        if commit:
            instance.save()
        return instance


class InviteAcceptForm(forms.Form):
    code = forms.CharField(
        label="رمز الدعوة",
        max_length=16,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "أدخل الرمز"}),
    )


class ConversationStartForm(forms.Form):
    teacher = forms.ModelChoiceField(
        queryset=UserModel.objects.filter(profile__role="teacher").order_by("username") if hasattr(UserModel, "objects") else User.objects.none(),
        label="المعلم",
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    assignment = forms.ModelChoiceField(
        queryset=Assignment.objects.all().order_by("-due_date") if Assignment else [],
        required=False,
        label="الواجب (اختياري)",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, **kwargs):
        self.request_user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        role = getattr(getattr(self.request_user, "profile", None), "role", None)
        if role == "teacher":
            self.fields.pop("teacher", None)
            student_qs = UserModel.objects.filter(profile__role="student").order_by("username") if hasattr(UserModel, "objects") else User.objects.none()
            self.fields["student"] = forms.ModelChoiceField(
                queryset=student_qs,
                label="الطالب",
                widget=forms.Select(attrs={"class": "form-select"}),
            )
        else:
            self.fields["teacher"].required = True


class MessageForm(forms.Form):
    text = forms.CharField(
        label="الرسالة",
        widget=forms.Textarea(
            attrs={"rows": 2, "class": "form-control", "placeholder": "اكتب رسالتك هنا..."}
        ),
    )


__all__ = [
    "MultiFileInput",
    "SystemSettingForm",
    "AdminAccessForm",
    "CourseForm",
    "AssignmentCreateForm",
    "SubmissionUploadForm",
    "InviteCreateForm",
    "InviteAcceptForm",
    "ConversationStartForm",
    "MessageForm",
]
