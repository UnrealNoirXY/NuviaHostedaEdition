from django.db import models

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Nome della competenza (es. Elettricista, Idraulico)")

    class Meta:
        ordering = ['name']
        verbose_name = "Competenza"
        verbose_name_plural = "Competenze"

    def __str__(self):
        return self.name
