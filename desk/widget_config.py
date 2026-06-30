# A registry of all available widgets and their default properties
WIDGET_REGISTRY = {
    # Common
    'notification_center': {'id': 'notification-center-widget', 'name': 'Centro Notifiche', 'w': 5, 'h': 4, 'icon': 'fas fa-bell'},
    'recent_activity': {'id': 'recent-activity-widget', 'name': 'La Mia Attività Recente', 'w': 4, 'h': 4, 'icon': 'fas fa-history'},
    'calendar': {'id': 'calendar-widget', 'name': 'Calendario Eventi', 'w': 7, 'h': 4, 'icon': 'fas fa-calendar-alt'},
    'announcements': {'id': 'announcements-widget', 'name': 'Annunci Recenti', 'w': 4, 'h': 4, 'icon': 'fas fa-bullhorn'},

    # Superadmin / Corporate
    'ticket_overview': {'id': 'ticket-overview-widget', 'name': 'Panoramica Ticket Globale', 'w': 7, 'h': 4, 'icon': 'fas fa-globe-europe'},
    'recent_reviews': {'id': 'recent-reviews-widget', 'name': 'Ultime Recensioni Globali', 'w': 6, 'h': 4, 'icon': 'fas fa-star-half-alt'},

    # Director
    'director_kpis': {'id': 'director-kpis-widget', 'name': 'KPI Principali', 'w': 12, 'h': 2, 'icon': 'fas fa-chart-line'},
    'director_reviews': {'id': 'director-reviews-widget', 'name': 'Andamento Recensioni', 'w': 6, 'h': 4, 'icon': 'fas fa-star'},

    # Maintainer
    'maintainer_tickets': {'id': 'maintainer-tickets-widget', 'name': 'I Miei Ticket Attivi', 'w': 6, 'h': 3, 'icon': 'fas fa-ticket-alt'},
    'maintainer_quick_access': {'id': 'maintainer-quick-access-widget', 'name': 'Accesso Rapido', 'w': 6, 'h': 3, 'icon': 'fas fa-bolt'},

    # Head Maintainer
    'ticket_assignment': {'id': 'ticket-assignment-widget', 'name': 'Assegnazione Ticket', 'w': 5, 'h': 4, 'icon': 'fas fa-user-plus'},
    'team_performance': {'id': 'team-performance-widget', 'name': 'Performance Team', 'w': 7, 'h': 4, 'icon': 'fas fa-chart-pie'},
    'critical_stock': {'id': 'critical-stock-widget', 'name': 'Scorte Critiche', 'w': 6, 'h': 3, 'icon': 'fas fa-box-open'},
    'urgent_tickets': {'id': 'urgent-tickets-widget', 'name': 'Ticket Urgenti/Scaduti', 'w': 6, 'h': 3, 'icon': 'fas fa-exclamation-triangle'},

    # Receptionist
    'daily_arrivals': {'id': 'daily-arrivals-widget', 'name': 'Arrivi del Giorno', 'w': 6, 'h': 5, 'icon': 'fas fa-plane-arrival'},
    'quick_ticket': {'id': 'quick-ticket-widget', 'name': 'Creazione Rapida Ticket', 'w': 4, 'h': 5, 'icon': 'fas fa-plus-square'},
    'resort_recent_tickets': {'id': 'resort-recent-tickets-widget', 'name': 'Ticket Recenti del Resort', 'w': 8, 'h': 5, 'icon': 'fas fa-concierge-bell'},
    'guest_announcements': {'id': 'guest-announcements-widget', 'name': 'Annunci per Ospiti', 'w': 7, 'h': 4, 'icon': 'fas fa-info-circle'},
    'useful_documents': {'id': 'useful-documents-widget', 'name': 'Documenti Utili', 'w': 5, 'h': 4, 'icon': 'fas fa-file-alt'},

    # Owner
    'financial_performance': {'id': 'financial-performance-widget', 'name': 'Performance Finanziaria', 'w': 6, 'h': 4, 'icon': 'fas fa-euro-sign'},
    'online_reputation': {'id': 'online-reputation-widget', 'name': 'Reputazione Online', 'w': 6, 'h': 4, 'icon': 'fas fa-medal'},
    'competitor_analysis': {'id': 'competitor-analysis-widget', 'name': 'Analisi Competitor', 'w': 12, 'h': 4, 'icon': 'fas fa-search-dollar'},

    # Housekeeping
    'room_status': {'id': 'room-status-widget', 'name': 'Stato Camere', 'w': 8, 'h': 4, 'icon': 'fas fa-bed'},
    'quick_report': {'id': 'quick-report-widget', 'name': 'Segnalazione Rapida', 'w': 4, 'h': 4, 'icon': 'fas fa-flag'},

    # Administrative
    'approved_pos': {'id': 'approved-pos-widget', 'name': 'Ordini da Processare', 'w': 6, 'h': 4, 'icon': 'fas fa-check-double'},
    'supplier_list': {'id': 'supplier-list-widget', 'name': 'Accesso Fornitori', 'w': 6, 'h': 4, 'icon': 'fas fa-truck'},

    # Economo / Capo Economo
    'po_approvals': {'id': 'po-approvals-widget', 'name': 'Approvazione Ordini', 'w': 12, 'h': 4, 'icon': 'fas fa-stamp'},

    # IT Technician
    'it_tickets': {'id': 'it-tickets-widget', 'name': 'I Miei Ticket IT', 'w': 8, 'h': 4, 'icon': 'fas fa-laptop-code'},
    'active_chats': {'id': 'active-chats-widget', 'name': 'Chat di Supporto Attive', 'w': 4, 'h': 4, 'icon': 'fas fa-comments'},
    'system_pulse': {'id': 'system-pulse-widget', 'name': 'System Pulse', 'w': 4, 'h': 4, 'icon': 'fas fa-heartbeat'},
}

