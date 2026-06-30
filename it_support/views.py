import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from datetime import datetime, timezone
from .models import IT_Ticket, IT_TicketComment, ChatMessage
from .forms import IT_TicketForm, IT_TicketUpdateForm, IT_TicketCommentForm
from core.utils import themed_render
from accounts.models import User
from core.decorators import role_required, it_support_management_access_required
from .forms import IT_TicketForm, IT_TicketUpdateForm, IT_TicketCommentForm
from core.utils import themed_render
from accounts.models import User

@login_required
def it_ticket_create(request):
    if request.method == 'POST':
        form = IT_TicketForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            messages.success(request, 'Il tuo ticket di supporto IT è stato creato con successo.')
            return redirect('it_support:it_ticket_detail', pk=ticket.pk)
    else:
        form = IT_TicketForm(user=request.user)

    context = {
        'form': form,
        'anydesk_download_url': 'https://anydesk.com/it/downloads'
    }
    return themed_render(request, 'it_support/it_ticket_form.html', context)

@login_required
def it_ticket_list(request):
    # Redirect users with management access directly to the management list
    if request.user.is_superuser or getattr(request.user, 'has_it_support_management_access', False) or request.user.role == User.IT_TECHNICIAN:
        return redirect('it_support:it_ticket_management_list')

    tickets = IT_Ticket.objects.filter(user=request.user).order_by('-created_at')
    return themed_render(request, 'it_support/it_ticket_list.html', {'tickets': tickets})

@login_required
def it_ticket_detail(request, pk):
    can_manage = request.user.is_superuser or getattr(request.user, 'has_it_support_management_access', False) or request.user.role == User.IT_TECHNICIAN
    if can_manage:
        ticket = get_object_or_404(IT_Ticket.objects.prefetch_related('comments__author'), pk=pk)
    else:
        ticket = get_object_or_404(IT_Ticket.objects.prefetch_related('comments__author'), pk=pk, user=request.user)

    comments = ticket.comments.all()
    comment_form = IT_TicketCommentForm()

    if request.method == 'POST' and 'comment' in request.POST: # Check if it's a comment submission
        comment_form = IT_TicketCommentForm(request.POST, request.FILES)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.ticket = ticket
            new_comment.author = request.user
            new_comment.save()
            messages.success(request, 'Il tuo commento è stato aggiunto.')
            return redirect('it_support:it_ticket_detail', pk=ticket.pk)

    context = {
        'ticket': ticket,
        'comments': comments,
        'comment_form': comment_form,
    }
    return themed_render(request, 'it_support/it_ticket_detail.html', context)

@login_required
@it_support_management_access_required
def it_ticket_management_list(request):
    all_tickets = IT_Ticket.objects.all()
    open_tickets_count = all_tickets.filter(status__in=['open', 'in_progress']).count()
    unassigned_tickets_count = all_tickets.filter(status='open', assigned_to__isnull=True).count()
    my_tickets_count = all_tickets.filter(assigned_to=request.user).count()
    urgent_tickets_count = all_tickets.filter(priority='urgent', status__in=['open', 'in_progress']).count()

    view_filter = request.GET.get('view', 'all')
    if view_filter == 'unassigned':
        tickets = all_tickets.filter(status='open', assigned_to__isnull=True)
        page_title = 'Ticket IT Non Assegnati'
    elif view_filter == 'my_tickets':
        tickets = all_tickets.filter(assigned_to=request.user)
        page_title = 'Ticket IT Assegnati a Me'
    else:
        tickets = all_tickets
        page_title = 'Tutti i Ticket IT'

    context = {
        'tickets': tickets.order_by('-created_at'),
        'page_title': page_title,
        'view_filter': view_filter,
        'kpis': {
            'open_tickets': open_tickets_count,
            'unassigned_tickets': unassigned_tickets_count,
            'my_tickets': my_tickets_count,
            'urgent_tickets': urgent_tickets_count,
        }
    }
    return themed_render(request, 'it_support/it_ticket_management_list.html', context)

@login_required
@it_support_management_access_required
def it_reporting_dashboard(request):
    total_tickets = IT_Ticket.objects.count()
    tickets_by_status = IT_Ticket.objects.values('status').annotate(count=Count('status')).order_by('-count')
    tickets_by_priority = IT_Ticket.objects.values('priority').annotate(count=Count('priority')).order_by('-count')
    tickets_by_device = IT_Ticket.objects.values('device_type').annotate(count=Count('device_type')).order_by('-count')

    context = {
        'total_tickets': total_tickets,
        'tickets_by_status': tickets_by_status,
        'tickets_by_priority': tickets_by_priority,
        'tickets_by_device': tickets_by_device,
    }
    return themed_render(request, 'it_support/it_reporting_dashboard.html', context)

@login_required
@it_support_management_access_required
def active_chats_list_view(request):
    active_chats = IT_Ticket.objects.filter(chat_status='active').order_by('-updated_at')
    context = {
        'active_chats': active_chats
    }
    return themed_render(request, 'it_support/active_chats_list.html', context)

