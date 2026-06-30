# Standard Library Imports
import traceback
from datetime import timedelta

# Django Imports
from django.conf import settings
from django.db.models import Avg, Case, Count, DurationField, ExpressionWrapper, F, IntegerField, Q, Sum, When
from django.urls import reverse
from django.utils import timezone

# Third-Party Imports
from rest_framework import serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

# Local Application Imports
from accounts.models import User
from communications.models import Announcement
from notifications.models import Notification
from communications.tasks import send_event_invitation_email
from reviews.models import Review
from tickets.models import Ticket
from bookings.models import Booking
from resort.models import Resort, Room
from inventory.models import InventoryItem, StockRecord
from .models import Event, EventInvitation, WidgetPreference
from .widget_config import WIDGET_REGISTRY, APP_REGISTRY, ROLE_WIDGET_MAP, ROLE_APP_MAP


# --- HELPERS ---

def get_ticket_queryset_for_user(user):
    queryset = Ticket.objects.select_related('resort').all()
    if user.is_superuser or user.role in {User.SUPERADMIN, User.CORPORATE}:
        return queryset
    if user.resort_id:
        return queryset.filter(resort=user.resort)
    if user.company_id:
        return queryset.filter(resort__company=user.company)
    return queryset.none()


# --- SERIALIZERS ---

class WidgetPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WidgetPreference
        fields = ['layout', 'open_windows', 'pinned_icons', 'workspaces', 'active_workspace_id']

class EventSerializer(serializers.ModelSerializer):
    attendee_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Event
        fields = ['id', 'title', 'start', 'end', 'user', 'event_type', 'attendee_ids']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'avatar']

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ['id', 'title', 'status', 'priority', 'created_at', 'due_date']

class AnnouncementSerializer(serializers.ModelSerializer):
    content = serializers.CharField(source='body', read_only=True)
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'content', 'created_at']

class ReviewSerializer(serializers.ModelSerializer):
    source_name = serializers.CharField(source='source.name', read_only=True)
    sentiment_label = serializers.CharField(source='analysis.sentiment_label', read_only=True, default='neutral')
    class Meta:
        model = Review
        fields = ['id', 'title', 'rating', 'author', 'review_date', 'source_name', 'text', 'original_url', 'sentiment_label']


# --- API VIEWS ---

class AnnouncementsWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        announcements = Announcement.objects.order_by('-created_at')[:5]
        serializer = AnnouncementSerializer(announcements, many=True)
        return Response(serializer.data)

class CalendarWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        user = request.user
        user_events = Event.objects.filter(attendees=user).prefetch_related('invitations')
        events_data = []
        for event in user_events:
            invitation = next((inv for inv in event.invitations.all() if inv.invitee_id == user.id), None)
            invitation_status = invitation.status if invitation else None
            events_data.append({
                'title': event.title,
                'start': event.start.isoformat(),
                'end': event.end.isoformat(),
                'event_type': event.event_type,
                'invitation_status': invitation_status,
            })
        assigned_tickets = Ticket.objects.filter(
            assigned_to=user,
            due_date__isnull=False
        ).exclude(status__in=['resolved', 'closed'])
        for ticket in assigned_tickets:
            events_data.append({
                'title': f"Scadenza Ticket #{ticket.id}",
                'start': ticket.due_date.isoformat(),
                'end': ticket.due_date.isoformat(),
                'url': reverse('ticket_detail', args=[ticket.id]),
                'event_type': 'ticket_due_date',
            })
        return Response(events_data)