# Registry of full-page applications available in Nuvia OS
# IMPORTANT: Use relative URLs to avoid X-Frame-Options mismatches with SAMEORIGIN
APP_REGISTRY = {
    'hr_portal': {
        'id': 'hr-portal-app',
        'name': 'Portal HR',
        'icon': 'fas fa-users-cog',
        'url': '/hr/',
        'type': 'iframe',
        'category': 'management'
    },
    'maintenance': {
        'id': 'maintenance-app',
        'name': 'Gestione Manutenzioni',
        'icon': 'fas fa-tools',
        'url': '/maintenance/',
        'type': 'iframe',
        'category': 'operations'
    },
    'menu_studio': {
        'id': 'menu-studio-app',
        'name': 'Menu Creation Studio',
        'icon': 'fas fa-utensils',
        'url': '/menu-generator/',
        'type': 'iframe',
        'category': 'operations'
    },
    'profile_cards': {
        'id': 'profile-cards-app',
        'name': 'Digital Business Cards',
        'icon': 'fas fa-id-card',
        'url': '/cards/',
        'type': 'iframe',
        'category': 'identity'
    },
    'financial_dashboard': {
        'id': 'financial-dashboard-app',
        'name': 'Analisi Finanziaria',
        'icon': 'fas fa-chart-pie',
        'url': '/finanza/',
        'type': 'iframe',
        'category': 'management'
    },
    'bookings': {
        'id': 'bookings-app',
        'name': 'Gestione Prenotazioni',
        'icon': 'fas fa-calendar-check',
        'url': '/bookings/',
        'type': 'iframe',
        'category': 'operations'
    },
    'documents': {
        'id': 'documents-app',
        'name': 'Amministrazione & Doc',
        'icon': 'fas fa-file-invoice-dollar',
        'url': '/amministrazione/',
        'type': 'iframe',
        'category': 'management'
    },
    'reviews': {
        'id': 'reviews-app',
        'name': 'Analisi Recensioni',
        'icon': 'fas fa-star-half-alt',
        'url': '/reviews/analysis-center/',
        'type': 'iframe',
        'category': 'management'
    },
    'it_support': {
        'id': 'it-support-app',
        'name': 'Supporto IT',
        'icon': 'fas fa-laptop-code',
        'url': '/supporto-it/',
        'type': 'iframe',
        'category': 'operations'
    },
    'bacheca': {
        'id': 'bacheca-app',
        'name': 'Bacheca Nuvia',
        'icon': 'fas fa-chalkboard-user',
        'url': '/hr/bacheca/',
        'type': 'iframe',
        'category': 'identity'
    },
    'nuvia_mail': {
        'id': 'nuvia-mail-app',
        'name': 'Nuvia Mail',
        'icon': 'fas fa-envelope',
        'url': '/nuvia-mail/?chromeless=true',
        'type': 'iframe',
        'category': 'operations'
    },
    'veratour_upload': {
        'id': 'veratour-upload-app',
        'name': 'Upload Veratour',
        'icon': 'fas fa-file-excel',
        'url': '/reviews/veratour/upload/',
        'type': 'iframe',
        'category': 'management'
    },
}

# Mapping of roles to the apps they can access
ROLE_APP_MAP = {
    'all': ['profile_cards', 'bacheca', 'nuvia_mail'],
    'superadmin': ['hr_portal', 'maintenance', 'menu_studio', 'financial_dashboard', 'bookings', 'documents', 'reviews', 'it_support', 'veratour_upload'],
    'corporate': ['financial_dashboard', 'bookings', 'reviews', 'veratour_upload'],
    'head_maintainer': ['maintenance'],
    'maintainer': ['maintenance'],
    'director': ['hr_portal', 'maintenance', 'financial_dashboard', 'bookings', 'documents', 'reviews', 'veratour_upload'],
    'owner': ['financial_dashboard', 'documents', 'reviews', 'veratour_upload'],
    'receptionist': ['bookings', 'maintenance'],
    'risorse_umane': ['hr_portal', 'documents'],
    'it_technician': ['it_support'],
}

# Mapping of roles to the widgets they can access
ROLE_WIDGET_MAP = {
    'all': ['notification_center', 'recent_activity', 'calendar', 'announcements', 'system_pulse'],  # Widgets for everyone
    'superadmin': [
        'ticket_overview',
        'recent_reviews',
        'director_kpis',
        'room_status',
        'daily_arrivals',
    ],
    'corporate': [
        'ticket_overview',
        'recent_reviews',
    ],
    'head_maintainer': [
        'ticket_assignment',
        'team_performance',
        'critical_stock',
        'urgent_tickets',
    ],
    'maintainer': ['maintainer_tickets', 'maintainer_quick_access'],
    'director': ['director_kpis', 'director_reviews'],
    'receptionist': [
        'daily_arrivals',
        'quick_ticket',
        'resort_recent_tickets',
        'guest_announcements',
        'useful_documents',
    ],
    'owner': [
        'financial_performance',
        'online_reputation',
        'competitor_analysis',
        'director_kpis', # Owners likely want to see KPIs as well
    ],
    'housekeeping': [
        'room_status',
        'quick_report',
    ],
    'administrative': [
        'approved_pos',
        'supplier_list',
        'useful_documents', # Re-using this from Receptionist
    ],
    'economo': [
        'critical_stock',
        'supplier_list',
    ],
    'capo_economo': [
        'po_approvals',
        'critical_stock',
        'supplier_list',
    ],
    'it_technician': [
        'it_tickets',
        'active_chats',
    ],
}
