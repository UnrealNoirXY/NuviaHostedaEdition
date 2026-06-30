from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from resort.models import Room, Resort
from .forms import TicketUpdateForm
from .models import Ticket, TicketComment, TicketHistory, TicketDeadlineChange


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'role']


class RoomSerializer(serializers.ModelSerializer):
    resort = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Room
        fields = ['id', 'name', 'description', 'resort']


class ResortSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resort
        fields = ['id', 'name']


class TicketCommentSerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)

    class Meta:
        model = TicketComment
        fields = ['id', 'author', 'comment', 'attachment', 'created_at']
        read_only_fields = fields


class TicketHistorySerializer(serializers.ModelSerializer):
    author = UserSummarySerializer(read_only=True)

    class Meta:
        model = TicketHistory
        fields = ['id', 'author', 'action', 'timestamp']
        read_only_fields = fields


class TicketDeadlineChangeSerializer(serializers.ModelSerializer):
    changed_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = TicketDeadlineChange
        fields = [
            'id',
            'previous_due_date',
            'new_due_date',
            'changed_by',
            'justification',
            'change_type',
            'created_at',
        ]
        read_only_fields = fields


class TicketSerializer(serializers.ModelSerializer):
    assigned_to = UserSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    room = RoomSerializer(read_only=True)
    resort = ResortSerializer(read_only=True)
    comments = TicketCommentSerializer(many=True, read_only=True)
    history = TicketHistorySerializer(many=True, read_only=True)
    deadline_changes = TicketDeadlineChangeSerializer(many=True, read_only=True)
    completion_photo = serializers.ImageField(read_only=True)
    acknowledged_by = UserSummarySerializer(read_only=True)
    claimed_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = [
            'id',
            'title',
            'description',
            'notes',
            'status',
            'priority',
            'due_date',
            'completion_photo',
            'attachment',
            'room',
            'resort',
            'required_skill',
            'assigned_to',
            'created_by',
            'created_at',
            'updated_at',
            'comments',
            'history',
            'deadline_changes',
            'estimated_cost',
            'actual_cost',
            'initial_due_date',
            'acknowledged_due_date',
            'acknowledged_by',
            'acknowledged_at',
            'claimed_by',
            'claimed_at',
            'first_claimed_at',
            'last_released_at',
        ]
        read_only_fields = [
            'attachment',
            'assigned_to',
            'created_by',
            'created_at',
            'updated_at',
            'comments',
            'history',
            'deadline_changes',
            'initial_due_date',
            'acknowledged_due_date',
            'acknowledged_by',
            'acknowledged_at',
            'claimed_by',
            'claimed_at',
            'first_claimed_at',
            'last_released_at',
        ]


class TicketCreateSerializer(serializers.ModelSerializer):
    confirmed = serializers.BooleanField(write_only=True)
    notification_mode = serializers.ChoiceField(
        choices=[('assigned', 'assigned'), ('selected', 'selected')],
        required=False,
        default='assigned',
        write_only=True,
    )
    notify_maintainers = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.MAINTAINER),
        many=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = Ticket
        fields = [
            'title',
            'description',
            'priority',
            'room',
            'resort',
            'required_skill',
            'attachment',
            'assigned_to',
            'due_date',
            'estimated_cost',
            'actual_cost',
            'confirmed',
            'notification_mode',
            'notify_maintainers',
        ]

    def validate_due_date(self, value):
        if value and value <= timezone.now():
            raise serializers.ValidationError('La scadenza deve essere nel futuro.')
        return value

    def validate(self, attrs):
        confirmed = attrs.pop('confirmed', False)
        if not confirmed:
            raise serializers.ValidationError('Devi confermare i dettagli del ticket prima di crearlo.')
        notification_mode = attrs.get('notification_mode', 'assigned')
        notify_maintainers = attrs.get('notify_maintainers', [])
        assigned_to = attrs.get('assigned_to')
        if assigned_to:
            resort = attrs.get('resort')
            room = attrs.get('room')
            if resort is None and room is not None:
                resort = room.resort
            if assigned_to.role != User.MAINTAINER:
                raise serializers.ValidationError("Puoi assegnare il ticket solo a un manutentore valido.")
            if not resort or assigned_to.resort_id != resort.id:
                raise serializers.ValidationError("Il manutentore assegnato non appartiene alla struttura selezionata.")

        resort = attrs.get('resort')
        room = attrs.get('room')
        if resort is None and room is not None:
            resort = room.resort

        if notification_mode == 'assigned':
            if not assigned_to:
                raise serializers.ValidationError('Seleziona un manutentore o usa la modalità di notifica manuale.')
            if notify_maintainers:
                raise serializers.ValidationError('Non puoi selezionare manutentori se invii solo all’assegnato.')
        else:
            if not resort:
                raise serializers.ValidationError('Seleziona una struttura per inviare notifiche ai manutentori.')
            if not notify_maintainers:
                raise serializers.ValidationError('Seleziona almeno un manutentore da notificare.')
            for maintainer in notify_maintainers:
                if maintainer.role != User.MAINTAINER:
                    raise serializers.ValidationError('Puoi notificare solo manutentori validi.')
                if maintainer.resort_id != resort.id:
                    raise serializers.ValidationError('Il manutentore selezionato non appartiene alla struttura scelta.')

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data.pop('notification_mode', None)
        validated_data.pop('notify_maintainers', None)
        return super().create(validated_data)


