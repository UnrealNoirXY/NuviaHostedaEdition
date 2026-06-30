import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from accounts.models import User
from communications.models import Announcement
from inventory.models import InventoryItem
from purchase_orders.models import PurchaseOrder, Supplier
from reviews.models import Review, ReviewAnalysis
from tickets.models import Ticket

from .api import UserLayoutView
from .models import WidgetPreference
from .widget_config import WIDGET_REGISTRY, ROLE_WIDGET_MAP


@login_required
@require_POST
def save_layout(request):
    """Persist the Home Desk layout for the current user."""
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON.'}, status=400)

    layout_data = payload.get('layout')
    if layout_data is None:
        return JsonResponse({'status': 'error', 'message': 'Missing layout data.'}, status=400)

    WidgetPreference.objects.update_or_create(
        user=request.user,
        defaults={'layout': layout_data},
    )
    return JsonResponse({'status': 'success'})


@login_required
def calendar_events(request):
    """Return a minimal JSON feed of upcoming ticket deadlines for legacy clients."""
    tickets = Ticket.objects.exclude(status__in=['resolved', 'closed']).filter(due_date__isnull=False)
    if request.user.resort_id:
        tickets = tickets.filter(resort=request.user.resort)

    events = [
        {
            'title': f"Ticket #{ticket.id}: {ticket.title}",
            'start': ticket.due_date.isoformat(),
            'url': reverse('ticket_detail', args=[ticket.id]),
            'color': '#ff9f89',
        }
        for ticket in tickets.order_by('due_date')
    ]
    return JsonResponse(events, safe=False)


