"""Serializzatori DRF per il Menu Creation Studio."""

from datetime import date

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from clients.models import StructureMembership

from django.utils import timezone

from .models import (
    Allergene,
    Ingrediente,
    BaseFoodItem,
    Piatto,
    PiattoIngrediente,
    LayoutTemplate,
    CavaliereTemplate,
    Menu,
    MenuVersion,
    MenuDocumentJob,
    MenuAuditEvent,
)


class AllergeneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergene
        fields = ('id', 'codice', 'nome', 'icona_svg')


class IngredienteSerializer(serializers.ModelSerializer):
    allergeni = serializers.PrimaryKeyRelatedField(
        queryset=Allergene.objects.all(), many=True, required=False
    )
    allergeni_details = AllergeneSerializer(source='allergeni', many=True, read_only=True)
    economato_item_details = serializers.SerializerMethodField()

    class Meta:
        model = Ingrediente
        exclude = ('company', 'created_at', 'updated_at')

    def get_economato_item_details(self, obj):
        if not obj.economato_item:
            return None
        return {
            'id': obj.economato_item.id,
            'last_purchase_price': obj.economato_item.last_purchase_price,
            'unit': obj.economato_item.unit,
        }


class PiattoIngredienteSerializer(serializers.ModelSerializer):
    ingrediente_nome = serializers.CharField(source='ingrediente.nome', read_only=True)
    costo_teorico = serializers.SerializerMethodField()

    class Meta:
        model = PiattoIngrediente
        fields = ('id', 'ingrediente', 'ingrediente_nome', 'quantita', 'unita_misura', 'scarto_percentuale', 'note', 'costo_teorico')

    def get_costo_teorico(self, obj):
        return obj.get_cost()


class PiattoSerializer(serializers.ModelSerializer):
    """Serializer dettagliato per GET (singolo) e operazioni CUD."""
    composizione_details = PiattoIngredienteSerializer(source='composizione_ingredienti', many=True, read_only=True)
    food_cost_teorico = serializers.FloatField(source='calculate_food_cost', read_only=True)
    food_cost_percentuale = serializers.FloatField(source='food_cost_percentage', read_only=True)
    composizione_input = serializers.JSONField(write_only=True, required=False, help_text="Lista di oggetti {ingrediente_id, quantita, unita_misura, scarto_percentuale}")

    allergeni = AllergeneSerializer(many=True, read_only=True)
    allergeni_ids = serializers.PrimaryKeyRelatedField(
        queryset=Allergene.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='allergeni'
    )
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)

    class Meta:
        model = Piatto
        fields = '__all__'
        read_only_fields = ('company', 'created_at', 'updated_at')

    @transaction.atomic
    def create(self, validated_data):
        composizione_data = validated_data.pop('composizione_input', [])
        piatto = super().create(validated_data)
        self._set_composizione(piatto, composizione_data)
        return piatto

    @transaction.atomic
    def update(self, instance, validated_data):
        composizione_data = validated_data.pop('composizione_input', None)
        piatto = super().update(instance, validated_data)
        if composizione_data is not None:
            self._set_composizione(piatto, composizione_data)
        return piatto

    def _set_composizione(self, piatto, composizione_data):
        piatto.composizione_ingredienti.all().delete()
        for item in composizione_data:
            PiattoIngrediente.objects.create(
                piatto=piatto,
                ingrediente_id=item.get('ingrediente_id'),
                quantita=item.get('quantita', 0),
                unita_misura=item.get('unita_misura', 'g'),
                scarto_percentuale=item.get('scarto_percentuale', 0),
                note=item.get('note', '')
            )


class PiattoListSerializer(serializers.ModelSerializer):
    """Serializer leggero per la lista dei piatti."""
    categoria_display = serializers.CharField(source='get_categoria_display', read_only=True)
    allergeni_details = AllergeneSerializer(source='allergeni', many=True, read_only=True)
    ingredienti_details = IngredienteSerializer(source='ingredienti', many=True, read_only=True)
    food_cost_teorico = serializers.FloatField(source='calculate_food_cost', read_only=True)
    food_cost_percentuale = serializers.FloatField(source='food_cost_percentage', read_only=True)

    class Meta:
        model = Piatto
        fields = (
            'id',
            'nome',
            'categoria',
            'categoria_display',
            'prezzo',
            'is_active',
            'stagionalita',
            'descrizione',
            'immagine',
            'allergeni_details',
            'ingredienti_details',
            'variante_di',
            'base_item',
            'food_cost_teorico',
            'food_cost_percentuale',
        )


class BaseFoodItemSerializer(serializers.ModelSerializer):
    ingredienti_details = IngredienteSerializer(
        source='ingredienti_default', many=True, read_only=True
    )
    allergeni_details = AllergeneSerializer(
        source='allergeni_default', many=True, read_only=True
    )

    class Meta:
        model = BaseFoodItem
        fields = '__all__'


