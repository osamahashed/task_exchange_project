from django.apps import apps as django_apps
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver
from django.db.utils import OperationalError, ProgrammingError

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        Profile = django_apps.get_model("accounts", "Profile")
        if Profile is None:
            return
        Profile.objects.get_or_create(user=instance)
    except (OperationalError, ProgrammingError, LookupError):
        pass


@receiver(post_migrate)
def ensure_site_settings(sender, **kwargs):
    try:
        SiteSetting = django_apps.get_model("accounts", "SiteSetting")
        if SiteSetting is None:
            return
        SiteSetting.objects.get_or_create(pk=1)
    except (OperationalError, ProgrammingError, LookupError):
        pass
