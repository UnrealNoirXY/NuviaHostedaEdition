import hashlib
import hashlib

from django.template.loader import render_to_string
from weasyprint import HTML
from django.utils import timezone
from .models import Booking, Guest
from django.conf import settings
from django.urls import reverse
from communications.email_gateway import EmailGateway


email_gateway = EmailGateway()


def get_booking_details_for_email(booking, request):
    """
    Estrae un dizionario di dettagli serializzabili da un oggetto Booking,
    usando il request object per costruire URL assoluti.
    """
    company_logo_url = None
    if booking.resort.company and booking.resort.company.logo:
        company_logo_url = request.build_absolute_uri(booking.resort.company.logo.url)

    return {
        'guest_name': booking.guest_name,
        'guest_email': booking.guest_email,
        'resort_name': booking.resort.name,
        'check_in_date': booking.check_in_date.strftime('%d/%m/%Y'),
        'check_out_date': booking.check_out_date.strftime('%d/%m/%Y'),
        'company_logo_url': company_logo_url,
    }


def generate_checkin_pdf(booking, signature_meta):
    """
    Genera un PDF di riepilogo del check-in da un template HTML.
    Questa versione semplificata calcola l'hash sul contenuto finale del PDF
    senza tentare di inserire l'hash nel documento stesso, il che è un paradosso.
    """
    guests = Guest.objects.filter(booking=booking)
    generation_time = signature_meta.get('ts', timezone.now())

    context = {
        'booking': booking,
        'guests': guests,
        'generation_date': generation_time,
        'signature_meta': signature_meta,
    }
    html_string = render_to_string('bookings/emails/checkin_summary_pdf.html', context)
    pdf_bytes = HTML(string=html_string).write_pdf()
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

    return pdf_bytes, pdf_hash


def _send_booking_email(booking, scheme, host, template_name, subject_prefix):
    """Helper generico per inviare email di prenotazione con link di check-in."""
    raw_token = booking.ensure_access_token()
    checkin_path = reverse('bookings:checkin_wizard', kwargs={'token': raw_token})
    checkin_link = f"{scheme}://{host}{checkin_path}"

    company_logo_url = None
    if booking.resort.company and booking.resort.company.logo:
        logo_path = booking.resort.company.logo.url
        company_logo_url = f"{scheme}://{host}{logo_path}"

    context = {
        'guest_name': booking.guest_name,
        'resort_name': booking.resort.name,
        'check_in_date': booking.check_in_date.strftime('%d/%m/%Y'),
        'check_out_date': booking.check_out_date.strftime('%d/%m/%Y'),
        'checkin_link': checkin_link,
        'company_logo_url': company_logo_url,
        'year': timezone.now().year,
    }

    html_body = render_to_string(template_name, context)
    text_body = f"La tua prenotazione presso {booking.resort.name} è stata gestita. Puoi accedere al tuo check-in qui: {checkin_link}"
    subject = f"{subject_prefix} per il tuo soggiorno presso {booking.resort.name}"

    email_gateway.send_email(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        recipients=[booking.guest_email],
    )


def send_final_confirmation_email(booking, scheme, host):
    """
    Invia l'email di conferma finale con il PDF e l'evento di calendario in allegato.
    """
    # 1. Genera il PDF
    signature_meta = booking.checkin_process.signature_meta or {}
    pdf_content, _ = generate_checkin_pdf(booking, signature_meta)

    # 2. Crea l'evento iCalendar
    from icalendar import Calendar, Event
    cal = Calendar()
    cal.add('prodid', '-//NoirTech//Booking Calendar//EN')
    cal.add('version', '2.0')
    event = Event()
    event.add('summary', f'Prenotazione: {booking.resort.name} - {booking.guest_name}')
    event.add('dtstart', booking.check_in_date)
    event.add('dtend', booking.check_out_date)
    event.add('dtstamp', timezone.now())
    event.add('uid', f'booking-{booking.id}@noirtech.online')
    event.add('location', booking.resort.address or booking.resort.name)
    cal.add_component(event)
    ics_content = cal.to_ical()

    # 3. Prepara il contesto per l'email
    context = {
        'guest_name': booking.guest_name,
        'resort_name': booking.resort.name,
        'year': timezone.now().year,
        'calendar_link': '#'
    }

    html_body = render_to_string('bookings/emails/final_confirmation_email.html', context)
    text_body = f"Grazie per aver completato il tuo check-in per il soggiorno presso {booking.resort.name}. Trovi il riepilogo in PDF e l'evento di calendario in allegato."
    subject = f"Conferma Finale del tuo Check-in presso {booking.resort.name}"

    # 4. Crea e invia l'email con allegati
    email_gateway.send_email(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        recipients=[booking.guest_email],
        attachments=[
            ('checkin_summary.pdf', pdf_content, 'application/pdf'),
            ('booking.ics', ics_content, 'text/calendar'),
        ],
    )


