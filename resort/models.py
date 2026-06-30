from django.db import models
from clients.models import Company

class Resort(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='resorts', null=True, blank=True)
    name = models.CharField(max_length=255, unique=True)
    location = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

class Room(models.Model):
    resort = models.ForeignKey(Resort, on_delete=models.CASCADE, related_name='rooms')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('resort', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.resort.name})"
