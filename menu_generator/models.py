"""Modelli principali per il Menu Creation Studio."""

import uuid
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from clients.models import Structure


class Allergene(models.Model):
    """Catalogo di allergeni gestiti dalla piattaforma o dalla singola azienda."""

    codice = models.SlugField(max_length=50, unique=True, help_text="Codice univoco (es. glutine, latte).")
    nome = models.CharField(max_length=150, help_text="Nome visualizzato dell'allergene.")
    descrizione = models.TextField(blank=True)
    icona_svg = models.TextField(blank=True, help_text="Markup SVG opzionale da mostrare sui documenti.")
    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='allergeni_personalizzati',
        help_text="Società proprietaria (lasciare vuoto per allergeni globali).",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Allergene"
        verbose_name_plural = "Allergeni"
        ordering = ["codice"]

    def __str__(self):
        return self.nome


class Ingrediente(models.Model):
    """Ingrediente singolo, collegato agli allergeni e riutilizzabile."""

    STAGIONALITA_CHOICES = [
        ("annuale", "Tutto l'anno"),
        ("primavera", "Primavera"),
        ("estate", "Estate"),
        ("autunno", "Autunno"),
        ("inverno", "Inverno"),
    ]

    nome = models.CharField(max_length=200, help_text="Nome dell'ingrediente.")
    descrizione = models.TextField(blank=True)
    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        related_name='ingredienti',
    )
    economato_item = models.ForeignKey(
        'economato.EconomatoItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_ingredients',
        help_text="Collegamento all'articolo dell'economato per il calcolo dei costi."
    )
    allergeni = models.ManyToManyField(
        Allergene,
        blank=True,
        related_name='ingredienti',
        help_text="Allergeni contenuti nell'ingrediente.",
    )
    stagionalita = models.CharField(
        max_length=20,
        choices=STAGIONALITA_CHOICES,
        default="annuale",
    )
    disponibilita = models.JSONField(
        default=dict,
        blank=True,
        help_text="Informazioni opzionali su disponibilità o fornitore.",
    )
    informazioni_nutrizionali = models.JSONField(
        default=dict,
        blank=True,
        help_text="Valori nutrizionali (kcal, proteine, etc.).",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ingrediente"
        verbose_name_plural = "Ingredienti"
        unique_together = ("company", "nome")
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class BaseFoodItem(models.Model):
    """Catalogo di alimenti base riutilizzabili e versionabili."""

    CATEGORIA_CHOICES = [
        ("antipasto", "Antipasto"),
        ("primo", "Primo"),
        ("secondo", "Secondo"),
        ("contorno", "Contorno"),
        ("dessert", "Dessert"),
        ("bevanda", "Bevanda"),
        ("altro", "Altro"),
    ]

    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        related_name='alimenti_base',
    )
    nome = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True)
    categoria = models.CharField(
        max_length=50,
        choices=CATEGORIA_CHOICES,
        default="altro",
    )
    ingredienti_default = models.ManyToManyField(
        Ingrediente,
        blank=True,
        related_name='alimenti_default',
    )
    allergeni_default = models.ManyToManyField(
        Allergene,
        blank=True,
        related_name='alimenti_default',
    )
    informazioni_nutrizionali = models.JSONField(
        default=dict,
        blank=True,
        help_text="Valori nutrizionali standard.",
    )
    note = models.TextField(blank=True)
    versione = models.PositiveIntegerField(default=1, help_text="Versione attuale dell'alimento base.")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Alimento Base"
        verbose_name_plural = "Alimenti Base"
        unique_together = ("company", "nome", "versione")

    def __str__(self):
        return f"{self.nome} v{self.versione}"


