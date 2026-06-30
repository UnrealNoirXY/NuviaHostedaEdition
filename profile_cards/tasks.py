from celery import shared_task
from django.conf import settings
from .models import ProfileCard, ProfileCardDelivery
from .emailing import send_profile_card_email
from .tokens import issue_public_token
from django.urls import reverse

@shared_task
def send_profile_card_email_batch_task(card_ids, recipient_emails, created_by_id=None):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    created_by = User.objects.filter(pk=created_by_id).first() if created_by_id else None

    cards = ProfileCard.objects.filter(pk__in=card_ids)
    sent_count = 0
    for card in cards:
        token = issue_public_token(card)
        public_url = f"{settings.BASE_URL.rstrip('/')}" + reverse("profile_cards:public_profile", kwargs={"token": token.token})
        for recipient_email in recipient_emails:
            delivery = send_profile_card_email(
                card=card,
                public_url=public_url,
                recipient_email=recipient_email,
                created_by=created_by,
            )
            if delivery.status == ProfileCardDelivery.STATUS_SENT:
                sent_count += 1
    return sent_count
