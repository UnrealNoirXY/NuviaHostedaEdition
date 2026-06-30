const translations = {
    it: {
        downloadReady: 'Documento pronto al download',
        downloadError: 'Errore durante la generazione del documento',
        documentStarting: 'Generazione documenti avviata...',
        auditTrail: 'Registro attività',
        auditEmpty: 'Nessuna attività registrata',
    },
    en: {
        downloadReady: 'Document ready to download',
        downloadError: 'Error generating document',
        documentStarting: 'Document generation started...',
        auditTrail: 'Activity log',
        auditEmpty: 'No activity recorded',
    },
};

export const getLocale = () => (navigator.language || 'it').startsWith('en') ? 'en' : 'it';

export const t = (key) => {
    const locale = getLocale();
    return translations[locale]?.[key] || translations.it[key] || key;
};
