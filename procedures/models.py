from django.db import models
from django.conf import settings
from clients.models import Company

class Sector(models.Model):
    """Represents a sector, corresponding to a user role."""
    name = models.CharField(max_length=100, unique=True, help_text="The display name of the sector, e.g., 'Manutenzione'.")
    role_key = models.CharField(max_length=30, unique=True, help_text="The internal key for the role, e.g., 'maintainer'.")

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Procedure(models.Model):
    """Represents a procedure document."""
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='procedures', verbose_name="Azienda")
    title = models.CharField(max_length=255, verbose_name="Titolo")
    file = models.FileField(upload_to='procedures/', verbose_name="File PDF")
    sectors = models.ManyToManyField(
        Sector,
        related_name='procedures',
        verbose_name="Settori di pertinenza"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_procedures',
        verbose_name="Caricato da"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data di Creazione")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Data Ultimo Aggiornamento")
    version = models.PositiveIntegerField(default=1, verbose_name="Versione")

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-updated_at']
        verbose_name = "Procedura"
        verbose_name_plural = "Procedure"