class Piatto(models.Model):
    """Rappresenta un singolo piatto che può essere aggiunto a un menu."""

    CATEGORIA_CHOICES = BaseFoodItem.CATEGORIA_CHOICES
    STAGIONALITA_CHOICES = Ingrediente.STAGIONALITA_CHOICES

    nome = models.CharField(max_length=200, help_text="Il nome del piatto.")
    descrizione = models.TextField(blank=True, help_text="Descrizione del piatto e note sugli ingredienti.")
    categoria = models.CharField(max_length=50, choices=CATEGORIA_CHOICES, db_index=True)
    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        related_name='piatti',
        help_text="L'azienda a cui questo piatto appartiene.",
    )
    ingredienti = models.ManyToManyField(
        Ingrediente,
        blank=True,
        related_name='piatti',
        help_text="Lista ingredienti collegati al piatto.",
    )
    allergeni = models.ManyToManyField(
        Allergene,
        blank=True,
        related_name='piatti',
        help_text="Allergeni derivati per il piatto.",
    )
    allergen_summary = models.CharField(
        max_length=255,
        blank=True,
        help_text="Descrizione personalizzata degli allergeni da mostrare nel menu.",
    )
    base_item = models.ForeignKey(
        BaseFoodItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='piatti_associati',
        help_text="Voce di catalogo di riferimento per il piatto.",
    )
    variante_di = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='varianti',
        help_text="Permette di collegare piatti alternativi (es. versione vegan).",
    )
    stagionalita = models.CharField(
        max_length=20,
        choices=STAGIONALITA_CHOICES,
        default="annuale",
        help_text="Periodo di disponibilità suggerito per il piatto.",
    )
    tempo_preparazione_minuti = models.PositiveIntegerField(
        default=0,
        help_text="Tempo di preparazione stimato (minuti).",
    )
    tempo_cottura_minuti = models.PositiveIntegerField(
        default=0,
        help_text="Tempo di cottura stimato (minuti).",
    )
    porzioni = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        help_text="Numero di porzioni standard.",
    )
    prezzo = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Prezzo del piatto.",
    )
    immagine = models.ImageField(
        upload_to='menu_piatti/',
        null=True,
        blank=True,
        help_text="Foto opzionale del piatto.",
    )
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    note_internal = models.TextField(
        blank=True,
        help_text="Note interne per la brigata o per la pianificazione.",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Piatto"
        verbose_name_plural = "Piatti"
        ordering = ['categoria', 'nome']

    def __str__(self):
        return f"{self.nome} ({self.get_categoria_display()})"

    def calculate_food_cost(self, resort=None):
        """Calcola il costo totale del piatto aggregando gli ingredienti."""
        from decimal import Decimal
        total = Decimal('0.00')
        for composizione in self.composizione_ingredienti.all():
            total += composizione.get_cost(resort=resort)
        return float(total)

    @property
    def food_cost_percentage(self):
        """Calcola la percentuale di food cost rispetto al prezzo di vendita."""
        from decimal import Decimal
        cost = Decimal(str(self.calculate_food_cost()))
        prezzo = Decimal(str(self.prezzo or '0.00'))
        if prezzo <= 0:
            return 0.0
        return float((cost / prezzo) * 100.0)


class PiattoIngrediente(models.Model):
    """Relazione tecnica tra Piatto e Ingrediente con dosi e scarti."""

    UNIT_CHOICES = [
        ('g', 'Grammi'),
        ('kg', 'Chilogrammi'),
        ('ml', 'Millilitri'),
        ('lt', 'Litri'),
        ('pz', 'Pezzi'),
        ('qb', 'Quanto basta'),
    ]

    piatto = models.ForeignKey(Piatto, on_delete=models.CASCADE, related_name='composizione_ingredienti')
    ingrediente = models.ForeignKey(Ingrediente, on_delete=models.CASCADE, related_name='utilizzi_nei_piatti')
    quantita = models.DecimalField(max_digits=10, decimal_places=3, default=0, help_text="Quantità necessaria per la ricetta.")
    unita_misura = models.CharField(max_length=10, choices=UNIT_CHOICES, default='g')
    scarto_percentuale = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Percentuale di scarto (es. 20.00 per il 20%). Calcola il passaggio da peso lordo a peso netto."
    )
    note = models.CharField(max_length=255, blank=True, help_text="Note specifiche per l'uso in questa ricetta.")

    class Meta:
        verbose_name = "Ingrediente in Ricetta"
        verbose_name_plural = "Ingredienti in Ricetta"
        unique_together = ('piatto', 'ingrediente')

    def __str__(self):
        return f"{self.quantita} {self.unita_misura} di {self.ingrediente.nome} in {self.piatto.nome}"

    def get_cost(self, resort=None):
        """Calcola il costo teorico di questo ingrediente nella ricetta."""
        from decimal import Decimal
        if not self.ingrediente.economato_item:
            return Decimal('0.00')

        # Recupera l'ultimo prezzo di acquisto registrato nell'economato
        # In una evoluzione reale, qui potremmo filtrare per resort specifico
        # se l'economato supportasse prezzi diversi per resort sullo stesso articolo base.
        item = self.ingrediente.economato_item
        unit_price = Decimal(str(item.last_purchase_price or '0.00'))

        # Logica di conversione unita di misura (semplificata per ora)
        # Assumiamo che l'economato tratti l'unità base (kg, lt, pz)
        qty = Decimal(str(self.quantita))
        if self.unita_misura == 'g' or self.unita_misura == 'ml':
            qty = qty / Decimal('1000')

        # Calcola costo includendo lo scarto (quantità lorda necessaria)
        yield_factor = Decimal('1.00')
        if self.scarto_percentuale < 100:
            yield_factor = Decimal('1.00') / (Decimal('1.00') - (Decimal(str(self.scarto_percentuale)) / Decimal('100')))

        return (unit_price * qty * yield_factor).quantize(Decimal('0.01'))


