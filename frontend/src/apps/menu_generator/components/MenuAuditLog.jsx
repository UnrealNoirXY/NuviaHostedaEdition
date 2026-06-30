import React, { useEffect, useState } from 'react';
import { getMenuAuditTrail } from '../api';
import { t } from '../i18n';

const ACTION_ICONS = {
    publish: 'bi-cloud-check',
    snapshot: 'bi-camera',
    restore: 'bi-arrow-counterclockwise',
    clone: 'bi-copy',
};

const ACTION_ICONS_FA = {
    publish: 'fa-cloud-upload-alt',
    snapshot: 'fa-camera-retro',
    restore: 'fa-history',
    clone: 'fa-clone',
    insight: 'fa-lightbulb',
};

const AuditRow = ({ event }) => (
    <div className="d-flex justify-content-between align-items-center border-bottom border-white border-opacity-5 py-3 last-no-border">
        <div className="d-flex align-items-center gap-3">
            <div className="p-2 rounded bg-white bg-opacity-5 text-nuvia-primary border border-white border-opacity-5" style={{ width: '36px', height: '36px', display: 'grid', placeItems: 'center' }}>
                <i className={`fas ${ACTION_ICONS_FA[event.action] || 'fa-info-circle'} tiny`}></i>
            </div>
            <div>
                <div className="fw-bold smallest text-white uppercase ls-1 mb-1">{event.action}</div>
                <div className="text-muted-soft tiny fw-bold uppercase ls-tight">{event.metadata?.version || event.metadata?.format || 'SYSTEM LOG'}</div>
            </div>
        </div>
        <div className="text-end">
            <div className="smallest fw-bold text-white mb-1">{event.actor_display || '—'}</div>
            <div className="tiny text-muted-soft uppercase ls-1">{new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
        </div>
    </div>
);

const MenuAuditLog = ({ menuId }) => {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchAudit = async () => {
            setLoading(true);
            try {
                const res = await getMenuAuditTrail(menuId, { page_size: 5 });
                setEvents(res.data.results || res.data);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        };
        fetchAudit();
    }, [menuId]);

    return (
        <div className="d-flex flex-column overflow-hidden mt-4">
            <div className="d-flex align-items-center gap-2 mb-3">
                <i className="fas fa-fingerprint tiny text-nuvia-accent"></i>
                <span className="smallest fw-bold text-white uppercase ls-1">Audit Trail Operativo</span>
            </div>

            <div className="p-1 overflow-auto" style={{ maxHeight: '220px' }}>
                {loading && <div className="text-center py-4 animate-pulse text-muted-soft smallest fw-bold uppercase ls-1">Sincronizzazione log...</div>}
                {!loading && events.length === 0 && (
                    <div className="text-muted-soft smallest py-4 text-center border border-dashed border-white border-opacity-10 rounded-3">Nessuna attività registrata</div>
                )}
                {!loading && events.length > 0 && (
                    <div className="audit-list">
                        {events.map((ev) => (
                            <AuditRow key={ev.id} event={ev} />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default MenuAuditLog;
