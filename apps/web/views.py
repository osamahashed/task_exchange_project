from collections import Counter

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.db import transaction
from django.db.utils import OperationalError, ProgrammingError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST
from django.utils import timezone

from apps.accounts.models import Invitation, SiteSetting
from apps.assignments.models import Assignment
from apps.courses.models import Course
from apps.messaging.models import Conversation, Message
from apps.submissions.models import Submission, SubmissionAttachment

from .decorators import (
    admin_gate_required,
    admin_required,
    student_verified_required,
    teacher_required,
)
from .forms import (
    AdminAccessForm,
    AssignmentCreateForm,
    ConversationStartForm,
    CourseForm,
    InviteAcceptForm,
    MessageForm,
    SubmissionUploadForm,
    SystemSettingForm,
)

User = get_user_model()


class GradeForm(forms.Form):
    grade = forms.IntegerField(
        label="الدرجة",
        min_value=0,
        max_value=100,
        required=False,
        widget=forms.NumberInput(attrs={"class": "form-control", "min": 0, "max": 100}),
    )
    feedback = forms.CharField(
        label="ملاحظات",
        required=False,
        widget=forms.Textarea(
            attrs={"rows": 3, "class": "form-control", "placeholder": "ملاحظات للطالب (اختياري)"}
        ),
    )


def home(request):
    return render(request, "web/home.html")

@login_required
def student_home(request):
    try:
        context = {
            "courses_count": Course.objects.count(),
            "assignments_count": Assignment.objects.count(),
            "submissions_count": Submission.objects.filter(user=request.user).count(),
        }
    except (OperationalError, ProgrammingError):
        messages.info(request, "سيتم عرض الإحصائيات بعد إتمام تهيئة قاعدة البيانات.")
        context = {"courses_count": 0, "assignments_count": 0, "submissions_count": 0}
    return render(request, "web/student_home.html", context)


@login_required
@teacher_required
def teacher_home(request):
    try:
        context = {
            "total_submissions": Submission.objects.count(),
            "pending_submissions": Submission.objects.filter(grade__isnull=True).count(),
            "assignments_count": Assignment.objects.count(),
        }
    except (OperationalError, ProgrammingError):
        messages.info(request, "سيتم تفعيل لوحة المعلم بعد ترحيل الجداول.")
        context = {"total_submissions": 0, "pending_submissions": 0, "assignments_count": 0}
    return render(request, "web/teacher_home.html", context)


@login_required
def courses_list(request):
    try:
        courses = Course.objects.all()
    except (OperationalError, ProgrammingError):
        messages.info(request, "ستظهر المقررات هنا بعد تهيئة قاعدة البيانات.")
        courses = Course.objects.none()
    return render(request, "web/courses_list.html", {"courses": courses})

@login_required
def assignments_list(request):
    try:
        assignments = Assignment.objects.select_related("course").all()
        profile = getattr(request.user, "profile", None)
        is_teacher = profile.role == "teacher" if profile else False
    except (OperationalError, ProgrammingError):
        messages.info(request, "ستظهر الواجبات بعد تهيئة قاعدة البيانات.")
        assignments = Assignment.objects.none()
        is_teacher = False
    return render(
        request,
        "web/assignments_list.html",
        {
            "assignments": assignments,
            "is_teacher": is_teacher,
        },
    )

@login_required
def assignment_detail(request, pk):
    try:
        assignment = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    except (OperationalError, ProgrammingError):
        messages.info(request, "تعذر تحميل تفاصيل الواجب قبل إعداد قاعدة البيانات.")
        return redirect("web:assignments_list")
    return render(request, "web/assignment_detail.html", {"assignment": assignment})

@login_required
def submissions_list(request):
    try:
        submissions = (
            Submission.objects.select_related("assignment", "assignment__course")
            .prefetch_related("attachments")
            .filter(user=request.user)
            .order_by("-created_at")
        )
    except (OperationalError, ProgrammingError):
        messages.info(request, "قائمة التسليمات ستظهر بعد تفعيل قاعدة البيانات.")
        submissions = Submission.objects.none()
    return render(request, "web/submissions_list.html", {"submissions": submissions})