class LayoutTemplate(models.Model):
    """Salva le configurazioni di layout per i menu e i cavalieri."""

    nome_layout = models.CharField(max_length=100, help_text="Nome del layout (es. 'Layout Estivo', 'Menu Serale').")
    logo = models.ImageField(upload_to='menu_logos/', null=True, blank=True, help_text="Logo da visualizzare sul menu.")
    font_principale = models.CharField(max_length=100, default='Helvetica', help_text="Nome del font da utilizzare per i titoli.")
    colore_font = models.CharField(max_length=7, default='#000000', help_text="Colore del testo in formato esadecimale (es. #RRGGBB).")
    palette_colori = models.JSONField(
        default=dict,
        blank=True,
        help_text="Palette cromatica utilizzata nel layout (accenti, sfondi).",
    )
    struttura_blocchi = models.JSONField(
        default=dict,
        blank=True,
        help_text="Configurazione drag&drop dei blocchi del menu.",
    )
    documento_word = models.FileField(
        upload_to='menu_layouts/docx/',
        null=True,
        blank=True,
        help_text="Template Word riutilizzabile (.docx).",
    )
    background_image = models.ImageField(
        upload_to='menu_layouts/backgrounds/',
        null=True,
        blank=True,
        help_text="Immagine di sfondo opzionale.",
    )
    struttura = models.ForeignKey(
        Structure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='layout_templates',
        help_text="Struttura associata al layout (selezione opzionale).",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadati aggiuntivi per l'editor front-end.",
    )
    versione = models.PositiveIntegerField(default=1)
    company = models.ForeignKey('clients.Company', on_delete=models.CASCADE, related_name='layout_templates')
    creato_da = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='layout_templates_creati')
    is_preset = models.BooleanField(default=False, help_text="Se vero, il layout è un preset di sistema non modificabile.")
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Layout Template"
        verbose_name_plural = "Layout Templates"
        unique_together = ("company", "nome_layout", "versione")

    def __str__(self):
        return self.nome_layout


class CavaliereTemplate(models.Model):
    """Template dedicato alla generazione di cavalieri per i tavoli."""

    nome = models.CharField(max_length=150)
    layout = models.ForeignKey(
        LayoutTemplate,
        on_delete=models.CASCADE,
        related_name='cavalieri',
    )
    company = models.ForeignKey(
        'clients.Company',
        on_delete=models.CASCADE,
        related_name='cavalieri_templates',
    )
    configurazione = models.JSONField(
        default=dict,
        blank=True,
        help_text="Posizionamento testi, logo, colori, dimensioni.",
    )
    documento_word = models.FileField(
        upload_to='cavalieri/docx/',
        null=True,
        blank=True,
        help_text="Template Word specifico per i cavalieri.",
    )
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='cavalieri_templates_creati',
    )
    creato_il = models.DateTimeField(auto_now_add=True)
    aggiornato_il = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Template Cavaliere"
        verbose_name_plural = "Template Cavalieri"
        unique_together = ("company", "nome")

    def __str__(self):
        return self.nome