def send_newsletter_confirmation_email(booking, scheme, host):
    """Invia l'email di conferma per l'iscrizione alla newsletter."""
    company_logo_url = None
    if booking.resort.company and booking.resort.company.logo:
        logo_path = booking.resort.company.logo.url
        company_logo_url = f"{scheme}://{host}{logo_path}"

    context = {
        'guest_name': booking.guest_name,
        'company_logo_url': company_logo_url,
        'year': timezone.now().year,
    }

    html_body = render_to_string('bookings/emails/newsletter_confirmation.html', context)
    text_body = "Grazie per esserti iscritto alla nostra newsletter!"
    subject = "Conferma Iscrizione Newsletter"

    email_gateway.send_email(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        recipients=[booking.guest_email],
    )


def send_checkin_invitation_email(booking, scheme, host):
    """Invia un'email di invito al check-in."""
    return _send_booking_email(
        booking, scheme, host,
        'bookings/emails/checkin_invitation.html',
        "Invito al Check-in Online"
    )


def send_booking_creation_email(booking, scheme, host):
    """Invia un'email di notifica per una nuova prenotazione."""
    return _send_booking_email(
        booking, scheme, host,
        'bookings/emails/booking_created.html',
        "Conferma Prenotazione e Invito al Check-in"
    )


def send_booking_update_email(booking, scheme, host):
    """Invia un'email di notifica per la modifica di una prenotazione."""
    return _send_booking_email(
        booking, scheme, host,
        'bookings/emails/booking_updated.html',
        "Aggiornamento Prenotazione e Link al Check-in"
    )


def send_booking_deletion_email(booking_details):
    """Invia un'email di notifica per la cancellazione di una prenotazione."""
    context = {
        'guest_name': booking_details['guest_name'],
        'resort_name': booking_details['resort_name'],
        'check_in_date': booking_details['check_in_date'],
        'check_out_date': booking_details['check_out_date'],
        'company_logo_url': booking_details.get('company_logo_url'),
        'year': timezone.now().year,
    }

    html_body = render_to_string('bookings/emails/booking_deleted.html', context)
    text_body = f"La tua prenotazione presso {booking_details['resort_name']} è stata cancellata."
    subject = f"Cancellazione Prenotazione presso {booking_details['resort_name']}"

    email_gateway.send_email(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        recipients=[booking_details['guest_email']],
    )


def send_otp_email(booking, otp_code, scheme, host):
    """Invia l'email con il codice OTP per la verifica del check-in."""
    company_logo_url = None
    if booking.resort.company and booking.resort.company.logo:
        logo_path = booking.resort.company.logo.url
        company_logo_url = f"{scheme}://{host}{logo_path}"

    context = {
        'guest_name': booking.guest_name,
        'otp_code': otp_code,
        'company_logo_url': company_logo_url,
        'year': timezone.now().year,
    }

    html_body = render_to_string('bookings/emails/otp_notification.html', context)
    text_body = f"Il tuo codice di verifica per il check-in è: {otp_code}"
    subject = "Il Tuo Codice di Verifica per il Check-in"

    email_gateway.send_email(
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        recipients=[booking.guest_email],
    )