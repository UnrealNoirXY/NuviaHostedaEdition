from django.core.management.base import BaseCommand
from django.utils import timezone

from clients.models import Company, Structure, StructureRole
from menu_generator.models import Allergene, Ingrediente, Piatto, LayoutTemplate


class Command(BaseCommand):
    help = "Crea dati di esempio per il Menu Creation Studio"

    def add_arguments(self, parser):
        parser.add_argument('--company', type=int, help='ID della company su cui seminare i dati')

    def handle(self, *args, **options):
        company = Company.objects.first()
        if options.get('company'):
            company = Company.objects.filter(id=options['company']).first() or company
        if not company:
            self.stdout.write(self.style.ERROR('Nessuna Company trovata'))
            return

        structure, _ = Structure.objects.get_or_create(company=company, name='Ristorante Demo', defaults={'slug': 'demo-restaurant'})

        StructureRole.objects.get_or_create(
            company=company,
            name='Chef',
            defaults={
                'can_edit_menus': True,
                'can_edit_dishes': True,
                'can_manage_allergens': True,
            },
        )
        StructureRole.objects.get_or_create(
            company=company,
            name='Executive Chef',
            defaults={
                'can_edit_menus': True,
                'can_edit_dishes': True,
                'can_manage_allergens': True,
                'can_publish_menu': True,
                'can_approve_menu': True,
            },
        )
        StructureRole.objects.get_or_create(
            company=company,
            name='Chef Demo',
            defaults={
                'can_edit_menus': True,
                'can_edit_dishes': True,
                'can_publish_menu': True,
                'can_manage_templates': True,
                'can_manage_allergens': True,
                'can_edit_layouts': True,
            },
        )

        allergeni_data = [
            ('glutine', 'Glutine'),
            ('lattosio', 'Latte'),
            ('arachidi', 'Arachidi'),
            ('uova', 'Uova'),
            ('pesce', 'Pesce'),
            ('soia', 'Soia'),
        ]
        allergeni_lookup = {}
        for codice, nome in allergeni_data:
            allergene, _ = Allergene.objects.get_or_create(codice=codice, defaults={'nome': nome})
            allergeni_lookup[codice] = allergene

        ingredienti_data = [
            ('Pomodoro', 'estate', []),
            ('Mozzarella', 'annuale', ['lattosio']),
            ('Basilico', 'estate', []),
            ('Farina', 'annuale', ['glutine']),
            ('Uovo', 'annuale', ['uova']),
            ('Salmone', 'inverno', ['pesce']),
        ]
        ingredienti_lookup = {}
        for nome, stagionalita, allergeni_codes in ingredienti_data:
            ingrediente, _ = Ingrediente.objects.get_or_create(
                company=company,
                nome=nome,
                defaults={'stagionalita': stagionalita},
            )
            if allergeni_codes:
                ingrediente.allergeni.set([allergeni_lookup[codice] for codice in allergeni_codes])
            ingredienti_lookup[nome] = ingrediente

        piatti_data = [
            {
                'nome': 'Pizza Margherita',
                'categoria': 'primo',
                'stagionalita': 'estate',
                'ingredienti': ['Pomodoro', 'Mozzarella', 'Basilico', 'Farina'],
                'allergeni': ['glutine', 'lattosio'],
            },
            {
                'nome': 'Lasagna Classica',
                'categoria': 'primo',
                'stagionalita': 'annuale',
                'ingredienti': ['Farina', 'Uovo', 'Mozzarella'],
                'allergeni': ['glutine', 'uova', 'lattosio'],
            },
            {
                'nome': 'Salmone al Forno',
                'categoria': 'secondo',
                'stagionalita': 'inverno',
                'ingredienti': ['Salmone', 'Pomodoro'],
                'allergeni': ['pesce'],
            },
            {
                'nome': 'Insalata Caprese',
                'categoria': 'antipasto',
                'stagionalita': 'estate',
                'ingredienti': ['Pomodoro', 'Mozzarella', 'Basilico'],
                'allergeni': ['lattosio'],
            },
        ]
        from menu_generator.models import PiattoIngrediente
        for piatto_data in piatti_data:
            piatto, created = Piatto.objects.get_or_create(
                company=company,
                nome=piatto_data['nome'],
                categoria=piatto_data['categoria'],
                defaults={'porzioni': 1, 'stagionalita': piatto_data['stagionalita'], 'prezzo': 15.00},
            )
            if created:
                for nome in piatto_data['ingredienti']:
                    PiattoIngrediente.objects.create(
                        piatto=piatto,
                        ingrediente=ingredienti_lookup[nome],
                        quantita=150,
                        unita_misura='g'
                    )
            piatto.allergeni.set([allergeni_lookup[codice] for codice in piatto_data['allergeni']])

        LayoutTemplate.objects.get_or_create(
            company=company,
            nome='Layout Vetrina',
            defaults={
                'struttura': structure,
                'struttura_blocchi': {'colonne': 2, 'accento': '#7c4dff'},
            },
        )
        LayoutTemplate.objects.get_or_create(
            company=company,
            nome='Layout Classico',
            defaults={
                'struttura': structure,
                'struttura_blocchi': {'colonne': 1, 'accento': '#2f3b52'},
            },
        )

        self.stdout.write(self.style.SUCCESS(f'Dati seed creati per {company.name} su {timezone.now().date()}'))