class EventViewSet(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, *args, **kwargs):
        serializer = EventSerializer(data=request.data)
        if serializer.is_valid():
            attendee_ids = serializer.validated_data.pop('attendee_ids', [])
            event = serializer.save(user=request.user)
            EventInvitation.objects.create(event=event, invitee=request.user, status='accepted')
            for user_id in attendee_ids:
                if user_id != request.user.id:
                    try:
                        invitee = User.objects.get(id=user_id)
                        invitation, created = EventInvitation.objects.get_or_create(event=event, invitee=invitee)
                        if created:
                            send_event_invitation_email.delay(invitation.id)
                    except User.DoesNotExist:
                        continue
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SearchInviteesView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        user = request.user
        queryset = User.objects.none()
        if user.is_superuser or user.role == User.SUPERADMIN:
            queryset = User.objects.all()
        elif user.role == User.OWNER and user.company:
            queryset = User.objects.filter(company=user.company)
        elif user.role == User.DIRECTOR and user.resort:
            queryset = User.objects.filter(resort=user.resort)
        elif user.role == User.HEAD_MAINTAINER and user.resort:
            queryset = User.objects.filter(resort=user.resort, role=User.MAINTAINER)
        search_term = request.query_params.get('search', None)
        if search_term:
            queryset = queryset.filter(
                Q(username__icontains=search_term) |
                Q(first_name__icontains=search_term) |
                Q(last_name__icontains=search_term)
            )
        queryset = queryset.exclude(id=user.id).order_by('username')
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)

class NotificationCenterDataView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        user = request.user
        notifications = []
        in_app_candidates = Notification.objects.targeted_to(user).order_by('-is_pinned', '-created_at')[:10]
        for notif in in_app_candidates:
            if not notif.matches_user(user):
                continue
            notifications.append({
                'id': f'notification-{notif.id}',
                'type': 'in_app',
                'title': notif.display_title,
                'content': notif.body or notif.message,
                'date': notif.created_at,
                'icon': notif.icon or 'fa-bell',
                'cta_url': notif.link,
                'cta_label': notif.cta_label,
                'category': notif.category,
                'priority': notif.priority,
                'metadata': notif.metadata,
                'is_read': notif.is_read,
            })
        announcements = Announcement.objects.exclude(read_by=user).order_by('-created_at')[:5]
        for ann in announcements:
            notifications.append({
                'id': f'announcement-{ann.id}',
                'type': 'announcement',
                'title': ann.title,
                'content': ann.body, # Corrected from ann.content
                'date': ann.created_at,
            })
        invitations = EventInvitation.objects.filter(
            invitee=user,
            status='pending'
        ).select_related('event', 'event__user').order_by('-event__start')
        for inv in invitations:
            notifications.append({
                'id': f'invitation-{inv.id}',
                'type': 'event_invitation',
                'title': f"Invito a: {inv.event.title}",
                'content': f"Da: {inv.event.user.get_full_name() or inv.event.user.username}",
                'date': inv.event.start,
                'invitation_id': inv.id,
            })
        notifications.sort(key=lambda x: x['date'], reverse=True)
        return Response(notifications)

class RecentActivityDataView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        user = request.user
        activities = []
        created_tickets = Ticket.objects.filter(created_by=user).order_by('-created_at')[:5]
        for ticket in created_tickets:
            activities.append({
                'id': f'ticket-create-{ticket.id}',
                'type': 'ticket_created',
                'description': f'Hai creato il ticket #{ticket.id}: "{ticket.title}"',
                'date': ticket.created_at,
                'url': reverse('ticket_detail', args=[ticket.id]),
            })
        if user.role in [User.MAINTAINER, User.HEAD_MAINTAINER, User.IT_TECHNICIAN]:
            closed_tickets = Ticket.objects.filter(assigned_to=user, status__in=['resolved', 'closed']).order_by('-updated_at')[:5]
            for ticket in closed_tickets:
                activities.append({
                    'id': f'ticket-close-{ticket.id}',
                    'type': 'ticket_closed',
                    'description': f'Hai risolto il ticket #{ticket.id}: "{ticket.title}"',
                    'date': ticket.updated_at,
                    'url': reverse('ticket_detail', args=[ticket.id]),
                })
        activities.sort(key=lambda x: x['date'], reverse=True)
        recent_activities = activities[:10]
        return Response(recent_activities)

class UpdateInvitationStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, invitation_id, *args, **kwargs):
        invitation = get_object_or_404(EventInvitation, id=invitation_id)
        if request.user != invitation.invitee:
            return Response(
                {'error': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        new_status = request.data.get('status')
        if new_status not in ['accepted', 'declined']:
            return Response(
                {'error': 'Invalid status provided.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        invitation.status = new_status
        invitation.save()
        return Response({'status': 'success', 'new_status': new_status}, status=status.HTTP_200_OK)

class RecentReviewsWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        user = request.user
        reviews_queryset = Review.objects.select_related('source', 'analysis')

        if not (user.is_superuser or user.role in {User.SUPERADMIN, User.CORPORATE}):
            if user.resort_id:
                reviews_queryset = reviews_queryset.filter(resort=user.resort)
            elif user.company_id:
                reviews_queryset = reviews_queryset.filter(resort__company=user.company)

        recent_reviews = reviews_queryset.order_by('-review_date')[:5]
        serializer = ReviewSerializer(recent_reviews, many=True)
        return Response(serializer.data)

class MaintainerTicketsWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        maintainer_tickets = Ticket.objects.filter(
            assigned_to=request.user,
            status__in=['open', 'in_progress']
        ).order_by('-priority', 'created_at')
        serializer = TicketSerializer(maintainer_tickets, many=True)
        return Response(serializer.data)

class TicketOverviewWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        tickets = get_ticket_queryset_for_user(user)
        now = timezone.now()

        status_counts = {key: 0 for key, _ in Ticket.STATUS_CHOICES}
        for row in tickets.values('status').annotate(total=Count('id')):
            status_counts[row['status']] = row['total']

        priority_counts = {key: 0 for key, _ in Ticket.PRIORITY_CHOICES}
        for row in tickets.values('priority').annotate(total=Count('id')):
            priority_counts[row['priority']] = row['total']

        active_statuses = ['open', 'in_progress']
        active_count = sum(status_counts.get(status, 0) for status in active_statuses)
        overdue_count = tickets.filter(due_date__lt=now, status__in=active_statuses).count()
        resolved_last_week = tickets.filter(
            status__in=['resolved', 'closed'],
            updated_at__gte=now - timedelta(days=7)
        ).count()

        avg_duration = tickets.filter(status__in=['resolved', 'closed']).annotate(
            duration=ExpressionWrapper(F('updated_at') - F('created_at'), output_field=DurationField()),
        ).aggregate(avg=Avg('duration'))['avg']

        average_resolution_hours = None
        if avg_duration:
            average_resolution_hours = round(avg_duration.total_seconds() / 3600, 1)

        return Response({
            'status_counts': status_counts,
            'priority_counts': priority_counts,
            'active_count': active_count,
            'overdue_count': overdue_count,
            'resolved_last_week': resolved_last_week,
            'average_resolution_hours': average_resolution_hours,
        })


class UrgentTicketsWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        now = timezone.now()
        tickets = get_ticket_queryset_for_user(request.user).filter(status__in=['open', 'in_progress'])

        urgent_tickets = tickets.filter(
            Q(priority__in=[Ticket.PRIORITY_HIGH, Ticket.PRIORITY_URGENT]) | Q(due_date__lt=now)
        ).annotate(
            priority_rank=Case(
                When(priority=Ticket.PRIORITY_URGENT, then=0),
                When(priority=Ticket.PRIORITY_HIGH, then=1),
                When(priority=Ticket.PRIORITY_MEDIUM, then=2),
                default=3,
                output_field=IntegerField(),
            )
        ).order_by('priority_rank', 'due_date', 'created_at')[:10]

        payload = []
        for ticket in urgent_tickets:
            age_hours = int((now - ticket.created_at).total_seconds() // 3600)
            payload.append({
                'id': ticket.id,
                'title': ticket.title,
                'priority': ticket.priority,
                'status': ticket.status,
                'due_date': ticket.due_date.isoformat() if ticket.due_date else None,
                'is_overdue': bool(ticket.due_date and ticket.due_date < now),
                'age_hours': age_hours,
            })

        return Response(payload)


class MaintainerQuickAccessWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        today = timezone.localdate()

        assigned_to_me = Ticket.objects.filter(
            assigned_to=user,
            status__in=['open', 'in_progress'],
        ).order_by('due_date', 'created_at')

        awaiting_assignment = get_ticket_queryset_for_user(user).filter(
            assigned_to__isnull=True,
            status__in=['open', 'in_progress'],
        ).count()

        due_today = assigned_to_me.filter(due_date__date=today).count()
        next_due_ticket = assigned_to_me.filter(due_date__isnull=False).first()

        response_data = {
            'assigned_to_me': assigned_to_me.count(),
            'due_today': due_today,
            'awaiting_assignment': awaiting_assignment,
            'next_due': None,
            'actions': [
                {'label': 'Nuovo ticket', 'href': '/maintenance/ticket/nuovo/', 'icon': 'fa-plus'},
                {'label': 'Apri assistente', 'icon': 'fa-wand-magic-sparkles', 'target': 'open_assistant'},
                {'label': 'I miei ticket', 'href': '/tickets/', 'icon': 'fa-list-check'},
            ],
        }

        if next_due_ticket:
            response_data['next_due'] = {
                'id': next_due_ticket.id,
                'title': next_due_ticket.title,
                'due_date': next_due_ticket.due_date.isoformat() if next_due_ticket.due_date else None,
            }

        return Response(response_data)


class CriticalStockWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        try:
            threshold = int(request.query_params.get('threshold', 5))
        except (TypeError, ValueError):
            threshold = 5

        items = InventoryItem.objects.select_related('resort').all()

        if not (user.is_superuser or user.role in {User.SUPERADMIN, User.CORPORATE}):
            if user.resort_id:
                items = items.filter(resort=user.resort)
            elif user.company_id:
                items = items.filter(resort__company=user.company)
            else:
                items = items.none()

        lookback = timezone.now() - timedelta(days=30)
        critical_items = items.filter(current_stock__lte=threshold).order_by('current_stock', 'name')[:10]

        payload = []
        for item in critical_items:
            usage = item.stock_records.filter(
                timestamp__gte=lookback,
                change__lt=0,
            ).aggregate(total=Sum('change'))['total'] or 0

            monthly_usage = abs(int(usage))
            daily_usage = monthly_usage / 30 if monthly_usage else 0
            coverage_days = round(item.current_stock / daily_usage, 1) if daily_usage else None

            payload.append({
                'id': item.id,
                'name': item.name,
                'current_stock': item.current_stock,
                'resort_name': item.resort.name if item.resort else None,
                'monthly_usage': monthly_usage,
                'coverage_days': coverage_days,
            })

        return Response(payload)


class RoomStatusWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        rooms = Room.objects.all()
        if not (user.is_superuser or user.role in {User.SUPERADMIN, User.CORPORATE}):
            if user.resort_id:
                rooms = rooms.filter(resort=user.resort)
            elif user.company_id:
                rooms = rooms.filter(resort__company=user.company)
            else:
                rooms = rooms.none()

        # Simulazione stati camera (in attesa di modello dedicato)
        # In un sistema reale, avremmo un modello RoomStatus o campi su Room
        payload = []
        for room in rooms[:20]:
            payload.append({
                'id': room.id,
                'name': room.name,
                'status': 'clean' if room.id % 3 == 0 else 'dirty' if room.id % 3 == 1 else 'inspecting',
                'resort_name': room.resort.name
            })
        return Response(payload)

class DailyArrivalsWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        today = timezone.localdate()
        bookings = Booking.objects.filter(check_in_date=today)

        if not (user.is_superuser or user.role in {User.SUPERADMIN, User.CORPORATE}):
            if user.resort_id:
                bookings = bookings.filter(resort=user.resort)
            elif user.company_id:
                bookings = bookings.filter(resort__company=user.company)
            else:
                bookings = bookings.none()

        payload = []
        for booking in bookings.order_by('guest_name'):
            payload.append({
                'id': booking.id,
                'guest_name': booking.guest_name,
                'status': booking.status,
                'room_details': booking.room_details,
                'check_in_time': '14:00' # PMS placeholder
            })
        return Response(payload)

class FinancialPerformanceWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        from purchase_orders.models import PurchaseOrder, Budget
        user = request.user
        resorts = Resort.objects.all()
        if not (user.is_superuser or user.role in {User.SUPERADMIN, User.CORPORATE}):
            if user.resort_id:
                resorts = resorts.filter(id=user.resort_id)
            elif user.company_id:
                resorts = resorts.filter(company=user.company)
            else:
                resorts = resorts.none()

        orders = PurchaseOrder.objects.filter(resort__in=resorts, created_at__month=timezone.now().month)
        total_spent = sum(order.total_amount for order in orders if order.status in ['approved', 'completed'])

        # Budget mensile aggregato
        current_month = timezone.now().month
        current_year = timezone.now().year
        monthly_budget = Budget.objects.filter(resort__in=resorts, month=current_month, year=current_year).aggregate(Sum('amount'))['amount__sum'] or 0

        return Response({
            'total_spent': float(total_spent),
            'monthly_budget': float(monthly_budget),
            'pending_orders_count': orders.filter(status='submitted').count(),
            'approved_orders_count': orders.filter(status='approved').count(),
            'utilization_rate': round((float(total_spent) / float(monthly_budget)) * 100, 1) if monthly_budget > 0 else 0
        })

class DirectorKpisWidgetDataView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        resorts = Resort.objects.all()

        if user.is_superuser or user.role in {User.SUPERADMIN, User.CORPORATE}:
            pass
        elif user.resort_id:
            resorts = resorts.filter(id=user.resort_id)
        elif user.company_id:
            resorts = resorts.filter(company=user.company)
        else:
            resorts = resorts.none()

        bookings = Booking.objects.filter(resort__in=resorts)
        today = timezone.localdate()

        occupied_rooms = bookings.filter(
            check_in_date__lte=today,
            check_out_date__gt=today,
        ).count()

        total_rooms = Room.objects.filter(resort__in=resorts).count()
        occupancy_rate = round((occupied_rooms / total_rooms) * 100, 1) if total_rooms else 0

        upcoming_arrivals = bookings.filter(check_in_date=today).count()
        pending_checkins = bookings.filter(
            check_in_date=today,
            status=Booking.Status.PENDING,
        ).count()

        avg_stay_delta = bookings.aggregate(
            avg=Avg(ExpressionWrapper(
                F('check_out_date') - F('check_in_date'),
                output_field=DurationField(),
            ))
        )['avg']

        avg_stay_nights = 0
        if avg_stay_delta:
            avg_stay_nights = round(avg_stay_delta.total_seconds() / 86400, 1)

        review_queryset = Review.objects.filter(resort__in=resorts)
        avg_review_score = review_queryset.aggregate(avg=Avg('rating'))['avg']
        recent_reviews_count = review_queryset.filter(
            review_date__gte=timezone.now() - timedelta(days=30)
        ).count()
        last_review = review_queryset.order_by('-review_date').values('review_date').first()

        return Response({
            'occupancy_rate': occupancy_rate,
            'rooms_total': total_rooms,
            'rooms_occupied': occupied_rooms,
            'upcoming_arrivals': upcoming_arrivals,
            'pending_checkins': pending_checkins,
            'avg_stay_nights': avg_stay_nights,
            'avg_review_score': round(avg_review_score, 1) if avg_review_score is not None else None,
            'recent_reviews_count': recent_reviews_count,
            'last_review_date': last_review['review_date'].isoformat() if last_review else None,
        })


class SmartAlertsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        alerts = []

        # 1. Ticket Alert
        urgent_count = get_ticket_queryset_for_user(user).filter(
            status__in=['open', 'in_progress'],
            priority__in=[Ticket.PRIORITY_URGENT, Ticket.PRIORITY_HIGH]
        ).count()
        if urgent_count > 3:
            alerts.append({
                'id': 'maintenance-crisis',
                'level': 'critical',
                'title': 'Crisi Manutentiva',
                'message': f'Ci sono {urgent_count} ticket urgenti aperti. Focus richiesto.',
                'target_app': 'urgent-tickets-widget'
            })

        # 2. Reputation Alert
        negative_reviews = Review.objects.filter(rating__lte=2, review_date__gte=timezone.now() - timedelta(hours=24))
        if not (user.is_superuser or user.role in {User.SUPERADMIN, User.CORPORATE}):
            if user.resort_id:
                negative_reviews = negative_reviews.filter(resort=user.resort)

        if negative_reviews.exists():
            alerts.append({
                'id': 'reputation-alert',
                'level': 'warning',
                'title': 'Allerta Reputazione',
                'message': 'Ricevuta recensione negativa nelle ultime 24 ore.',
                'target_app': 'recent-reviews-widget'
            })

        return Response(alerts)

class UserLayoutView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        preference, created = WidgetPreference.objects.get_or_create(user=request.user)
        layouts = preference.layout
        open_windows = preference.open_windows
        pinned_icons = preference.pinned_icons
        workspaces = preference.workspaces
        active_workspace_id = preference.active_workspace_id

        should_regenerate = created or not layouts
        if isinstance(layouts, list):
            layouts = {'lg': layouts}
            preference.layout = layouts
            preference.save(update_fields=['layout'])
        elif not isinstance(layouts, dict):
            should_regenerate = True
        if request.user.is_superuser and not layouts.get('lg'):
            should_regenerate = True
        if should_regenerate:
            layouts = self.generate_default_layouts(request.user)
            preference.layout = layouts
            preference.save()
        user_role = request.user.role
        if request.user.is_superuser:
            user_role = 'superadmin'
        available_widget_keys = ROLE_WIDGET_MAP.get('all', []) + ROLE_WIDGET_MAP.get(user_role, [])
        available_widgets = [WIDGET_REGISTRY[key] for key in available_widget_keys if key in WIDGET_REGISTRY]

        available_app_keys = ROLE_APP_MAP.get('all', []) + ROLE_APP_MAP.get(user_role, [])
        available_apps = [APP_REGISTRY[key] for key in available_app_keys if key in APP_REGISTRY]

        return Response({
            'layouts': layouts,
            'open_windows': open_windows,
            'pinned_icons': pinned_icons,
            'workspaces': workspaces,
            'active_workspace_id': active_workspace_id,
            'available_widgets': available_widgets,
            'available_apps': available_apps
        })

    def post(self, request, *args, **kwargs):
        serializer = WidgetPreferenceSerializer(data=request.data)
        if serializer.is_valid():
            layouts_data = serializer.validated_data.get('layout')
            open_windows_data = serializer.validated_data.get('open_windows')
            pinned_icons_data = serializer.validated_data.get('pinned_icons')
            workspaces_data = serializer.validated_data.get('workspaces')
            active_workspace_id_data = serializer.validated_data.get('active_workspace_id')

            defaults = {}
            if layouts_data is not None:
                defaults['layout'] = layouts_data
            if open_windows_data is not None:
                defaults['open_windows'] = open_windows_data
            if pinned_icons_data is not None:
                defaults['pinned_icons'] = pinned_icons_data
            if workspaces_data is not None:
                defaults['workspaces'] = workspaces_data
            if active_workspace_id_data is not None:
                defaults['active_workspace_id'] = active_workspace_id_data

            WidgetPreference.objects.update_or_create(
                user=request.user,
                defaults=defaults
            )
            return Response({'status': 'success'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def generate_default_layouts(self, user):
        user_role = user.role
        if user.is_superuser:
            user_role = 'superadmin'
        widget_keys = ROLE_WIDGET_MAP.get('all', []) + ROLE_WIDGET_MAP.get(user_role, [])
        layouts = {}
        breakpoints = ['lg', 'md', 'sm', 'xs', 'xxs']
        cols = {'lg': 12, 'md': 10, 'sm': 6, 'xs': 4, 'xxs': 2}
        for bp in breakpoints:
            layout = []
            y_pos = 0
            x_pos = 0
            row_h = 0
            for key in widget_keys:
                if key in WIDGET_REGISTRY:
                    widget = WIDGET_REGISTRY[key]
                    widget_w = widget.get('w', 6)
                    widget_h = widget.get('h', 4)
                    if bp in ['sm', 'xs', 'xxs']:
                        layout.append({
                            "i": widget['id'], "x": 0, "y": y_pos,
                            "w": cols[bp], "h": widget_h
                        })
                        y_pos += widget_h
                    else:
                        if x_pos + widget_w > cols[bp]:
                            x_pos = 0
                            y_pos += row_h
                            row_h = 0
                        layout.append({
                            "i": widget['id'], "x": x_pos, "y": y_pos,
                            "w": widget_w, "h": widget_h
                        })
                        x_pos += widget_w
                        row_h = max(row_h, widget_h)
            layouts[bp] = layout
        return layouts
