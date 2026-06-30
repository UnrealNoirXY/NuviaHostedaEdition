import random
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker
from accounts.models import User
from clients.models import Company
from resort.models import Resort, Room
from tickets.models import Ticket
from reviews.models import Review, ReviewSource

class Command(BaseCommand):
    help = 'Seeds the database with demo data for the landing page previews.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Deleting old demo data...")
        # Be careful with this in production!
        Company.objects.filter(name__startswith='Demo').delete()
        User.objects.filter(username__startswith='demo_').delete()

        self.stdout.write("Seeding new demo data...")
        fake = Faker('it_IT')

        # Create Company and Resort
        company = Company.objects.create(name="Demo Resort Group")
        resort = Resort.objects.create(name="Paradiso Resort & Spa (Demo)", company=company, location=fake.city())

        # Create Rooms
        rooms = []
        for i in range(10):
            room = Room.objects.create(resort=resort, name=f"Stanza {101 + i}", description=f"Camera {('Matrimoniale', 'Doppia', 'Singola')[i % 3]}")
            rooms.append(room)

        # Create Users
        demo_superadmin = User.objects.create_superuser('demo_superadmin', 'demo@example.com', 'password')
        demo_director = User.objects.create_user('demo_director', 'director@example.com', 'password', role=User.DIRECTOR, company=company, resort=resort)
        demo_receptionist = User.objects.create_user('demo_receptionist', 'recep@example.com', 'password', role=User.RECEPTIONIST, company=company, resort=resort)

        maintainers = []
        for i in range(3):
            maintainer = User.objects.create_user(f'demo_maintainer_{i}', f'maintainer{i}@example.com', 'password', role=User.MAINTAINER, company=company, resort=resort)
            maintainers.append(maintainer)

        # Create Tickets
        ticket_titles = [
            "La TV in camera 203 non funziona",
            "Aria condizionata rotta nella suite 101",
            "Perdita dal lavandino del bagno in camera 305",
            "Lampadina fulminata nel corridoio del secondo piano",
            "Wi-Fi non disponibile nell'area piscina",
        ]
        statuses = ['open', 'in_progress', 'resolved']
        for title in ticket_titles:
            Ticket.objects.create(
                title=title,
                description=fake.paragraph(nb_sentences=3),
                resort=resort,
                room=random.choice(rooms),
                created_by=demo_receptionist,
                status=random.choice(statuses),
                assigned_to=random.choice(maintainers) if random.random() > 0.3 else None,
                priority=random.choice([1,2,3])
            )

        # Create Reviews
        booking, _ = ReviewSource.objects.get_or_create(name='Booking.com')
        tripadvisor, _ = ReviewSource.objects.get_or_create(name='TripAdvisor')
        google, _ = ReviewSource.objects.get_or_create(name='Google')
        sources = [booking, tripadvisor, google]

        review_texts = [
            ("Soggiorno fantastico!", "Tutto perfetto, dalla pulizia della camera alla cortesia dello staff. La piscina è magnifica. Torneremo sicuramente!"),
            ("Potrebbe migliorare", "La posizione è ottima, ma la camera era un po' datata. Il personale della reception è stato molto gentile e disponibile."),
            ("Delusione totale", "Aria condizionata non funzionante per due giorni. Servizio lento e poco attento. Non vale assolutamente il prezzo pagato."),
            ("Oasi di pace", "Un resort meraviglioso, immerso nel verde. Ideale per rilassarsi. Il ristorante offre piatti deliziosi e il servizio è impeccabile."),
            ("Buono, ma non eccezionale", "Hotel pulito e in una buona posizione. La colazione era un po' scarsa per un 4 stelle. Nel complesso un buon soggiorno."),
        ]

        for i, (title, text) in enumerate(review_texts):
            Review.objects.create(
                resort=resort,
                source=random.choice(sources),
                review_id=f"DEMO-{i}",
                title=title,
                text=text,
                rating=random.choice([1,2,3,4,5]),
                review_date=fake.date_this_year()
            )

        self.stdout.write(self.style.SUCCESS('Successfully seeded the database with demo data.'))
