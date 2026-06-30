from rest_framework import serializers
from .models import VerifiedDocument

class VerifiedDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = VerifiedDocument
        fields = [
            'id', 'status', 'document_number', 'first_name', 'last_name',
            'birth_date', 'expiry_date', 'issuer_country', 'review_notes',
            'confidence_scores', 'created_at'
        ]
        read_only_fields = fields # Rendiamo tutti i campi read-only per l'output