class TicketUpdateSerializer(serializers.ModelSerializer):
    deadline_justification = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)
    acknowledged_due_date = serializers.DateTimeField(required=False, allow_null=True)

    class Meta:
        model = Ticket
        fields = [
            'status',
            'notes',
            'due_date',
            'completion_photo',
            'deadline_justification',
            'actual_cost',
            'estimated_cost',
            'acknowledged_due_date',
        ]
        extra_kwargs = {
            'completion_photo': {'required': False, 'allow_null': True},
            'due_date': {'required': False, 'allow_null': True},
            'status': {'required': False},
            'notes': {'required': False},
            'actual_cost': {'required': False, 'allow_null': True},
            'estimated_cost': {'required': False, 'allow_null': True},
            'acknowledged_due_date': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        ticket = self.instance
        user = self.context['request'].user
        new_status = attrs.get('status', ticket.status)
        due_date = attrs.get('due_date', ticket.due_date)
        justification = attrs.get('deadline_justification')
        completion_photo = attrs.get('completion_photo')
        acknowledged_due = attrs.get('acknowledged_due_date', ticket.acknowledged_due_date)

        if due_date and due_date <= timezone.now():
            raise serializers.ValidationError('La scadenza non può essere nel passato.')

        if due_date != ticket.due_date:
            if not TicketUpdateForm._user_can_freely_edit_deadline(user):
                if ticket.due_date is None and due_date:
                    raise serializers.ValidationError('Non puoi impostare una scadenza per questo ticket.')
                if ticket.due_date and due_date and due_date <= ticket.due_date:
                    raise serializers.ValidationError('Puoi solo prorogare la scadenza.')
                if not justification:
                    raise serializers.ValidationError('La proroga richiede una motivazione.')

        if new_status == 'closed' and not (completion_photo or ticket.completion_photo):
            raise serializers.ValidationError('Per chiudere il ticket è obbligatorio caricare una foto del lavoro finito.')

        effective_due = due_date or ticket.due_date

        if new_status in ['in_progress', 'resolved', 'closed']:
            if effective_due is None:
                raise serializers.ValidationError('Definisci una scadenza prima di procedere.')
            if not acknowledged_due:
                raise serializers.ValidationError('Per proseguire devi confermare la scadenza.')

        if acknowledged_due:
            if effective_due is None:
                raise serializers.ValidationError('Non puoi confermare una scadenza inesistente.')
            if ticket.due_date and due_date and due_date != ticket.due_date and acknowledged_due != due_date:
                raise serializers.ValidationError('Conferma la scadenza dopo averla aggiornata.')
            if acknowledged_due != effective_due:
                raise serializers.ValidationError('La scadenza confermata deve coincidere con la scadenza del ticket.')

        return attrs

    def update(self, instance, validated_data):
        acknowledged_due = validated_data.pop('acknowledged_due_date', serializers.empty)
        previous_due = instance.due_date
        ticket = super().update(instance, validated_data)

        if 'due_date' in validated_data and ticket.due_date != previous_due:
            ticket.acknowledged_due_date = None
            ticket.acknowledged_by = None
            ticket.acknowledged_at = None
            ticket.save(update_fields=['acknowledged_due_date', 'acknowledged_by', 'acknowledged_at'])
        elif acknowledged_due is not serializers.empty:
            if acknowledged_due:
                ticket.acknowledged_due_date = acknowledged_due
                ticket.acknowledged_by = self.context['request'].user
                ticket.acknowledged_at = timezone.now()
            else:
                ticket.acknowledged_due_date = None
                ticket.acknowledged_by = None
                ticket.acknowledged_at = None
            ticket.save(update_fields=['acknowledged_due_date', 'acknowledged_by', 'acknowledged_at'])

        return ticket


class TicketCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketComment
        fields = ['comment', 'attachment']


class TicketExtensionSerializer(serializers.Serializer):
    due_date = serializers.DateTimeField()
    justification = serializers.CharField(trim_whitespace=True)

    def validate(self, attrs):
        ticket = self.context['ticket']
        user = self.context['request'].user
        due_date = attrs['due_date']

        if not attrs['justification'].strip():
            raise serializers.ValidationError('La motivazione è obbligatoria.')

        if not TicketUpdateForm._user_can_freely_edit_deadline(user):
            if ticket.due_date is None:
                raise serializers.ValidationError('Non puoi impostare una scadenza per questo ticket.')
            if due_date <= ticket.due_date:
                raise serializers.ValidationError('Puoi solo prorogare la scadenza.')

        if due_date <= timezone.now():
            raise serializers.ValidationError('La nuova scadenza deve essere nel futuro.')

        return attrs
