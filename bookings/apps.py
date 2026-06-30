from django.apps import AppConfig


class BookingsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bookings'
    verbose_name = 'Prenotazioni e Check-in'

    def ready(self):
        # Importa i segnali per registrarli correttamente all'avvio dell'app
        import bookings.signals