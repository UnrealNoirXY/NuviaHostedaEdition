from django.db import models
from django.conf import settings
from accounts.models import User

class Document(models.Model):
    DOCUMENT_TYPE_CHOICES = [
        ('payslip', 'Busta Paga'),
        ('contract', 'Contratto'),
        ('certificate', 'Certificazione'),
        ('other', 'Altro'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='user_documents/')
    document_type = models.CharField(max_length=20, choices=DOCUMENT_TYPE_CHOICES, default='other')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='read_documents',
        blank=True
    )

    def __str__(self):
        return f"{self.title} for {self.user.username}"

    class Meta:
        ordering = ['-uploaded_at']
