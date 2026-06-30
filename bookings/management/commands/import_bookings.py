import json
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date
from django.contrib.sites.models import Site
from bookings.models import Booking
from resort.models import Resort
from bookings.tasks import send_invitation_email_task
from communications.email_gateway import dispatch_email_task

class Command(BaseCommand):
    help = 'Importa prenotazioni da un file JSON o da un API endpoint (simulato).'

    def add_arguments(self, parser):
        parser.add_argument('source_file', type=str, help='Il percorso del file JSON contenente le prenotazioni.')

    def handle(self, *args, **options):
        source_file = options['source_file']

        try:
            with open(source_file, 'r') as f:
                bookings_data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File non trovato a: {source_file}")
        except json.JSONDecodeError:
            raise CommandError("Errore nel decodificare il file JSON. Assicurati che sia formattato correttamente.")

        created_count = 0
        updated_count = 0

        # Prepara i dati del sito per l'invio delle email
        current_site = Site.objects.get_current()
        scheme = 'https'  # Assumiamo https per i link di produzione
        host = current_site.domain

        for item in bookings_data:
            try:
                # Cerca il resort per nome. In un'app reale, si userebbe un ID.
                resort = Resort.objects.get(name__iexact=item['resort_name'])

                # Converte le date da stringa a oggetto Date
                check_in_date = parse_date(item['check_in_date'])
                check_out_date = parse_date(item['check_out_date'])

                # Usa update_or_create per l'idempotenza
                booking, created = Booking.objects.update_or_create(
                    booking_engine_id=item['booking_engine_id'],
                    defaults={
                        'guest_name': item['guest_name'],
                        'guest_email': item['guest_email'],
                        'check_in_date': check_in_date,
                        'check_out_date': check_out_date,
                        'resort': resort,
                        'room_details': item.get('room_details', ''),
                        'pms_payload_snapshot': item, # Salva lo snapshot dei dati originali
                    }
                )

                if created:
                    created_count += 1
                    # Invia l'email di invito usando il task asincrono
                    try:
                        dispatch_email_task(send_invitation_email_task, booking.id, scheme, host)
                        self.stdout.write(self.style.SUCCESS(f"Creata nuova prenotazione {booking.id}. Invio email programmato."))
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f"Creata prenotazione {booking.id}, ma fallita la programmazione dell'email: {e}"))
                else:
                    updated_count += 1
                    self.stdout.write(f"Aggiornata prenotazione esistente {booking.id}.")

            except Resort.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Resort '{item['resort_name']}' non trovato. Salto prenotazione {item['booking_engine_id']}."))
                continue
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Errore nell'importare la prenotazione {item.get('booking_engine_id', 'N/A')}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"Importazione completata. Create: {created_count}, Aggiornate: {updated_count}."
        ))