@login_required
@it_support_management_access_required
def it_ticket_update(request, pk):
    ticket = get_object_or_404(IT_Ticket, pk=pk)
    if request.method == 'POST':
        form = IT_TicketUpdateForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ticket #{ticket.pk} aggiornato con successo.")
            return redirect('it_support:it_ticket_detail', pk=ticket.pk)
    else:
        form = IT_TicketUpdateForm(instance=ticket)

    context = {
        'form': form,
        'ticket': ticket
    }
    return themed_render(request, 'it_support/it_ticket_update_form.html', context)

# --- Chat Lifecycle Views ---

@login_required
@require_POST
def request_chat(request, pk):
    ticket = get_object_or_404(IT_Ticket, pk=pk, user=request.user)
    if ticket.chat_status in ['none', 'declined', 'ended']:
        ticket.chat_status = 'requested'
        ticket.save()
        messages.success(request, 'Richiesta di chat inviata al supporto IT.')
    else:
        messages.warning(request, 'Una richiesta di chat è già in corso per questo ticket.')
    return redirect('it_support:it_ticket_detail', pk=pk)

@login_required
@require_POST
@it_support_management_access_required
def accept_chat(request, pk):
    ticket = get_object_or_404(IT_Ticket, pk=pk)
    if ticket.chat_status == 'requested':
        ticket.chat_status = 'active'
        ticket.save()
        ChatMessage.objects.create(ticket=ticket, author=None, message="La sessione di chat è stata avviata da un tecnico.")
        messages.success(request, 'Chat accettata e avviata.')
    return redirect('it_support:it_ticket_detail', pk=pk)

@login_required
@require_POST
@it_support_management_access_required
def decline_chat(request, pk):
    ticket = get_object_or_404(IT_Ticket, pk=pk)
    ticket.chat_status = 'declined'
    ticket.save()
    messages.info(request, 'Richiesta di chat rifiutata.')
    return redirect('it_support:it_ticket_detail', pk=pk)

@login_required
@require_POST
@it_support_management_access_required
def end_chat(request, pk):
    ticket = get_object_or_404(IT_Ticket, pk=pk)
    if ticket.chat_status == 'active':
        ticket.chat_status = 'ended'
        ticket.save()
        ChatMessage.objects.create(ticket=ticket, author=None, message="La sessione di chat è stata terminata dal tecnico.")
        messages.success(request, 'Chat terminata con successo.')
    return redirect('it_support:it_ticket_detail', pk=pk)

# --- API-like views for the frontend ---

def _user_can_access_ticket_chat(user, ticket):
    if ticket.user == user:
        return True
    if ticket.assigned_to == user:
        return True
    if user.is_superuser:
        return True
    if getattr(user, 'has_it_support_management_access', False):
        return True
    return user.role in [User.SUPERADMIN, User.IT_TECHNICIAN]

@login_required
def chat_messages(request, pk):
    try:
        ticket = IT_Ticket.objects.get(pk=pk)
    except IT_Ticket.DoesNotExist:
        return JsonResponse({'error': 'Not Found or Not Authorized'}, status=404)
    if not _user_can_access_ticket_chat(request.user, ticket):
        return JsonResponse({'error': 'Not Found or Not Authorized'}, status=404)

    since_timestamp_str = request.GET.get('since')
    messages_query = ticket.chat_messages.select_related('author').order_by('timestamp')

    if since_timestamp_str:
        try:
            since_timestamp = datetime.fromisoformat(since_timestamp_str.replace("Z", "+00:00"))
            messages_query = messages_query.filter(timestamp__gt=since_timestamp)
        except ValueError:
            pass
    messages = messages_query
    data = []
    for msg in messages:
        avatar_url = f'https://ui-avatars.com/api/?name={msg.author.username[0] if msg.author else "S"}&background=random&color=fff'
        if msg.author and msg.author.avatar:
            avatar_url = msg.author.avatar.url

        data.append({
            'author': msg.author.username if msg.author else "Sistema",
            'author_avatar_url': avatar_url,
            'message': msg.message,
            'timestamp': msg.timestamp.isoformat(),
            'is_me': msg.author == request.user if msg.author else False
        })
    return JsonResponse(data, safe=False)

@login_required
@require_POST
def chat_message_create(request, pk):
    try:
        ticket = IT_Ticket.objects.get(pk=pk)
    except IT_Ticket.DoesNotExist:
        return JsonResponse({'error': 'Not Found or Not Authorized'}, status=404)
    if not _user_can_access_ticket_chat(request.user, ticket):
        return JsonResponse({'error': 'Not Found or Not Authorized'}, status=404)

    payload = json.loads(request.body or '{}')
    message_text = (payload.get('message') or '').strip()
    if not message_text:
        return JsonResponse({'error': 'Message is required'}, status=400)

    new_message = ChatMessage.objects.create(
        ticket=ticket,
        author=request.user,
        message=message_text
    )

    avatar_url = f'https://ui-avatars.com/api/?name={request.user.username[0]}&background=random&color=fff'
    if request.user.avatar:
        avatar_url = request.user.avatar.url

    return JsonResponse({
        'author': request.user.username,
        'author_avatar_url': avatar_url,
        'message': new_message.message,
        'timestamp': new_message.timestamp.isoformat(),
        'is_me': True,
    })