class HomeDeskView(LoginRequiredMixin, TemplateView):
    """
    Renders the main container for the React-based Home Desk application.
    The actual content and widgets are managed by the frontend.
    """
    template_name = 'desk/nuvia_os.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['page_title'] = 'Home Desk'

        context.update(self._build_base_context(user))
        context.update(self._get_role_specific_context(user))

        return context

    def _build_base_context(self, user):
        preference, _ = WidgetPreference.objects.get_or_create(user=user)
        layout_list, updated_layouts = self._resolve_layout(preference, user)

        if updated_layouts is not None:
            preference.layout = updated_layouts
            preference.save(update_fields=['layout'])

        role_key = 'superadmin' if user.is_superuser else user.role
        available_widget_keys = ROLE_WIDGET_MAP.get('all', []) + ROLE_WIDGET_MAP.get(role_key, [])
        available_widgets = [
            WIDGET_REGISTRY[key]
            for key in available_widget_keys
            if key in WIDGET_REGISTRY
        ]

        context = {
            'widget_layout': json.dumps(self._adapt_layout_items(layout_list)),
            'available_widgets': available_widgets,
            'recent_announcements': Announcement.objects.order_by('-created_at')[:3],
        }

        # Shared summaries
        context['ticket_overview'] = self._build_ticket_overview(user)
        context['recent_reviews'] = Review.objects.select_related('source').order_by('-review_date')[:5]
        context['system_status'] = {
            'api': 'online',
            'pwa': 'online',
        }

        return context

    def _resolve_layout(self, preference, user):
        stored_layout = preference.layout
        updated_layouts = None

        if isinstance(stored_layout, list):
            layout_list = stored_layout
            updated_layouts = {'lg': stored_layout}
        elif isinstance(stored_layout, dict):
            layout_list = stored_layout.get('lg', [])
        else:
            layout_list = []

        if not layout_list:
            default_layouts = UserLayoutView().generate_default_layouts(user)
            layout_list = default_layouts.get('lg', [])
            updated_layouts = default_layouts

        return layout_list, updated_layouts

    def _adapt_layout_items(self, layout_items):
        converted = []
        for item in layout_items:
            if not isinstance(item, dict):
                continue
            if 'i' in item:
                converted.append({
                    'id': item.get('id') or item.get('i'),
                    'x': item.get('x', 0),
                    'y': item.get('y', 0),
                    'w': item.get('w', 0),
                    'h': item.get('h', 0),
                })
            else:
                converted.append(item)
        return converted

    def _build_ticket_overview(self, user):
        queryset = Ticket.objects.all()
        if not user.is_superuser:
            if user.resort_id:
                queryset = queryset.filter(resort=user.resort)
            elif user.company_id:
                queryset = queryset.filter(resort__company=user.company)

        status_counts = {key: 0 for key, _ in Ticket.STATUS_CHOICES}
        for row in queryset.values('status').annotate(total=Count('id')):
            status_counts[row['status']] = row['total']

        return {
            'open': status_counts.get('open', 0),
            'in_progress': status_counts.get('in_progress', 0),
            'resolved': status_counts.get('resolved', 0),
            'closed': status_counts.get('closed', 0),
        }

    def _build_director_kpis(self, user):
        if not user.resort_id and not user.company_id:
            return {'open_tickets': 0, 'avg_rating_month': 0, 'avg_sentiment': 0}

        resorts = []
        if user.resort_id:
            resorts = [user.resort]
        elif user.company_id:
            resorts = list(user.company.resorts.all())

        tickets = Ticket.objects.filter(resort__in=resorts, status='open')
        open_tickets = tickets.count()

        since = timezone.now() - timedelta(days=30)
        review_queryset = Review.objects.filter(resort__in=resorts, review_date__gte=since)
        avg_rating = review_queryset.aggregate(avg=Avg('rating'))['avg'] or 0
        sentiment_queryset = ReviewAnalysis.objects.filter(review__in=review_queryset)
        avg_sentiment = sentiment_queryset.aggregate(avg=Avg('sentiment_score'))['avg'] or 0

        return {
            'open_tickets': open_tickets,
            'avg_rating_month': round(avg_rating, 2) if avg_rating else 0,
            'avg_sentiment': round(avg_sentiment, 2) if avg_sentiment else 0,
        }

    def _build_review_chart_data(self, user):
        if not user.resort_id:
            return {'labels': [], 'data': []}

        reviews = Review.objects.filter(resort=user.resort).order_by('review_date')[:30]
        labels = [review.review_date.strftime('%d/%m') for review in reviews]
        data = [review.rating for review in reviews]
        return {'labels': labels, 'data': data}

    def _get_role_specific_context(self, user):
        context = {}

        if user.role == User.MAINTAINER:
            context['maintainer_tickets'] = Ticket.objects.filter(
                assigned_to=user,
                status__in=['open', 'in_progress'],
            ).order_by('due_date')

        if user.role == User.DIRECTOR:
            context['director_kpis'] = self._build_director_kpis(user)
            context['review_chart_data'] = json.dumps(self._build_review_chart_data(user))

        if user.role == User.OWNER:
            context['financial_performance'] = {
                'approved_orders': PurchaseOrder.objects.filter(status='approved').count(),
                'pending_orders': PurchaseOrder.objects.filter(status='submitted').count(),
            }
            context['online_reputation'] = {
                'avg_rating': round(Review.objects.aggregate(avg=Avg('rating'))['avg'] or 0, 2),
                'reviews_last_30_days': Review.objects.filter(
                    review_date__gte=timezone.now() - timedelta(days=30)
                ).count(),
            }
            context['competitor_analysis'] = {'status': 'coming_soon'}
            context['director_kpis'] = self._build_director_kpis(user)
            context['review_chart_data'] = json.dumps(self._build_review_chart_data(user))

        if user.role == User.SUPERADMIN or user.is_superuser:
            UserModel = get_user_model()
            context['active_users'] = UserModel.objects.filter(
                last_seen__gte=timezone.now() - timedelta(hours=24)
            ).count()

        if user.role == User.HEAD_MAINTAINER:
            context['unassigned_tickets'] = Ticket.objects.filter(
                assigned_to__isnull=True,
                resort=user.resort,
                status__in=['open', 'in_progress'],
            )
            context['urgent_tickets'] = Ticket.objects.filter(
                resort=user.resort,
                status__in=['open', 'in_progress'],
                priority__in=['high', 'urgent'],
            )
            context['critical_stock_items'] = InventoryItem.objects.filter(resort=user.resort, current_stock__lte=5)
            context['team_performance'] = {
                'resolved_this_week': Ticket.objects.filter(
                    resort=user.resort,
                    status='resolved',
                    updated_at__gte=timezone.now() - timedelta(days=7),
                ).count()
            }

        if user.role == User.RECEPTIONIST:
            context['quick_ticket_form'] = True
            context['resort_recent_tickets'] = Ticket.objects.filter(resort=user.resort).order_by('-created_at')[:5]
            context['guest_announcements'] = Announcement.objects.order_by('-created_at')[:5]
            context['useful_documents'] = []

        if user.role == User.HOUSEKEEPING:
            rooms = user.resort.rooms.all() if user.resort else []
            context['rooms_with_status'] = [{'room': room.name, 'status': 'unknown'} for room in rooms]
            context['quick_report_form'] = True

        if user.role == User.ADMINISTRATIVE:
            context['approved_pos'] = PurchaseOrder.objects.filter(status='approved')
            context['supplier_list'] = Supplier.objects.all()
            context['useful_documents'] = []

        if user.role == User.ECONOMO:
            context['critical_stock_items'] = InventoryItem.objects.filter(current_stock__lte=5)
            context['supplier_list'] = Supplier.objects.all()

        if user.role == User.CAPO_ECONOMO:
            context['po_approvals'] = PurchaseOrder.objects.filter(status='submitted')
            context['critical_stock_items'] = InventoryItem.objects.filter(current_stock__lte=5)
            context['supplier_list'] = Supplier.objects.all()

        if user.role == User.IT_TECHNICIAN:
            context['it_tickets'] = Ticket.objects.filter(assigned_to=user)
            context['active_chats'] = []
            context['system_status'] = context.get('system_status', {'api': 'online', 'pwa': 'online'})

        return context
