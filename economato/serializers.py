from django.utils import timezone
from rest_framework import serializers

from . import models


class EconomatoCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EconomatoCategory
        fields = ['id', 'name', 'description', 'color', 'company']


class EconomatoCostCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.EconomatoCostCenter
        fields = ['id', 'code', 'name', 'description', 'is_active', 'company']


class EconomatoItemSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='category.name', read_only=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)
    resort_name = serializers.CharField(source='resort.name', read_only=True)

    class Meta:
        model = models.EconomatoItem
        fields = [
            'id',
            'company',
            'resort',
            'resort_name',
            'category',
            'category_display',
            'supplier',
            'supplier_name',
            'code',
            'name',
            'description',
            'unit',
            'reorder_point',
            'optimal_stock',
            'last_purchase_price',
            'is_active',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ('created_at', 'updated_at')


class EconomatoStockLevelSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    item_code = serializers.CharField(source='item.code', read_only=True)
    resort_name = serializers.CharField(source='resort.name', read_only=True)
    below_reorder = serializers.SerializerMethodField()

    class Meta:
        model = models.EconomatoStockLevel
        fields = [
            'id',
            'item',
            'item_name',
            'item_code',
            'resort',
            'resort_name',
            'quantity',
            'reserved_quantity',
            'available_quantity',
            'below_reorder',
            'updated_at',
        ]
        read_only_fields = ('available_quantity', 'below_reorder', 'updated_at')

    def get_below_reorder(self, obj):
        return obj.is_below_reorder()


class EconomatoRequestItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source='item.name', read_only=True)
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = models.EconomatoRequestItem
        fields = [
            'id',
            'item',
            'item_name',
            'description',
            'quantity',
            'unit_of_measure',
            'unit_cost',
            'total_cost',
            'supplier',
        ]


class EconomatoRequestSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    resort_name = serializers.CharField(source='resort.name', read_only=True)
    items = EconomatoRequestItemSerializer(many=True)

    class Meta:
        model = models.EconomatoRequest
        fields = [
            'id',
            'company',
            'resort',
            'resort_name',
            'cost_center',
            'status',
            'priority',
            'needed_by',
            'notes',
            'requested_by',
            'requested_by_name',
            'approved_by',
            'approved_by_name',
            'total_estimated_cost',
            'created_at',
            'updated_at',
            'cancellation_reason',
            'items',
        ]
        read_only_fields = (
            'requested_by',
            'requested_by_name',
            'approved_by',
            'approved_by_name',
            'total_estimated_cost',
            'created_at',
            'updated_at',
        )

    def validate_needed_by(self, value):
        if value and value < timezone.now().date():
            raise serializers.ValidationError("La data richiesta non può essere nel passato.")
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Inserire almeno una voce nella richiesta.")
        for item in value:
            if item.get('quantity', 0) <= 0:
                raise serializers.ValidationError("La quantità deve essere maggiore di zero.")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items', [])
        request = models.EconomatoRequest.objects.create(**validated_data)
        self._save_items(request, items_data)
        request.recalculate_total()
        return request

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if items_data is not None:
            instance.items.all().delete()
            self._save_items(instance, items_data)
            instance.recalculate_total()
        return instance

    def _save_items(self, request, items_data):
        models.EconomatoRequestItem.objects.bulk_create([
            models.EconomatoRequestItem(request=request, **item_data) for item_data in items_data
        ])


class EconomatoTimelineEventSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = models.EconomatoTimelineEvent
        fields = ['id', 'verb', 'payload', 'created_at', 'created_by', 'created_by_name']
        read_only_fields = ('created_at', 'created_by', 'created_by_name')


class EconomatoOverviewSerializer(serializers.Serializer):
    stats = serializers.DictField(child=serializers.FloatField())
    low_stock_items = EconomatoStockLevelSerializer(many=True)
    requests_by_status = serializers.DictField(child=serializers.IntegerField())
    recent_requests = EconomatoRequestSerializer(many=True)
    available_companies = serializers.ListField(child=serializers.DictField(), allow_empty=True)
    available_resorts = serializers.ListField(child=serializers.DictField(), allow_empty=True)
    scope = serializers.DictField()