class LayoutTemplateSerializer(serializers.ModelSerializer):
    logo = serializers.ImageField(max_length=None, use_url=True, allow_null=True, required=False)

    class Meta:
        model = LayoutTemplate
        fields = '__all__'
        read_only_fields = ('company', 'creato_da', 'data_creazione', 'data_modifica')


class CavaliereTemplateSerializer(serializers.ModelSerializer):
    layout_details = LayoutTemplateSerializer(source='layout', read_only=True)

    class Meta:
        model = CavaliereTemplate
        fields = '__all__'


class MenuVersionSerializer(serializers.ModelSerializer):
    creato_da_display = serializers.CharField(source='creato_da.get_full_name', read_only=True)

    class Meta:
        model = MenuVersion
        fields = '__all__'


class MenuDocumentJobSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = MenuDocumentJob
        fields = [
            'id',
            'menu',
            'status',
            'output_format',
            'doc_type',
            'include_cavalieri',
            'progress',
            'error_message',
            'created_at',
            'updated_at',
            'completed_at',
            'expires_at',
            'download_url',
            'is_expired',
        ]
        read_only_fields = fields

    def get_download_url(self, obj):
        if obj.result_file and not self.get_is_expired(obj):
            request = self.context.get('request')
            url = obj.result_file.url
            return request.build_absolute_uri(url) if request else url
        return None

    def get_is_expired(self, obj):
        if obj.expires_at is None:
            return False
        return timezone.now() > obj.expires_at


class MenuAuditEventSerializer(serializers.ModelSerializer):
    actor_display = serializers.CharField(source='actor.get_full_name', read_only=True)

    class Meta:
        model = MenuAuditEvent
        fields = ('id', 'action', 'metadata', 'created_at', 'actor_display', 'menu')
        read_only_fields = fields


class MenuSerializer(serializers.ModelSerializer):
    piatti_details = serializers.SerializerMethodField()
    piatti = serializers.PrimaryKeyRelatedField(
        queryset=Piatto.objects.all(), many=True, required=False
    )
    versioni = MenuVersionSerializer(many=True, read_only=True)

    class Meta:
        model = Menu
        fields = '__all__'
        read_only_fields = (
            'company',
            'creato_da',
            'data_creazione',
            'data_modifica',
        )

    @transaction.atomic
    def create(self, validated_data):
        piatti_data = validated_data.pop('piatti', [])
        metadata = validated_data.pop('metadata', {}) or {}
        menu = Menu.objects.create(metadata=metadata, **validated_data)
        menu.piatti.set(piatti_data)
        if piatti_data:
            metadata['piatti_order'] = [p.id for p in piatti_data]
            menu.metadata = metadata
            menu.save(update_fields=['metadata'])
        return menu

    @transaction.atomic
    def update(self, instance, validated_data):
        piatti_data = validated_data.pop('piatti', None)
        metadata = validated_data.get('metadata', instance.metadata or {}) or {}
        instance = super().update(instance, validated_data)
        if piatti_data is not None:
            instance.piatti.set(piatti_data)
            metadata['piatti_order'] = [p.id for p in piatti_data]
        instance.metadata = metadata
        instance.save(update_fields=['metadata'])
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        ordered_piatti = self._ordered_piatti(instance)
        data['piatti'] = [p.id for p in ordered_piatti]
        data['piatti_details'] = PiattoListSerializer(ordered_piatti, many=True).data
        data['user_permissions'] = self._resolve_user_permissions(instance)
        return data

    def _ordered_piatti(self, instance):
        piatti = list(instance.piatti.all())
        order = []
        if instance.metadata:
            order = instance.metadata.get('piatti_order', []) or []
        piatti_map = {piatto.id: piatto for piatto in piatti}
        ordered = [piatti_map[pid] for pid in order if pid in piatti_map]
        remaining = [p for p in piatti if p.id not in order]
        remaining.sort(key=lambda p: (p.categoria, p.nome))
        return ordered + remaining

    def get_piatti_details(self, instance):
        return PiattoListSerializer(self._ordered_piatti(instance), many=True).data

    def _resolve_user_permissions(self, instance):
        request = self.context.get('request') if self.context else None
        user = getattr(request, 'user', None)
        default = {
            'can_edit': False,
            'can_publish': False,
            'can_approve': False,
        }

        if not user or not user.is_authenticated:
            return default

        if user.is_superuser or user.role == 'superadmin':
            return {key: True for key in default}

        if not instance.struttura:
            return default

        today = date.today()
        membership = (
            StructureMembership.objects.select_related('role')
            .filter(
                user=user,
                structure=instance.struttura,
                is_active=True,
                valid_from__lte=today,
            )
            .filter(Q(valid_to__isnull=True) | Q(valid_to__gte=today))
            .first()
        )

        if not membership or not membership.role:
            return default

        return {
            'can_edit': membership.role.can_edit_menus,
            'can_publish': membership.role.can_publish_menu,
            'can_approve': membership.role.can_approve_menu,
        }