class Menu(models.Model):
    """Rappresenta un menu specifico creato per una data o un evento."""

    TURNO_CHOICES = [
        ("colazione", "Colazione"),
        ("pranzo", "Pranzo"),
        ("cena", "Cena"),
        ("speciale", "Evento Speciale"),
    ]

    nome = models.CharField(max_length=200, help_text="Nome del menu (es. 'Menu Pranzo 15/07/2024').")
    piatti = models.ManyToManyField(Piatto, related_name='menu', help_text="Piatti inclusi in questo menu.")
    layout = models.ForeignKey(LayoutTemplate, on_delete=models.SET_NULL, null=True, blank=True, help_text="Il layout da applicare a questo menu.")
    cavaliere_template = models.ForeignKey(
        CavaliereTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Template da utilizzare per i cavalieri generati.",
    )
    struttura = models.ForeignKey(
        Structure,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='menu',
        help_text="Struttura per cui è creato il menu.",
    )
    data_evento = models.DateField(default=timezone.now, help_text="Data in cui il menu verrà servito.")
    turno = models.CharField(max_length=20, choices=TURNO_CHOICES, default="pranzo")
    ospiti_target = models.CharField(
        max_length=255,
        blank=True,
        help_text="Note sugli ospiti (es. VIP, congresso, matrimonio).",
    )
    note = models.TextField(blank=True, help_text="Note aggiuntive da mostrare internamente.")
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Metadati aggiuntivi per suggerimenti o AI.",
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    company = models.ForeignKey('clients.Company', on_delete=models.CASCADE, related_name='menu')
    creato_da = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='menu_creati')
    data_creazione = models.DateTimeField(auto_now_add=True)
    data_modifica = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Menu"
        verbose_name_plural = "Menu"
        ordering = ['-data_creazione']

    def __str__(self):
        return self.nome

    def publish(self, user):
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=["is_published", "published_at", "data_modifica"])
        MenuVersion.objects.create(menu=self, creato_da=user, payload=self.snapshot())

    def snapshot(self):
        return {
            "nome": self.nome,
            "data_evento": self.data_evento.isoformat() if self.data_evento else None,
            "turno": self.turno,
            "ospiti_target": self.ospiti_target,
            "note": self.note,
            "piatti": [
                {
                    "id": piatto.id,
                    "nome": piatto.nome,
                    "categoria": piatto.categoria,
                    "allergeni": [allergene.codice for allergene in piatto.allergeni.all()],
                }
                for piatto in self.piatti.all()
            ],
            "layout": self.layout_id,
            "cavaliere_template": self.cavaliere_template_id,
            "metadata": self.metadata,
        }


class MenuVersion(models.Model):
    """Versionamento dei menu per consentire rollback e auditing."""

    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='versioni')
    payload = models.JSONField(help_text="Snapshot completo del menu.")
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='menu_versioni_create',
    )
    creato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Versione Menu"
        verbose_name_plural = "Versioni Menu"
        ordering = ['-creato_il']

    def __str__(self):
        return f"Versione {self.creato_il:%Y-%m-%d %H:%M} - {self.menu.nome}"


class MenuDocumentJob(models.Model):
    """Stato di una generazione documenti gestita da Celery."""

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    FORMAT_CHOICES = [
        ("pdf", "PDF"),
        ("docx", "DOCX"),
        ("zip", "ZIP"),
    ]

    DOC_TYPE_CHOICES = [
        ("menu", "Menu"),
        ("cavaliere", "Cavaliere"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu = models.ForeignKey(Menu, related_name='document_jobs', on_delete=models.CASCADE)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='menu_doc_jobs'
    )
    output_format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default="pdf")
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default="menu")
    include_cavalieri = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[
            (STATUS_PENDING, "In attesa"),
            (STATUS_RUNNING, "In esecuzione"),
            (STATUS_SUCCESS, "Completato"),
            (STATUS_FAILED, "Errore"),
        ],
        default=STATUS_PENDING,
    )
    progress = models.PositiveIntegerField(default=0)
    result_file = models.FileField(upload_to='menu_documents/', null=True, blank=True)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Job {self.id} per menu {self.menu_id} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            retention_days = getattr(settings, 'MENU_DOCUMENT_RETENTION_DAYS', 7)
            self.expires_at = timezone.now() + timedelta(days=retention_days)
        super().save(*args, **kwargs)


class MenuAuditEvent(models.Model):
    ACTION_CHOICES = [
        ("snapshot", "Snapshot creato"),
        ("restore", "Ripristino versione"),
        ("clone", "Clone piatto"),
        ("publish", "Pubblicazione documenti"),
        ("insight", "Aggiornamento insights"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu = models.ForeignKey(Menu, related_name='audit_events', on_delete=models.CASCADE)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='menu_audit_events',
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.action} su menu {self.menu_id}"
