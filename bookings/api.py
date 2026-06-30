from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import AnonRateThrottle
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Count
import datetime

from .models import Booking, CheckInProcess, GuestDocument
from .token_validation import get_token_error_message, log_failed_token, validate_booking_token
from .serializers import (
    BookingSerializer,
    BookingCreateSerializer,
    CompanySerializer,
    ResortSerializer,
    GuestDocumentStatusSerializer
)
from .tasks import (
    send_booking_creation_email_task,
    send_booking_update_email_task,
    send_booking_deletion_email_task,
    send_otp_email_task
)
from .utils import get_booking_details_for_email
from clients.models import Company
from resort.models import Resort
from communications.email_gateway import dispatch_email_task


class BookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet per le operazioni CRUD sulle prenotazioni.
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filtra le prenotazioni in base ai permessi dell'utente.
        """
        user = self.request.user
        if user.is_superuser:
            return Booking.objects.all().select_related('resort').order_by('-check_in_date')

        # Filtra per i resort a cui l'utente ha accesso (da implementare)
        # Esempio: return Booking.objects.filter(resort__in=user.resorts.all())
        return Booking.objects.all().select_related('resort').order_by('-check_in_date')


    def get_serializer_class(self):
        if self.action == 'create':
            return BookingCreateSerializer
        return BookingSerializer

    def perform_create(self, serializer):
        """Salva una nuova prenotazione e invia l'email di notifica."""
        booking = serializer.save()
        request = self.request
        dispatch_email_task(send_booking_creation_email_task, booking.id, request.scheme, request.get_host())

    def perform_update(self, serializer):
        """Aggiorna una prenotazione e invia l'email di notifica."""
        booking = serializer.save()
        request = self.request
        dispatch_email_task(send_booking_update_email_task, booking.id, request.scheme, request.get_host())

    def perform_destroy(self, instance):
        """
        Invia l'email di notifica e cancella la prenotazione.
        """
        booking_details = get_booking_details_for_email(instance, self.request)
        dispatch_email_task(send_booking_deletion_email_task, booking_details)
        instance.delete()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_api_view(request):
    """
    Fornisce i dati aggregati per il cruscotto grafico in React.
    """
    today = timezone.now().date()
    next_7_days = today + datetime.timedelta(days=7)

    arrivals_today = Booking.objects.filter(check_in_date=today).count()
    completed_checkins_today = CheckInProcess.objects.filter(
        state=CheckInProcess.State.COMPLETED,
        completed_at__date=today
    ).count()
    pending_checkins_today = Booking.objects.filter(
        check_in_date=today,
        status=Booking.Status.PENDING
    ).count()

    arrivals_per_day = (
        Booking.objects
        .filter(check_in_date__range=[today, next_7_days])
        .values('check_in_date')
        .annotate(count=Count('id'))
        .order_by('check_in_date')
    )
    chart_labels = [(today + datetime.timedelta(days=i)).strftime("%d/%m") for i in range(7)]
    chart_data = [0] * 7
    for arrival in arrivals_per_day:
        day_index = (arrival['check_in_date'] - today).days
        if 0 <= day_index < 7:
            chart_data[day_index] = arrival['count']

    recent_completed_bookings = Booking.objects.filter(
        status=Booking.Status.COMPLETED
    ).order_by('-checkin_process__completed_at')[:5]
    recent_bookings_serializer = BookingSerializer(recent_completed_bookings, many=True)

    data = {
        'kpis': {
            'arrivals_today': arrivals_today,
            'completed_checkins_today': completed_checkins_today,
            'pending_checkins_today': pending_checkins_today,
        },
        'arrivals_chart': {
            'labels': chart_labels,
            'data': chart_data,
        },
        'recent_activity': recent_bookings_serializer.data,
    }

    return Response(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def form_options_api_view(request):
    """
    Fornisce le opzioni per i form, filtrando in base al ruolo dell'utente.
    """
    user = request.user

    if user.is_superuser:
        companies = Company.objects.all().order_by('name')
        resorts = Resort.objects.all().order_by('name')
    else:
        # Logica per altri ruoli (es. Proprietario, Direzione)
        # Qui si dovrebbe filtrare in base ai resort associati all'utente.
        # Esempio: companies = Company.objects.filter(resorts__in=user.resorts.all()).distinct()
        # Per ora, per semplicità, mostriamo tutto.
        companies = Company.objects.all().order_by('name')
        resorts = Resort.objects.all().order_by('name')

    company_serializer = CompanySerializer(companies, many=True)
    resort_serializer = ResortSerializer(resorts, many=True)

    data = {
        'companies': company_serializer.data,
        'resorts': resort_serializer.data,
    }
    return Response(data)


class DocumentStatusThrottle(AnonRateThrottle):
    rate = '30/min'

@api_view(['GET'])
@throttle_classes([DocumentStatusThrottle])
def document_status_api_view(request, doc_id, token):
    """
    API view per il polling dello stato di un documento.
    L'accesso è validato tramite il token della prenotazione e limitato nel tempo.
    """
    booking, reason, token_hash = validate_booking_token(token, status=Booking.Status.PENDING)
    if not booking:
        log_failed_token(reason, token_hash, request)
        return Response({'error': get_token_error_message(reason)}, status=404)

    # Trova il documento e verifica che appartenga alla prenotazione
    document = get_object_or_404(GuestDocument, id=doc_id, guest__booking=booking)

    # Serializza e ritorna i dati
    serializer = GuestDocumentStatusSerializer(document)
    return Response(serializer.data)


class OTPResendThrottle(AnonRateThrottle):
    rate = '1/min'

@api_view(['POST'])
@throttle_classes([OTPResendThrottle])
def resend_otp_api_view(request, token):
    """
    Gestisce la richiesta di reinvio di un codice OTP.
    L'accesso è validato tramite il token e limitato nel tempo.
    """
    booking, reason, token_hash = validate_booking_token(token, status=Booking.Status.PENDING)
    if not booking:
        log_failed_token(reason, token_hash, request)
        return Response({'error': get_token_error_message(reason)}, status=404)

    checkin_process = get_object_or_404(CheckInProcess, booking=booking)

    if checkin_process.state != CheckInProcess.State.AWAITING_OTP:
        return Response({'error': 'Non è possibile inviare un OTP in questo stato.'}, status=400)

    if checkin_process.otp_is_locked:
        return Response({'error': 'Accesso temporaneamente bloccato. Riprova più tardi.'}, status=429)

    now = timezone.now()
    cooldown_seconds = CheckInProcess.OTP_RESEND_COOLDOWN_SECONDS
    if checkin_process.otp_last_sent_at:
        elapsed = (now - checkin_process.otp_last_sent_at).total_seconds()
        if elapsed < cooldown_seconds:
            remaining = int(cooldown_seconds - elapsed)
            return Response({'error': f'Attendi {remaining}s prima di richiedere un nuovo codice.'}, status=429)

    # Genera e invia un nuovo OTP
    new_otp = checkin_process.issue_otp()
    dispatch_email_task(send_otp_email_task, booking.id, new_otp, request.scheme, request.get_host())

    return Response(
        {
            'message': 'Un nuovo codice OTP è stato inviato.',
            'expires_at': checkin_process.otp_expires_at,
            'cooldown_seconds': cooldown_seconds,
        },
        status=200,
    )