@login_required
@student_verified_required
def submission_create(request, assignment_id):
    try:
        assignment = get_object_or_404(Assignment, pk=assignment_id)
    except (OperationalError, ProgrammingError):
        messages.info(request, "الواجبات ستتوفر بعد إتمام تهيئة قاعدة البيانات.")
        return redirect("web:assignments_list")

    profile = getattr(request.user, "profile", None)
    if profile and profile.role == "teacher":
        raise PermissionDenied("المدرس لا ينشئ تسليمات.")
    if not profile or profile.role != "student":
        raise PermissionDenied("هذه الصفحة متاحة للطلاب فقط.")

    if assignment.due_date and assignment.due_date < timezone.now():
        messages.error(request, "انتهى موعد تسليم هذا الواجب.")
        return redirect("web:assignments_list")

    if hasattr(assignment, "is_active") and not getattr(assignment, "is_active"):
        messages.error(request, "هذا الواجب غير متاح حالياً.")
        return redirect("web:assignments_list")

    if request.method == "POST":
        form = SubmissionUploadForm(request.POST, request.FILES)
        if form.is_valid():
            files = form.cleaned_data.get("files_list", [])
            try:
                with transaction.atomic():
                    submission = Submission.objects.create(assignment=assignment, user=request.user)
                    for file_obj in files:
                        attachment = SubmissionAttachment(submission=submission, file=file_obj)
                        attachment.full_clean()
                        attachment.save()
            except ValidationError as exc:
                error_messages = []
                if hasattr(exc, "message_dict"):
                    for values in exc.message_dict.values():
                        error_messages.extend(values)
                else:
                    error_messages.extend(exc.messages)
                for message_text in error_messages:
                    form.add_error("files", message_text)
                messages.error(request, "حدث خطأ أثناء معالجة الملفات. يرجى تصحيح الأخطاء.")
            except (OperationalError, ProgrammingError):
                messages.error(request, "حدث خطأ أثناء معالجة الملفات. يرجى تصحيح الأخطاء.")
            else:
                messages.success(request, f"تم رفع {len(files)} ملف/مرفق بنجاح.")
                return redirect("web:submissions_list")
        else:
            messages.error(request, "حدث خطأ أثناء معالجة الملفات. يرجى تصحيح الأخطاء.")
    else:
        form = SubmissionUploadForm()

    return render(request, "web/submission_form.html", {"form": form, "assignment": assignment})


@login_required
@teacher_required
def teacher_submissions(request):
    try:
        submissions = (
            Submission.objects.select_related("assignment", "assignment__course", "user")
            .prefetch_related("attachments")
            .order_by("assignment__due_date", "-created_at")
        )
    except (OperationalError, ProgrammingError):
        messages.info(request, "ستظهر التسليمات بعد تهيئة قاعدة البيانات.")
        submissions = Submission.objects.none()
        duplicates = Counter()
    else:
        duplicates = Counter()
        for submission in submissions:
            for attachment in submission.attachments.all():
                if attachment.sha256:
                    duplicates[attachment.sha256] += 1
    return render(
        request,
        "web/teacher_submissions.html",
        {
            "submissions": submissions,
            "dup_map": duplicates,
        },
    )

@login_required
@teacher_required
def course_create(request):
    try:
        form = CourseForm(request.POST or None)
    except (OperationalError, ProgrammingError):
        messages.info(request, "سيصبح إنشاء المقررات متاحاً بعد تهيئة قاعدة البيانات.")
        return redirect("web:courses_list")

    if request.method == "POST":
        if form.is_valid():
            try:
                form.save()
            except (OperationalError, ProgrammingError):
                messages.error(request, "تعذّر حفظ المقرر. حاول مجدداً بعد تهيئة قاعدة البيانات.")
            else:
                messages.success(request, "تم حفظ المقرر بنجاح.")
                return redirect("web:courses_list")
        else:
            messages.error(request, "يرجى تصحيح الحقول المظللة أدناه.")
    return render(request, "web/course_form.html", {"form": form, "title": "إضافة مقرر"})

@login_required
@teacher_required
def assignment_create(request):
    if request.method == "POST":
        try:
            form = AssignmentCreateForm(request.POST, request.FILES)
        except (OperationalError, ProgrammingError):
            messages.info(request, "سيصبح إنشاء الواجبات متاحاً بعد تهيئة قاعدة البيانات.")
            return redirect("web:assignments_list")
        if form.is_valid():
            try:
                form.save()
            except (OperationalError, ProgrammingError):
                messages.error(request, "تعذّر حفظ الواجب. حاول مجدداً بعد تهيئة قاعدة البيانات.")
            else:
                messages.success(request, "تم حفظ الواجب بنجاح.")
                return redirect("web:assignments_list")
        else:
            messages.error(request, "يرجى تصحيح الحقول المظللة أدناه.")
    else:
        try:
            form = AssignmentCreateForm()
        except (OperationalError, ProgrammingError):
            messages.info(request, "سيصبح إنشاء الواجبات متاحاً بعد تهيئة قاعدة البيانات.")
            return redirect("web:assignments_list")
    return render(request, "web/assignment_form.html", {"form": form, "title": "إضافة واجب"})


