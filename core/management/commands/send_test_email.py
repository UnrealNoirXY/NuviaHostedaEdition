import os
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Sends a test email to check if the SMTP configuration is working.'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient_email',
            type=str,
            help='The email address to send the test email to.'
        )

    def handle(self, *args, **options):
        recipient_email = options['recipient_email']
        self.stdout.write("Attempting to send a test email...")
        self.stdout.write(f"Recipient: {recipient_email}")
        self.stdout.write(f"Email Backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"Email Host: {settings.EMAIL_HOST}")
        self.stdout.write(f"Email Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"Email Use TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"Email Use SSL: {settings.EMAIL_USE_SSL}")
        self.stdout.write(f"Email Host User: {settings.EMAIL_HOST_USER}")
        # Do not print the password for security reasons

        try:
            send_mail(
                subject='Test Email from Django Application',
                message='This is a test email to confirm that your SMTP settings are configured correctly.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS('Successfully sent the test email!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR('An error occurred while trying to send the email.'))
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
            self.stdout.write(self.style.WARNING('Please check your .env file and your SMTP provider settings.'))
            self.stdout.write(self.style.WARNING('Common issues include: incorrect password (some providers require app-specific passwords), firewall blocking the port, or incorrect TLS/SSL settings.'))
