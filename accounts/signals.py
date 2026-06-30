from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
from .models import User
from .emails import send_privacy_confirmation_email

@receiver(pre_save, sender=User)
def set_password_last_changed(sender, instance, **kwargs):
    """
    Automatically update the password_last_changed field whenever the
    password is modified.
    """
    if instance.pk:  # Check if this is an existing user
        try:
            old_instance = User.objects.get(pk=instance.pk)
            # Check if the password has been changed
            if instance.password != old_instance.password:
                instance.password_last_changed = timezone.now()
        except User.DoesNotExist:
            # This can happen if the user is being created, which is fine.
            # The password_last_changed will be null initially.
            pass
    elif not instance.pk and instance.password:
        # This handles the case of user creation where a password is set
        instance.password_last_changed = timezone.now()

@receiver(post_save, sender=User)
def send_password_change_notification(sender, instance, created, **kwargs):
    """
    Send a notification email to the user after their password has been changed.
    We check if the password_last_changed field is very recent.
    """
    if not created and instance.password_last_changed:
        # Check if the password was changed in the last few seconds.
        # This is a heuristic to avoid sending emails on every user save.
        time_since_change = timezone.now() - instance.password_last_changed
        if time_since_change.total_seconds() < 10:  # 10-second window
            try:
                context = {
                    'user': instance,
                    'site_name': getattr(
                        settings,
                        "SITE_NAME",
                        settings.JAZZMIN_SETTINGS.get("site_brand", ""),
                    ),
                }
                email_html_body = render_to_string('core/password_change_notification_email.html', context)
                email_plain_body = strip_tags(email_html_body)
                send_mail(
                    subject=(
                        "Avviso di Sicurezza: La tua password per "
                        f"{getattr(settings, 'SITE_NAME', settings.JAZZMIN_SETTINGS.get('site_brand', ''))}"
                        " è stata cambiata"
                    ),
                    html_message=email_html_body,
                    message=email_plain_body,
                    from_email=None,
                    recipient_list=[instance.email],
                    fail_silently=False
                )
            except Exception as e:
                # Log the error, but don't crash the save operation
                print(f"Error sending password change notification to {instance.email}: {e}")


@receiver(post_save, sender=User)
def send_privacy_confirmation_on_create(sender, instance, created, **kwargs):
    if not created:
        return
    if not instance.must_change_password:
        instance.must_change_password = True
        instance.save(update_fields=["must_change_password"])
    try:
        send_privacy_confirmation_email(instance)
    except Exception as e:
        print(f"Error sending privacy confirmation to {instance.email}: {e}")