@login_required
@teacher_required
def grade_submission(request, pk: int):
    try:
        submission = get_object_or_404(
            Submission.objects.select_related("assignment", "user").prefetch_related("attachments"),
            pk=pk,
        )
    except (OperationalError, ProgrammingError):
        messages.info(request, "سيتم تفعيل درجات الواجبات بعد تهيئة قاعدة البيانات.")
        return redirect("web:teacher_submissions")

    if request.method == "POST":
        form = GradeForm(request.POST)
        if form.is_valid():
            submission.grade = form.cleaned_data["grade"]
            submission.feedback = form.cleaned_data["feedback"]
            try:
                submission.save(update_fields=["grade", "feedback"])
            except (OperationalError, ProgrammingError):
                messages.error(request, "تعذّر حفظ التقييم. حاول لاحقاً بعد تهيئة قاعدة البيانات.")
            else:
                messages.success(request, "تم حفظ التقييم بنجاح.")
                return redirect("web:teacher_submissions")
        else:
            messages.error(request, "يرجى مراجعة الحقول ثم المحاولة مجدداً.")
    else:
        form = GradeForm(
            initial={
                "grade": submission.grade,
                "feedback": submission.feedback,
            }
        )

    return render(
        request,
        "web/grade_form.html",
        {
            "form": form,
            "submission": submission,
        },
    )


@login_required
@admin_required
def admin_access_view(request):
    if request.session.get("admin_gate_ok"):
        return redirect("web:admin_panel")

    try:
        form = AdminAccessForm(request.POST or None)
    except (OperationalError, ProgrammingError):
        messages.info(request, "سيصبح الوصول إلى لوحة الإدارة متاحاً بعد تهيئة قاعدة البيانات.")
        return redirect("web:home")

    if request.method == "POST":
        if form.is_valid():
            request.session["admin_gate_ok"] = True
            messages.success(request, "تم التحقق من رمز الإدارة بنجاح.")
            return redirect("web:admin_panel")
        messages.error(request, "رمز الوصول غير صحيح. يرجى المحاولة من جديد.")

    return render(request, "web/admin/admin_access.html", {"form": form})

@login_required
@admin_required
@admin_gate_required
def admin_panel(request):
    try:
        context = {
            "courses_count": Course.objects.count(),
            "assignments_count": Assignment.objects.count(),
            "submissions_count": Submission.objects.count(),
            "pending_submissions": Submission.objects.filter(grade__isnull=True).count(),
            "users_count": User.objects.count(),
        }
    except (OperationalError, ProgrammingError):
        messages.info(request, "ستعمل لوحة الإدارة بعد تهيئة قاعدة البيانات.")
        context = {
            "courses_count": 0,
            "assignments_count": 0,
            "submissions_count": 0,
            "pending_submissions": 0,
            "users_count": 0,
        }
    return render(request, "web/admin/admin_dashboard.html", context)

@login_required
@admin_required
@admin_gate_required
def admin_settings(request):
    defaults = {
        "teacher_code": SiteSetting._meta.get_field("teacher_code").default,
        "admin_access_code": SiteSetting._meta.get_field("admin_access_code").default,
    }
    try:
        settings_obj, _ = SiteSetting.objects.get_or_create(id=1, defaults=defaults)
    except (OperationalError, ProgrammingError):
        messages.info(request, "سيصبح إعداد رموز الإدارة متاحاً بعد تهيئة قاعدة البيانات.")
        return redirect("web:admin_panel")

    if request.method == "POST":
        form = SystemSettingForm(request.POST, instance=settings_obj, request=request)
        if form.is_valid():
            try:
                form.save()
            except (OperationalError, ProgrammingError):
                messages.error(request, "تعذّر حفظ الإعدادات. حاول لاحقاً بعد تهيئة قاعدة البيانات.")
            else:
                messages.success(request, "تم تحديث الإعدادات بنجاح.")
                return redirect("web:admin_settings")
        else:
            messages.error(request, "يرجى تصحيح الحقول المظللة أدناه.")
    else:
        form = SystemSettingForm(instance=settings_obj, request=request)

    return render(request, "web/admin/admin_settings.html", {"form": form})

