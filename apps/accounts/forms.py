from django import forms
from django.contrib.auth import authenticate, get_user_model

from .models import Profile, SiteSetting

User = get_user_model()


class RegisterForm(forms.Form):
    username = forms.CharField(label="اسم المستخدم", max_length=150)
    email = forms.EmailField(label="البريد الإلكتروني", required=False)
    password1 = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput)
    password2 = forms.CharField(label="تأكيد كلمة المرور", widget=forms.PasswordInput)
    role = forms.ChoiceField(label="الدور", choices=Profile.ROLE_CHOICES, widget=forms.Select)
    teacher_code = forms.CharField(
        label="رمز المعلم",
        required=False,
        help_text="استخدم الرمز السري للانضمام كمعلم.",
    )

    def clean_username(self) -> str:
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("اسم المستخدم مسجل مسبقاً.")
        return username

    def clean(self) -> dict:
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("كلمتا المرور غير متطابقتين.")

        role = cleaned_data.get("role")
        teacher_code = cleaned_data.get("teacher_code", "").strip()
        if role == "teacher":
            expected_code = self._get_teacher_code()
            if not teacher_code:
                raise forms.ValidationError("الرجاء إدخال رمز المعلم.")
            if teacher_code != expected_code:
                raise forms.ValidationError("رمز المعلم غير صحيح.")
        return cleaned_data

    def save(self) -> User:
        username = self.cleaned_data["username"].strip()
        email = self.cleaned_data.get("email", "").strip()
        password = self.cleaned_data["password1"]
        role = self.cleaned_data["role"]

        user = User.objects.create_user(username=username, email=email, password=password)
        user.refresh_from_db()
        profile = user.profile
        profile.role = role
        if role == "teacher":
            profile.is_verified_student = False
        profile.save()
        return user

    def _get_teacher_code(self) -> str:
        setting = SiteSetting.objects.first()
        if setting and setting.teacher_code:
            return setting.teacher_code
        return SiteSetting._meta.get_field("teacher_code").default


class LoginForm(forms.Form):
    username = forms.CharField(label="اسم المستخدم")
    password = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput)

    def clean(self) -> dict:
        cleaned_data = super().clean()
        username = cleaned_data.get("username")
        password = cleaned_data.get("password")
        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise forms.ValidationError("بيانات تسجيل الدخول غير صحيحة.")
            cleaned_data["user"] = user
        return cleaned_data
