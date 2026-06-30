from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from .services import get_ocr_service, DocumentVerificationService
from .serializers import VerifiedDocumentSerializer

class DocumentVerificationView(APIView):
    """
    Endpoint API per avviare il processo di verifica di un documento.
    """
    permission_classes = [AllowAny] # Rende l'endpoint pubblico
    def post(self, request, *args, **kwargs):
        image_id = request.data.get('image_id')
        ocr_provider = request.data.get('ocr_provider', 'mock')
        issuer_country = request.data.get('issuer_country')
        document_type = request.data.get('document_type')

        if not image_id:
            return Response(
                {"error": "image_id è obbligatorio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Inizializza i servizi tramite la factory
            ocr_service = get_ocr_service(ocr_provider)
            verification_service = DocumentVerificationService(ocr_service=ocr_service)

            # Esegui il processo di verifica
            verified_document = verification_service.verify_document(
                image_id=image_id,
                issuer_country=issuer_country,
                document_type=document_type,
            )

            # Serializza e restituisci la risposta
            serializer = VerifiedDocumentSerializer(verified_document)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            # Log dell'errore in un sistema di produzione
            return Response(
                {"error": "Si è verificato un errore interno durante la verifica."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
