export const getNuviaCommands = (query) => {
    const q = query.toLowerCase();
    const commands = [];

    if (!q) return commands;

    // Maintenance commands
    if (q.includes('nuov') && (q.includes('manut') || q.includes('ticket') || q.includes('guast'))) {
        commands.push({
            id: 'ai-cmd-new-ticket',
            name: 'Crea Nuova Manutenzione',
            icon: 'fa-plus-circle',
            type: 'AI Command',
            action: { type: 'redirect', url: '/maintenance/ticket/nuovo/' },
            description: 'Avvia il wizard per una nuova segnalazione'
        });
    }

    if (q.includes('miei') && (q.includes('ticket') || q.includes('compiti') || q.includes('lavori'))) {
        commands.push({
            id: 'ai-cmd-my-tickets',
            name: 'Mostra i Miei Ticket',
            icon: 'fa-list-check',
            type: 'AI Command',
            action: { type: 'launch', targetId: 'maintainer-tickets-widget' },
            description: 'Apri la lista degli interventi assegnati a te'
        });
    }

    if (q.includes('recensioni') || q.includes('review') || q.includes('analisi')) {
        commands.push({
            id: 'ai-cmd-reviews',
            name: 'Analisi Recensioni',
            icon: 'fa-star-half-alt',
            type: 'AI Command',
            action: { type: 'launch', targetId: 'reviews-app' },
            description: 'Accedi al centro analisi recensioni'
        });
    }

    if (q.includes('it') || q.includes('supporto') || q.includes('pc') || q.includes('tecnico')) {
        commands.push({
            id: 'ai-cmd-it-support',
            name: 'Supporto IT',
            icon: 'fa-laptop-code',
            type: 'AI Command',
            action: { type: 'launch', targetId: 'it-support-app' },
            description: 'Apri la gestione ticket IT e supporto'
        });
    }

    if (q.includes('bacheca') || q.includes('comunicazioni') || q.includes('hr')) {
        commands.push({
            id: 'ai-cmd-bacheca',
            name: 'Bacheca Nuvia',
            icon: 'fa-chalkboard-user',
            type: 'AI Command',
            action: { type: 'launch', targetId: 'bacheca-app' },
            description: 'Controlla documenti, buste paga e avvisi'
        });
    }

    // Room/Operations commands
    if (q.includes('stato') && (q.includes('camer') || q.includes('room'))) {
        commands.push({
            id: 'ai-cmd-room-status',
            name: 'Stato Camere in Tempo Reale',
            icon: 'fa-bed',
            type: 'AI Command',
            action: { type: 'launch', targetId: 'room-status-widget' },
            description: 'Visualizza la pulizia e l\'occupazione delle camere'
        });
    }

    if (q.includes('arrivi') || q.includes('check-in') || q.includes('oggi')) {
        commands.push({
            id: 'ai-cmd-arrivals',
            name: 'Arrivi del Giorno',
            icon: 'fa-plane-arrival',
            type: 'AI Command',
            action: { type: 'launch', targetId: 'daily-arrivals-widget' },
            description: 'Controlla chi arriva oggi in struttura'
        });
    }

    // System commands
    if (q.includes('esci') || q.includes('logout') || q.includes('chiudi sessione')) {
        commands.push({
            id: 'ai-cmd-logout',
            name: 'Termina Sessione',
            icon: 'fa-power-off',
            type: 'AI Command',
            action: { type: 'redirect', url: '/logout/' },
            description: 'Disconnetti l\'utente corrente in sicurezza'
        });
    }

    if (q.includes('profilo') || q.includes('impostazioni')) {
        commands.push({
            id: 'ai-cmd-profile',
            name: 'Gestione Profilo',
            icon: 'fa-user-gear',
            type: 'AI Command',
            action: { type: 'redirect', url: '/profile/' },
            description: 'Modifica i tuoi dati e le preferenze'
        });
    }

    // AI Assistant
    if (q.includes('assistente') || q.includes('aiuto') || q.includes('nuvia') || q.includes('ciao')) {
        commands.push({
            id: 'ai-cmd-assistant',
            name: 'Parla con Nuvia AI',
            icon: 'fa-robot',
            type: 'AI Command',
            action: { type: 'event', name: 'homeDesk.openAssistant' },
            description: 'Chiedi aiuto o informazioni sulla struttura'
        });
    }

    return commands;
};