@login_required
@csrf_protect
def invite_new(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != "teacher":
        raise PermissionDenied("الإذن غير متاح.")
    code = None
    if request.method == "POST":
        code = Invitation.generate_code()
        try:
            Invitation.objects.create(code=code, teacher=request.user)
        except (OperationalError, ProgrammingError):
            messages.error(request, "تعذّر إنشاء الدعوة. حاول مجدداً بعد تهيئة قاعدة البيانات.")
            code = None
        else:
            messages.success(request, f"تم إنشاء الدعوة: {code}")
    return render(request, "web/invite_new.html", {"code": code})

@login_required
@csrf_protect
def invite_accept(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != "student":
        raise PermissionDenied("الوصول غير مسموح.")
    if profile.is_verified_student:
        messages.info(request, "حسابك مفعل بالفعل.")
        return render(request, "web/invite_accept.html", {"already_verified": True, "form": None})

    form = InviteAcceptForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            code = form.cleaned_data["code"]
            try:
                Invitation.consume_code(code, request.user)
            except ValueError as exc:
                form.add_error("code", str(exc))
                messages.error(request, str(exc))
            except (OperationalError, ProgrammingError):
                error_msg = "تعذّر التحقق من الرمز قبل تهيئة قاعدة البيانات."
                form.add_error("code", error_msg)
                messages.error(request, error_msg)
            else:
                messages.success(request, "تم تفعيل حسابك كطالب. يمكنك الآن رفع التسليمات.")
                return redirect("web:profile")
        else:
            messages.error(request, "يرجى التأكد من إدخال رمز صالح.")
    return render(request, "web/invite_accept.html", {"already_verified": False, "form": form})


@login_required
@student_verified_required
def chat_list(request):
    try:
        qs = Conversation.objects.filter(
            Q(student=request.user) | Q(teacher=request.user)
        ).select_related("student", "teacher", "assignment")
        unread_map = {}
        try:
            role = getattr(
                getattr(request.user, "profile", None),
                "role",
                "student" if not request.user.is_staff else "teacher",
            )
            # unread_map اختياري؛ إن تعذّر نحطه فارغ
            for conversation in qs:
                msgs = conversation.messages.exclude(sender=request.user)
                if role == "student":
                    unread_map[conversation.id] = msgs.filter(is_read_by_student=False).count()
                else:
                    unread_map[conversation.id] = msgs.filter(is_read_by_teacher=False).count()
        except (OperationalError, ProgrammingError):
            unread_map = {}
        return render(
            request,
            "web/chat_list.html",
            {"conversations": qs, "unread_map": unread_map},
        )
    except (OperationalError, ProgrammingError):
        messages.info(
            request,
            "ميزة الدردشة ستكون متاحة بعد إتمام ترحيل الجداول.",
        )
        return render(
            request,
            "web/chat_list.html",
            {"conversations": [], "unread_map": {}},
        )

@login_required
@student_verified_required
def chat_start(request):
    profile = getattr(request.user, "profile", None)
    mode = "teacher" if profile and profile.role == "teacher" else "student"

    form = ConversationStartForm(request.POST or None, user=request.user)
    if request.method == "POST":
        if form.is_valid():
            assignment = form.cleaned_data.get("assignment")
            if mode == "teacher":
                student = form.cleaned_data["student"]
                teacher = request.user
            else:
                teacher = form.cleaned_data["teacher"]
                student = request.user
            if getattr(getattr(student, "profile", None), "role", None) != "student":
                messages.error(request, "المستخدم المحدد ليس طالباً.")
                return render(request, "web/chat_start.html", {"form": form})
            if getattr(getattr(teacher, "profile", None), "role", None) != "teacher":
                messages.error(request, "المستخدم المحدد ليس معلماً.")
                return render(request, "web/chat_start.html", {"form": form})
            try:
                conversation, _ = Conversation.objects.get_or_create(
                    student=student,
                    teacher=teacher,
                    assignment=assignment,
                )
            except (OperationalError, ProgrammingError):
                messages.error(request, "ميزة الدردشة ستعمل بعد إتمام ترحيل جداول المحادثات.")
                return redirect("web:chat_list")
            return redirect("web:chat_room", pk=conversation.pk)
        messages.error(request, "يرجى مراجعة الحقول لإتمام إنشاء المحادثة.")
    return render(request, "web/chat_start.html", {"form": form})


@login_required
@student_verified_required
def chat_room(request, pk):
    try:
        conv = get_object_or_404(Conversation, pk=pk)
    except (OperationalError, ProgrammingError):
        messages.info(request, "ميزة الدردشة ستعمل بعد إتمام ترحيل الجداول.")
        return redirect("web:chat_list")

    if not conv.is_participant(request.user):
        raise PermissionDenied("لا يمكنك الوصول لهذه المحادثة.")

    try:
        chat_messages = conv.messages.select_related("sender")
        for msg in chat_messages:
            if msg.sender_id != request.user.id:
                msg.mark_read_for(request.user)
    except (OperationalError, ProgrammingError):
        messages.info(request, "سيتم تحميل الرسائل بعد إتمام تهيئة قاعدة البيانات.")
        chat_messages = Message.objects.none()

    form = MessageForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        text_value = form.cleaned_data["text"].strip()
        if text_value:
            try:
                Message.objects.create(conversation=conv, sender=request.user, text=text_value)
            except (OperationalError, ProgrammingError):
                messages.error(request, "تعذّر إرسال الرسالة حالياً. جرّب مرة أخرى بعد تهيئة قاعدة البيانات.")
            else:
                return redirect("web:chat_room", pk=conv.pk)
        else:
            messages.error(request, "الرسالة فارغة.")

    last_id = chat_messages.order_by("-id").values_list("id", flat=True).first() or 0

    return render(
        request,
        "web/chat_room.html",
        {"conv": conv, "chat_messages": chat_messages, "form": form, "last_id": last_id},
    )


@login_required
@require_GET
def chat_unread_count(request):
    try:
        role = getattr(getattr(request.user, "profile", None), "role", "student" if not request.user.is_staff else "teacher")
        conv_ids = (
            Conversation.objects.filter(Q(student=request.user) | Q(teacher=request.user))
            .values_list("id", flat=True)
        )
        if role == "student":
            unread = (
                Message.objects.filter(conversation_id__in=conv_ids)
                .exclude(sender=request.user)
                .filter(is_read_by_student=False)
                .count()
            )
        else:
            unread = (
                Message.objects.filter(conversation_id__in=conv_ids)
                .exclude(sender=request.user)
                .filter(is_read_by_teacher=False)
                .count()
            )
        return JsonResponse({"unread": unread})
    except (OperationalError, ProgrammingError):
        return JsonResponse({"unread": 0})

@login_required
@require_GET
def chat_messages_poll(request, pk):
    try:
        conversation = get_object_or_404(Conversation, pk=pk)
    except (OperationalError, ProgrammingError):
        return JsonResponse({"messages": []})

    if not conversation.is_participant(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)

    after = request.GET.get("after")
    queryset = conversation.messages.select_related("sender")
    if after:
        try:
            queryset = queryset.filter(pk__gt=int(after))
        except ValueError:
            pass

    payload = []
    try:
        for message_obj in queryset:
            payload.append(
                {
                    "id": message_obj.id,
                    "text": message_obj.text,
                    "sender": message_obj.sender.username,
                    "mine": message_obj.sender_id == request.user.id,
                    "created": message_obj.created_at.strftime("%Y-%m-%d %H:%M"),
                }
            )
            if message_obj.sender_id != request.user.id:
                message_obj.mark_read_for(request.user)
    except (OperationalError, ProgrammingError):
        return JsonResponse({"messages": []})

    return JsonResponse({"messages": payload})

@login_required
@require_POST
@csrf_protect
def chat_mark_read(request, pk):
    try:
        conversation = get_object_or_404(Conversation, pk=pk)
    except (OperationalError, ProgrammingError):
        return JsonResponse({"ok": False})

    if not conversation.is_participant(request.user):
        return JsonResponse({"error": "forbidden"}, status=403)

    try:
        for message_obj in conversation.messages.exclude(sender=request.user):
            message_obj.mark_read_for(request.user)
    except (OperationalError, ProgrammingError):
        return JsonResponse({"ok": False})

    return JsonResponse({"ok": True})


def error_403(request, exception=None):
    response = render(request, "web/errors/403.html")
    response.status_code = 403
    return response


def error_404(request, exception=None):
    response = render(request, "web/errors/404.html")
    response.status_code = 404
    return response


def error_500(request):
    response = render(request, "web/errors/500.html")
    response.status_code = 500
    return response
