from decimal import Decimal

from datetime import timedelta

from django.db import transaction
from django.db.models import Q, Count, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.urls import reverse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from accounts.models import User
from resort.models import Resort, Room
from .emails import (
    send_new_assignment_notification,
    send_new_ticket_notification,
    send_new_comment_notification,
    send_status_change_notification,
    send_ticket_claim_notification,
    send_ticket_release_notification,
)
from .forms import TicketUpdateForm
from .models import Ticket, TicketComment, TicketHistory, TicketDeadlineChange, ProactiveMaintenanceAlert
from .serializers import (
    TicketSerializer,
    TicketCreateSerializer,
    TicketUpdateSerializer,
    TicketCommentSerializer,
    TicketCommentCreateSerializer,
    TicketExtensionSerializer,
)


class TicketPermission(permissions.IsAuthenticated):
    """Base permission enforcing authenticated access and tool visibility."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        user = request.user
        return user.is_superuser or user.has_maintenance_access or user.role in (
            User.MAINTAINER,
            User.HEAD_MAINTAINER,
            User.OWNER,
            User.MAINTENANCE_MANAGER,
            User.SUPERADMIN,
        )


class TicketViewSet(viewsets.ModelViewSet):
    permission_classes = [TicketPermission]
    queryset = Ticket.objects.select_related(
        'resort__company', 'room', 'assigned_to', 'created_by'
    ).prefetch_related(
        'comments__author', 'history__author', 'deadline_changes__changed_by'
    )

    ROOM_OK = 'ok'
    ROOM_WARNING = 'warning'
    ROOM_CRITICAL = 'critical'

    def get_serializer_class(self):
        if self.action == 'create':
            return TicketCreateSerializer
        if self.action in ['update', 'partial_update']:
            return TicketUpdateSerializer
        if self.action == 'add_comment':
            return TicketCommentCreateSerializer
        if self.action == 'extend_deadline':
            return TicketExtensionSerializer
        return TicketSerializer

    def get_queryset(self):
        user = self.request.user
        qs = super().get_queryset()
        if user.is_superuser or user.role in [User.SUPERADMIN, User.OWNER, User.MAINTENANCE_MANAGER, User.HEAD_MAINTAINER]:
            if user.company:
                return qs.filter(resort__company=user.company)
            return qs
        if user.role == User.MAINTAINER:
            filters = Q(assigned_to=user) | Q(created_by=user)
            if user.resort_id:
                filters |= Q(resort_id=user.resort_id, assigned_to__isnull=True)
            return qs.filter(filters)
        if user.resort:
            return qs.filter(resort=user.resort)
        return qs.none()

    def _accessible_resorts(self, user):
        resorts = Resort.objects.select_related('company')
        if user.is_superuser or user.role in [User.SUPERADMIN]:
            if user.role == User.SUPERADMIN and user.company_id:
                return resorts.filter(company=user.company)
            return resorts
        if user.role in [User.OWNER, User.MAINTENANCE_MANAGER]:
            if user.company_id:
                return resorts.filter(company=user.company)
            return resorts.none()
        if user.role in [User.HEAD_MAINTAINER, User.MAINTAINER]:
            if user.resort_id:
                return resorts.filter(pk=user.resort_id)
            return resorts.none()
        if user.company_id:
            return resorts.filter(company=user.company)
        if user.resort_id:
            return resorts.filter(pk=user.resort_id)
        return resorts.none()

    def _accessible_rooms(self, user):
        return Room.objects.filter(resort__in=self._accessible_resorts(user)).select_related('resort__company')

    def _build_absolute_url(self, ticket):
        return f"{self.request.build_absolute_uri(reverse('ticket_detail', args=[ticket.id]))}"

    def _user_can_claim_ticket(self, user, ticket):
        if user.is_superuser:
            return True
        if not user.has_maintenance_access and user.role not in (
            User.MAINTAINER,
            User.HEAD_MAINTAINER,
            User.MAINTENANCE_MANAGER,
            User.OWNER,
            User.SUPERADMIN,
        ):
            return False

        if user.role in [User.MAINTAINER, User.HEAD_MAINTAINER]:
            return user.resort_id == ticket.resort_id

        if user.role in [User.MAINTENANCE_MANAGER, User.OWNER]:
            return user.company_id == ticket.resort.company_id if ticket.resort and ticket.resort.company_id else False

        if user.role == User.SUPERADMIN:
            return user.company_id == ticket.resort.company_id if user.company_id else True

        return False

    def _user_can_force_release(self, user, ticket):
        if user.is_superuser:
            return True
        if ticket.assigned_to_id == user.id:
            return True
        if user.role in [User.SUPERADMIN, User.OWNER, User.MAINTENANCE_MANAGER, User.HEAD_MAINTAINER]:
            return self._user_can_claim_ticket(user, ticket)
        return False

    def _user_can_claim_any(self, user):
        if user.is_superuser:
            return True
        return user.role in (
            User.MAINTAINER,
            User.HEAD_MAINTAINER,
            User.MAINTENANCE_MANAGER,
            User.OWNER,
            User.SUPERADMIN,
        )

    @transaction.atomic
    def perform_create(self, serializer):
        user = self.request.user
        due_date = serializer.validated_data.get('due_date')
        notification_mode = serializer.validated_data.get('notification_mode', 'assigned')
        notify_maintainers = serializer.validated_data.get('notify_maintainers', [])
        if due_date and not TicketUpdateForm._user_can_freely_edit_deadline(user):
            raise PermissionDenied("Non hai i permessi per impostare una scadenza.")

        ticket = serializer.save(created_by=user)

        if ticket.due_date and not ticket.initial_due_date:
            ticket.initial_due_date = ticket.due_date
            ticket.save(update_fields=['initial_due_date'])

        if due_date:
            TicketDeadlineChange.objects.create(
                ticket=ticket,
                previous_due_date=None,
                new_due_date=due_date,
                changed_by=user,
                justification="",
                change_type=TicketDeadlineChange.CHANGE_SET,
            )
            TicketHistory.objects.create(
                ticket=ticket,
                author=user,
                action=f"Scadenza impostata al {timezone.localtime(due_date).strftime('%d/%m/%Y %H:%M')}",
            )

        if ticket.assigned_to:
            now = timezone.now()
            updates = ['claimed_by', 'claimed_at']
            ticket.claimed_by = ticket.assigned_to
            ticket.claimed_at = now
            if not ticket.first_claimed_at:
                ticket.first_claimed_at = now
                updates.append('first_claimed_at')
            ticket.last_released_at = None
            updates.append('last_released_at')
            ticket.unassigned_notification_sent_at = None
            updates.append('unassigned_notification_sent_at')
            ticket.save(update_fields=updates)

            TicketHistory.objects.create(
                ticket=ticket,
                author=user,
                action=f"Assegnato a {ticket.assigned_to.get_full_name() or ticket.assigned_to.username}",
            )

            absolute_url = self._build_absolute_url(ticket)
            if notification_mode == 'assigned':
                send_new_assignment_notification(ticket, absolute_url)

        if notification_mode == 'selected' and notify_maintainers:
            absolute_url = self._build_absolute_url(ticket)
            send_new_ticket_notification(ticket, notify_maintainers, absolute_url)

        TicketHistory.objects.create(ticket=ticket, author=user, action="Ticket creato")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        ticket = self.get_queryset().get(pk=serializer.instance.pk)
        output = TicketSerializer(ticket, context={'request': request})
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial, context={'request': request})
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        justification = validated.pop('deadline_justification', '')
        due_before = instance.due_date
        status_before = instance.status
        ack_before = instance.acknowledged_due_date

        due_changed = 'due_date' in validated and validated['due_date'] != due_before
        status_changed = 'status' in validated and validated['status'] != status_before
        completion_uploaded = 'completion_photo' in validated and validated['completion_photo']

        ticket = serializer.save()
        ack_after = ticket.acknowledged_due_date

        if due_changed:
            new_due = ticket.due_date
            ticket.deadline_reminder_sent_at = None
            update_fields = ['deadline_reminder_sent_at']
            if new_due and ticket.initial_due_date is None:
                ticket.initial_due_date = new_due
                update_fields.append('initial_due_date')
            ticket.save(update_fields=update_fields)
            change_type = TicketDeadlineChange.CHANGE_SET
            if due_before and new_due:
                change_type = TicketDeadlineChange.CHANGE_EXTEND if new_due > due_before else TicketDeadlineChange.CHANGE_SHORTEN
            elif due_before and not new_due:
                change_type = TicketDeadlineChange.CHANGE_SHORTEN

            TicketDeadlineChange.objects.create(
                ticket=ticket,
                previous_due_date=due_before,
                new_due_date=new_due,
                changed_by=request.user,
                justification=justification,
                change_type=change_type,
            )

            message = "Scadenza rimossa"
            if new_due:
                message = f"Scadenza aggiornata a {timezone.localtime(new_due).strftime('%d/%m/%Y %H:%M')}"
            if justification:
                message += f" (Motivazione: {justification})"
            TicketHistory.objects.create(ticket=ticket, author=request.user, action=message)

            if ack_before:
                TicketHistory.objects.create(
                    ticket=ticket,
                    author=request.user,
                    action="Conferma scadenza annullata: il manutentore deve riconfermare la nuova data.",
                )

        if completion_uploaded:
            TicketHistory.objects.create(ticket=ticket, author=request.user, action="Foto di completamento caricata")

        if status_changed:
            old_label = dict(Ticket.STATUS_CHOICES)[status_before]
            new_label = dict(Ticket.STATUS_CHOICES)[ticket.status]
            TicketHistory.objects.create(
                ticket=ticket,
                author=request.user,
                action=f"Stato cambiato da {old_label} a {new_label}",
            )
            absolute_url = self._build_absolute_url(ticket)
            send_status_change_notification(ticket, old_label, new_label, absolute_url)

        if ack_after != ack_before:
            if ack_after:
                TicketHistory.objects.create(
                    ticket=ticket,
                    author=request.user,
                    action=f"Scadenza confermata per il {timezone.localtime(ack_after).strftime('%d/%m/%Y %H:%M')}",
                )
            elif ack_before:
                TicketHistory.objects.create(
                    ticket=ticket,
                    author=request.user,
                    action="Conferma scadenza rimossa",
                )

        output = TicketSerializer(ticket, context={'request': request})
        return Response(output.data)

    @action(detail=True, methods=['post'], url_path='comments')
    def add_comment(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comment = TicketComment.objects.create(
            ticket=ticket,
            author=request.user,
            comment=serializer.validated_data.get('comment', ''),
            attachment=serializer.validated_data.get('attachment'),
        )

        TicketHistory.objects.create(ticket=ticket, author=request.user, action="Nota aggiunta")
        absolute_url = self._build_absolute_url(ticket)
        send_new_comment_notification(comment, absolute_url)

        return Response(TicketCommentSerializer(comment, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='extend-deadline')
    def extend_deadline(self, request, pk=None):
        ticket = self.get_object()
        serializer = TicketExtensionSerializer(data=request.data, context={'ticket': ticket, 'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        justification = data['justification']
        new_due = data['due_date']

        with transaction.atomic():
            previous_due = ticket.due_date
            ticket.due_date = new_due
            ticket.deadline_reminder_sent_at = None
            ticket.save(update_fields=['due_date', 'deadline_reminder_sent_at'])

            TicketDeadlineChange.objects.create(
                ticket=ticket,
                previous_due_date=previous_due,
                new_due_date=new_due,
                changed_by=request.user,
                justification=justification,
                change_type=TicketDeadlineChange.CHANGE_EXTEND,
            )

            TicketHistory.objects.create(
                ticket=ticket,
                author=request.user,
                action=f"Scadenza prorogata a {timezone.localtime(new_due).strftime('%d/%m/%Y %H:%M')} (Motivazione: {justification})",
            )

            ticket.acknowledged_due_date = None
            ticket.acknowledged_by = None
            ticket.acknowledged_at = None
            ticket.save(update_fields=['acknowledged_due_date', 'acknowledged_by', 'acknowledged_at'])

            TicketHistory.objects.create(
                ticket=ticket,
                author=request.user,
                action="Conferma scadenza annullata: nuova conferma richiesta.",
            )

        return Response(TicketSerializer(ticket, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='claim')
    def claim(self, request, pk=None):
        ticket = self.get_object()
        user = request.user

        if ticket.status in ['resolved', 'closed']:
            return Response({'detail': 'Il ticket è già stato completato.'}, status=status.HTTP_400_BAD_REQUEST)

        if ticket.assigned_to and ticket.assigned_to != user:
            return Response({'detail': 'Il ticket è già stato preso in carico da un altro manutentore.'}, status=status.HTTP_409_CONFLICT)

        if not self._user_can_claim_ticket(user, ticket):
            raise PermissionDenied('Non puoi prendere in carico questo ticket.')

        now = timezone.now()
        updates = ['assigned_to', 'claimed_by', 'claimed_at', 'last_released_at', 'unassigned_notification_sent_at']
        ticket.assigned_to = user
        ticket.claimed_by = user
        ticket.claimed_at = now
        ticket.last_released_at = None
        ticket.unassigned_notification_sent_at = None
        if not ticket.first_claimed_at:
            ticket.first_claimed_at = now
            updates.append('first_claimed_at')
        ticket.save(update_fields=updates)

        TicketHistory.objects.create(
            ticket=ticket,
            author=user,
            action=f"Ticket preso in carico da {user.get_full_name() or user.username}",
        )

        absolute_url = self._build_absolute_url(ticket)
        send_ticket_claim_notification(ticket, user, absolute_url)

        return Response(TicketSerializer(ticket, context={'request': request}).data)

    @action(detail=True, methods=['post'], url_path='release')
    def release(self, request, pk=None):
        ticket = self.get_object()
        user = request.user

        if not ticket.assigned_to:
            return Response(TicketSerializer(ticket, context={'request': request}).data)

        if not self._user_can_force_release(user, ticket):
            raise PermissionDenied('Non puoi rilasciare questo ticket.')

        updates = ['assigned_to', 'claimed_by', 'claimed_at', 'last_released_at', 'unassigned_notification_sent_at']
        ticket.assigned_to = None
        ticket.claimed_by = None
        ticket.claimed_at = None
        ticket.last_released_at = timezone.now()
        ticket.unassigned_notification_sent_at = None
        ticket.save(update_fields=updates)

        TicketHistory.objects.create(
            ticket=ticket,
            author=user,
            action=f"Ticket rilasciato da {user.get_full_name() or user.username}",
        )

        absolute_url = self._build_absolute_url(ticket)
        send_ticket_release_notification(ticket, user, absolute_url)

        return Response(TicketSerializer(ticket, context={'request': request}).data)

    @action(detail=False, methods=['get'], url_path='room-dashboard')
    def room_dashboard(self, request):
        user = request.user

        accessible_rooms = list(self._accessible_rooms(user))
        if not accessible_rooms:
            return Response({'companies': [], 'summary': self._empty_room_summary()}, status=status.HTTP_200_OK)

        room_ids = [room.id for room in accessible_rooms]
        now = timezone.now()

        ticket_qs = Ticket.objects.filter(room_id__in=room_ids)

        aggregates = {
            entry['room_id']: entry
            for entry in ticket_qs.values('room_id').annotate(
                total=Count('id'),
                open_count=Count('id', filter=Q(status__in=['open', 'in_progress'])),
                in_progress_count=Count('id', filter=Q(status='in_progress')),
                resolved_count=Count('id', filter=Q(status__in=['resolved', 'closed'])),
                overdue_count=Count(
                    'id',
                    filter=Q(status__in=['open', 'in_progress']) & Q(due_date__lt=now),
                ),
                critical_priority_count=Count(
                    'id',
                    filter=Q(status__in=['open', 'in_progress'])
                    & (Q(priority__in=[Ticket.PRIORITY_HIGH, Ticket.PRIORITY_URGENT]) | Q(due_date__lt=now)),
                ),
                planned_budget=Coalesce(
                    Sum(
                        'estimated_cost',
                        filter=Q(status__in=['open', 'in_progress']),
                    ),
                    Decimal('0'),
                ),
                invested_budget=Coalesce(
                    Sum(
                        'actual_cost',
                        filter=Q(status__in=['resolved', 'closed']),
                    ),
                    Decimal('0'),
                ),
            )
        }

        ticket_ids_map = {}
        for ticket_id, room_id in ticket_qs.values_list('id', 'room_id'):
            ticket_ids_map.setdefault(room_id, []).append(ticket_id)

        alerts_qs = ProactiveMaintenanceAlert.objects.filter(
            room_id__in=room_ids,
            is_addressed=False,
        ).order_by('-created_at')
        alerts_map = {}
        for alert in alerts_qs:
            alerts_map.setdefault(alert.room_id, []).append(
                {
                    'id': alert.id,
                    'reason': alert.reason,
                    'createdAt': alert.created_at,
                }
            )

        companies = {}
        summary = self._empty_room_summary()

        for room in accessible_rooms:
            stats = aggregates.get(
                room.id,
                {
                    'total': 0,
                    'open_count': 0,
                    'in_progress_count': 0,
                    'resolved_count': 0,
                    'overdue_count': 0,
                    'critical_priority_count': 0,
                    'planned_budget': Decimal('0'),
                    'invested_budget': Decimal('0'),
                },
            )

            alerts = alerts_map.get(room.id, [])
            status = self._evaluate_room_status(stats, bool(alerts))

            company = room.resort.company if room.resort else None
            company_key = company.id if company else None
            if company_key not in companies:
                companies[company_key] = {
                    'id': company.id if company else None,
                    'name': company.name if company else 'Strutture senza società',
                    'resorts': {},
                }

            resort_entry = companies[company_key]['resorts'].setdefault(
                room.resort_id,
                {
                    'id': room.resort_id,
                    'name': room.resort.name,
                    'rooms': [],
                    'stats': self._empty_room_summary(),
                },
            )

            room_payload = {
                'id': room.id,
                'name': room.name,
                'status': status,
                'ticketIds': ticket_ids_map.get(room.id, []),
                'openTickets': stats['open_count'],
                'resolvedTickets': stats['resolved_count'],
                'plannedBudget': str(stats['planned_budget']),
                'investedBudget': str(stats['invested_budget']),
                'alerts': alerts,
            }

            resort_entry['rooms'].append(room_payload)
            self._accumulate_summary(resort_entry['stats'], status, stats, len(alerts))
            self._accumulate_summary(summary, status, stats, len(alerts))

        response_payload = {
            'companies': [
                {
                    'id': company_data['id'],
                    'name': company_data['name'],
                    'resorts': [
                        {
                            'id': resort_data['id'],
                            'name': resort_data['name'],
                            'rooms': sorted(resort_data['rooms'], key=lambda r: r['name']),
                            'stats': resort_data['stats'],
                        }
                        for resort_data in company_data['resorts'].values()
                    ],
                }
                for company_data in sorted(
                    companies.values(),
                    key=lambda item: item['name'].lower() if item['name'] else '',
                )
            ],
            'summary': summary,
        }

        for company in response_payload['companies']:
            company['resorts'].sort(key=lambda item: item['name'])

        return Response(response_payload)

    def _calendar_permission_map(self, user):
        if user is None:
            return {k: False for k in ['canCreateTickets', 'canAssignTickets', 'canAcknowledgeDeadline', 'canRescheduleDeadline', 'canClaimTickets']}
        if not hasattr(user, 'is_superuser') and hasattr(user, 'user'):
            user = user.user
        privileged_roles = {
            User.OWNER,
            User.MAINTENANCE_MANAGER,
            User.HEAD_MAINTAINER,
            User.SUPERADMIN,
        }

        can_manage_assignments = user.is_superuser or user.role in privileged_roles
        can_acknowledge_deadline = user.is_superuser or user.role in privileged_roles or user.role == User.MAINTAINER
        can_reschedule = TicketUpdateForm._user_can_freely_edit_deadline(user)
        can_create = bool(
            user
            and (
                user.is_superuser
                or user.has_maintenance_access
                or user.role in {
                    User.MAINTAINER,
                    User.HEAD_MAINTAINER,
                    User.MAINTENANCE_MANAGER,
                    User.OWNER,
                    User.SUPERADMIN,
                }
            )
        )

        return {
            'canCreateTickets': can_create,
            'canAssignTickets': can_manage_assignments,
            'canAcknowledgeDeadline': can_acknowledge_deadline,
            'canRescheduleDeadline': can_reschedule,
            'canClaimTickets': self._user_can_claim_any(user),
        }

    def _serialize_company_scope(self, resorts_qs):
        companies_map = {}
        for resort in resorts_qs.select_related('company'):
            if not resort.company:
                continue
            if resort.company_id not in companies_map:
                companies_map[resort.company_id] = {
                    'id': resort.company_id,
                    'name': resort.company.name,
                    'resorts': [],
                }
            companies_map[resort.company_id]['resorts'].append({'id': resort.id, 'name': resort.name})
        return list(companies_map.values())

    def _validate_calendar_filters(self, request, accessible_resorts):
        params = request.query_params
        filters = {}

        resort_id = params.get('resort')
        if resort_id:
            try:
                resort_id_int = int(resort_id)
            except (TypeError, ValueError):
                raise PermissionDenied('Filtro struttura non valido.')
            if not accessible_resorts.filter(pk=resort_id_int).exists():
                raise PermissionDenied('Non hai accesso alla struttura selezionata.')
            filters['resort_id'] = resort_id_int

        company_id = params.get('company')
        if company_id:
            try:
                company_id_int = int(company_id)
            except (TypeError, ValueError):
                raise PermissionDenied('Filtro società non valido.')
            allowed_company_ids = list(filter(None, accessible_resorts.values_list('company_id', flat=True).distinct()))
            if company_id_int not in allowed_company_ids:
                raise PermissionDenied('Non hai accesso alla società selezionata.')
            filters['resort__company_id'] = company_id_int

        assigned_to = params.get('assigned_to')
        if assigned_to:
            try:
                assigned_to_int = int(assigned_to)
            except (TypeError, ValueError):
                raise PermissionDenied('Filtro manutentore non valido.')
            allowed_maintainers = list(User.objects.filter(
                resort__in=accessible_resorts,
                role=User.MAINTAINER,
            ).values_list('id', flat=True))
            if assigned_to_int not in allowed_maintainers:
                raise PermissionDenied('Non hai accesso al manutentore selezionato.')
            filters['assigned_to_id'] = assigned_to_int

        status_filter = params.get('status')
        if status_filter:
            filters['status'] = status_filter

        priority_filter = params.get('priority')
        if priority_filter:
            filters['priority'] = priority_filter

        room_id = params.get('room')
        if room_id:
            try:
                room_id_int = int(room_id)
            except (TypeError, ValueError):
                raise PermissionDenied('Filtro camera non valido.')
            accessible_room_ids = list(self._accessible_rooms(request.user).values_list('id', flat=True))
            if room_id_int not in accessible_room_ids:
                raise PermissionDenied('Non hai accesso alla camera selezionata.')
            filters['room_id'] = room_id_int

        return filters

    @action(detail=False, methods=['get'], url_path='calendar')
    def calendar(self, request):
        user = request.user
        queryset = self.get_queryset()
        accessible_resorts = self._accessible_resorts(user)

        filters = self._validate_calendar_filters(request, accessible_resorts)
        if filters:
            queryset = queryset.filter(**filters)

        events = []
        permission_map = self._calendar_permission_map(user)
        for ticket in queryset.order_by('due_date', 'priority').select_related('resort__company', 'room', 'assigned_to'):
            start = ticket.due_date or ticket.created_at
            end = start + timedelta(minutes=30)
            resort_payload = None
            if ticket.resort:
                resort_payload = {
                    'id': ticket.resort.id,
                    'name': ticket.resort.name,
                    'company': {
                        'id': ticket.resort.company.id if ticket.resort.company else None,
                        'name': ticket.resort.company.name if ticket.resort.company else None,
                    } if ticket.resort.company else None,
                }

            events.append({
                'id': ticket.id,
                'title': f"#{ticket.id} • {ticket.title}",
                'start': timezone.localtime(start),
                'end': timezone.localtime(end),
                'allDay': False,
                'status': ticket.status,
                'priority': ticket.priority,
                'dueDate': ticket.due_date,
                'acknowledged': bool(ticket.acknowledged_due_date),
                'resort': resort_payload,
                'room': {'id': ticket.room.id, 'name': ticket.room.name} if ticket.room else None,
                'assignedTo': {
                    'id': ticket.assigned_to.id,
                    'name': ticket.assigned_to.get_full_name() or ticket.assigned_to.username,
                } if ticket.assigned_to else None,
                'permissions': {
                    'canAcknowledge': permission_map['canAcknowledgeDeadline'],
                    'canAssign': permission_map['canAssignTickets'],
                    'canReschedule': permission_map['canRescheduleDeadline'],
                },
            })

        metadata = {
            'filters': {
                'resorts': [
                    {'id': resort.id, 'name': resort.name}
                    for resort in accessible_resorts.order_by('name')
                ],
                'maintainers': [
                    {'id': maint.id, 'name': maint.get_full_name() or maint.username}
                    for maint in User.objects.filter(
                        resort__in=accessible_resorts,
                        role=User.MAINTAINER,
                    ).order_by('first_name', 'last_name')
                ],
                'statuses': [{'value': value, 'label': label} for value, label in Ticket.STATUS_CHOICES],
                'priorities': [{'value': value, 'label': label} for value, label in Ticket.PRIORITY_CHOICES],
            },
            'scope': {
                'companies': self._serialize_company_scope(accessible_resorts),
                'resorts': [
                    {'id': resort.id, 'name': resort.name, 'company': resort.company_id}
                    for resort in accessible_resorts.order_by('name')
                ],
            },
            'permissions': permission_map,
        }

        return Response({'events': events, 'metadata': metadata})

    @action(detail=False, methods=['get'], url_path='rooms/(?P<room_id>[^/.]+)/detail')
    def room_detail(self, request, room_id=None):
        user = request.user
        try:
            room = self._accessible_rooms(user).get(pk=room_id)
        except Room.DoesNotExist:
            raise PermissionDenied('Non hai accesso a questa camera.')

        tickets_qs = Ticket.objects.filter(room=room).select_related('assigned_to', 'created_by')
        now = timezone.now()

        open_statuses = ['open', 'in_progress']
        resolved_statuses = ['resolved', 'closed']

        stats = {
            'open': tickets_qs.filter(status__in=open_statuses).count(),
            'in_progress': tickets_qs.filter(status='in_progress').count(),
            'resolved': tickets_qs.filter(status__in=resolved_statuses).count(),
            'overdue': tickets_qs.filter(status__in=open_statuses, due_date__lt=now).count(),
            'planned_budget': tickets_qs.filter(status__in=open_statuses).aggregate(
                total=Coalesce(Sum('estimated_cost'), Decimal('0')
                ),
            )['total'],
            'invested_budget': tickets_qs.filter(status__in=resolved_statuses).aggregate(
                total=Coalesce(Sum('actual_cost'), Decimal('0')),
            )['total'],
        }

        open_tickets = [
            {
                'id': ticket.id,
                'title': ticket.title,
                'status': ticket.status,
                'priority': ticket.priority,
                'dueDate': ticket.due_date,
                'estimatedCost': ticket.estimated_cost,
                'assignedTo': ticket.assigned_to.get_full_name() if ticket.assigned_to else None,
            }
            for ticket in tickets_qs.filter(status__in=open_statuses).order_by('due_date', '-priority')
        ]

        resolved_tickets = [
            {
                'id': ticket.id,
                'title': ticket.title,
                'status': ticket.status,
                'priority': ticket.priority,
                'closedAt': ticket.updated_at,
                'actualCost': ticket.actual_cost,
            }
            for ticket in tickets_qs.filter(status__in=resolved_statuses).order_by('-updated_at')
        ]

        alerts = [
            {
                'id': alert.id,
                'reason': alert.reason,
                'createdAt': alert.created_at,
            }
            for alert in ProactiveMaintenanceAlert.objects.filter(room=room).order_by('-created_at')
        ]

        status = self._evaluate_room_status(
            {
                'open_count': stats['open'],
                'overdue_count': stats['overdue'],
                'critical_priority_count': tickets_qs.filter(
                    status__in=open_statuses,
                    priority__in=[Ticket.PRIORITY_HIGH, Ticket.PRIORITY_URGENT],
                ).count(),
            },
            bool(alerts),
        )

        detail_payload = {
            'room': {
                'id': room.id,
                'name': room.name,
                'status': status,
                'resort': {
                    'id': room.resort.id,
                    'name': room.resort.name,
                },
                'company': (
                    {
                        'id': room.resort.company.id,
                        'name': room.resort.company.name,
                    }
                    if room.resort and room.resort.company
                    else None
                ),
            },
            'stats': {
                'openTickets': stats['open'],
                'inProgressTickets': stats['in_progress'],
                'resolvedTickets': stats['resolved'],
                'overdueTickets': stats['overdue'],
                'plannedBudget': str(stats['planned_budget']),
                'investedBudget': str(stats['invested_budget']),
            },
            'tickets': {
                'open': open_tickets,
                'resolved': resolved_tickets,
            },
            'alerts': alerts,
            'ticketIds': list(tickets_qs.values_list('id', flat=True)),
        }

        return Response(detail_payload)

    def _evaluate_room_status(self, stats, has_alerts):
        if stats.get('critical_priority_count', 0) or stats.get('overdue_count', 0) or has_alerts:
            return self.ROOM_CRITICAL
        if stats.get('open_count', 0):
            return self.ROOM_WARNING
        return self.ROOM_OK

    def _empty_room_summary(self):
        return {
            'totalRooms': 0,
            'roomsOk': 0,
            'roomsWarning': 0,
            'roomsCritical': 0,
            'openTickets': 0,
            'resolvedTickets': 0,
            'alerts': 0,
            'plannedBudget': '0',
            'investedBudget': '0',
        }

    def _accumulate_summary(self, accumulator, status, stats, alert_count):
        accumulator['totalRooms'] += 1
        if status == self.ROOM_OK:
            accumulator['roomsOk'] += 1
        elif status == self.ROOM_WARNING:
            accumulator['roomsWarning'] += 1
        else:
            accumulator['roomsCritical'] += 1

        accumulator['openTickets'] += stats.get('open_count', 0)
        accumulator['resolvedTickets'] += stats.get('resolved_count', 0)
        accumulator['alerts'] += alert_count

        planned = Decimal(accumulator['plannedBudget']) + stats.get('planned_budget', Decimal('0'))
        invested = Decimal(accumulator['investedBudget']) + stats.get('invested_budget', Decimal('0'))
        accumulator['plannedBudget'] = str(planned)
        accumulator['investedBudget'] = str(invested)


    @action(detail=False, methods=['get'], url_path='metadata')
    def metadata(self, request):
        user = request.user

        resorts = self._accessible_resorts(user)

        resort_data = [
            {'id': resort.id, 'name': resort.name}
            for resort in resorts.order_by('name')
        ]

        rooms = Room.objects.filter(resort__in=resorts).order_by('resort__name', 'name')
        room_data = [
            {'id': room.id, 'name': room.name, 'resort': room.resort_id}
            for room in rooms
        ]

        maintainers = User.objects.filter(
            resort__in=resorts,
            role=User.MAINTAINER,
        ).order_by('first_name', 'last_name')

        maintainer_data = [
            {'id': maint.id, 'name': maint.get_full_name() or maint.username, 'resort': maint.resort_id}
            for maint in maintainers
        ]

        permission_map = self._calendar_permission_map(user)

        return Response({
            'resorts': resort_data,
            'rooms': room_data,
            'maintainers': maintainer_data,
            'statuses': [{'value': value, 'label': label} for value, label in Ticket.STATUS_CHOICES],
            'priorities': [{'value': value, 'label': label} for value, label in Ticket.PRIORITY_CHOICES],
            'deadlinePrivileges': TicketUpdateForm._user_can_freely_edit_deadline(user),
            'canClaimTickets': self._user_can_claim_any(user),
            'receivesUnassignedAlerts': getattr(user, 'receives_unassigned_ticket_alerts', True),
            'currentUser': {
                'id': user.id,
                'role': user.role,
                'isSuperuser': user.is_superuser,
                'company': user.company_id,
                'resort': user.resort_id,
                'fullName': user.get_full_name() or user.username,
            },
            'permissionMap': permission_map,
        })

    @action(detail=False, methods=['post'], url_path='preferences/unassigned-alerts')
    def update_unassigned_alerts_preference(self, request):
        enabled = request.data.get('enabled')
        if isinstance(enabled, str):
            enabled = enabled.lower() in ['true', '1', 'yes', 'on']
        elif isinstance(enabled, (int, float)):
            enabled = bool(enabled)
        elif isinstance(enabled, bool):
            enabled = enabled
        else:
            return Response({'detail': "Valore non valido."}, status=status.HTTP_400_BAD_REQUEST)

        request.user.receives_unassigned_ticket_alerts = enabled
        request.user.save(update_fields=['receives_unassigned_ticket_alerts'])

        return Response({'receivesUnassignedAlerts': request.user.receives_unassigned_ticket_alerts})

    @action(detail=False, methods=['get'], url_path='insights')
    def insights(self, request):
        qs = self.get_queryset()
        now = timezone.now()
        horizon = now + timezone.timedelta(hours=48)

        unassigned = qs.filter(assigned_to__isnull=True, status__in=['open', 'in_progress'])
        total_unassigned = unassigned.count()
        overdue_unassigned = unassigned.filter(due_date__lt=now, due_date__isnull=False).count()
        due_soon_unassigned = unassigned.filter(due_date__gt=now, due_date__lte=horizon).count()
        without_deadline = unassigned.filter(due_date__isnull=True).count()

        durations = []
        for entry in qs.values_list('created_at', 'first_claimed_at'):
            created_at, first_claimed_at = entry
            if created_at and first_claimed_at:
                delta = first_claimed_at - created_at
                durations.append(delta.total_seconds())

        average_claim_hours = None
        if durations:
            average_claim_hours = round(sum(durations) / len(durations) / 3600, 2)

        percent_overdue = 0
        if total_unassigned:
            percent_overdue = round((overdue_unassigned / total_unassigned) * 100, 2)

        return Response({
            'unassigned': {
                'total': total_unassigned,
                'overdue': overdue_unassigned,
                'dueSoon': due_soon_unassigned,
                'withoutDeadline': without_deadline,
                'percentOverdue': percent_overdue,
            },
            'averages': {
                'claimHours': average_claim_hours,
            },
        })

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
