from rest_framework import serializers
from .models import Booking, GuestDocument
from resort.models import Resort
from clients.models import Company

class CompanySerializer(serializers.ModelSerializer):
    """Serializer per il modello Company."""
    class Meta:
        model = Company
        fields = ['id', 'name']

class ResortSerializer(serializers.ModelSerializer):
    """Serializer per il modello Resort, ora include ID e società."""
    class Meta:
        model = Resort
        fields = ['id', 'name', 'company'] # L'ID della società collegata

class BookingSerializer(serializers.ModelSerializer):
    """Serializer per visualizzare i dettagli di una prenotazione."""
    resort = ResortSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id',
            'guest_name',
            'guest_email',
            'check_in_date',
            'check_out_date',
            'resort',
            'status',
            'status_display',
            'booking_engine_id'
        ]

class BookingCreateSerializer(serializers.ModelSerializer):
    """Serializer specifico per la creazione di una nuova prenotazione."""
    class Meta:
        model = Booking
        fields = [
            'guest_name',
            'guest_email',
            'check_in_date',
            'check_out_date',
            'resort',
            'room_details',
            'booking_engine_id'
        ]

    def create(self, validated_data):
        """
        Alla creazione, genera anche il token di accesso per il check-in.
        """
        booking = Booking.objects.create(**validated_data)
        booking.issue_access_token()
        return booking


class GuestDocumentStatusSerializer(serializers.ModelSerializer):
    """
    Serializer per esporre lo stato di un GuestDocument, usato per il polling
    dal frontend durante la scansione OCR.
    """
    class Meta:
        model = GuestDocument
        fields = ['id', 'scan_result', 'ocr_confidence', 'scanned_at']