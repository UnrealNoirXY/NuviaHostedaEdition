import React from "react";
import PropTypes from "prop-types";

const formatCurrency = (value) => {
  if (value === null || value === undefined) return "€0";
  const amount = Number.parseFloat(value);
  return amount.toLocaleString("it-IT", { style: "currency", currency: "EUR" });
};

export default function MobileRoomDetailSheet({ detail, onClose, onSelectTickets }) {
  if (!detail) return null;

  return (
    <div className="noir-sheet">
      <header className="sheet-header">
        <div className="title">Dettaglio {detail.room?.name}</div>
        <button type="button" className="close-btn" onClick={onClose}>
          <i className="fa-solid fa-xmark" />
        </button>
      </header>

      <div className="sheet-body">
        <div className="noir-section-title" style={{ fontSize: '1.4rem' }}>{detail.room?.name}</div>
        <p style={{ color: 'var(--nuvia-text-muted)', marginBottom: '1.5rem' }}>{detail.room?.resort?.name}</p>

        <div className="noir-grid">
           <div className="noir-tile">
              <div className="tile-label">Ticket Aperti</div>
              <div className="tile-value">{detail.stats?.openTickets || 0}</div>
           </div>
           <div className="noir-tile">
              <div className="tile-label">Investito</div>
              <div className="tile-value" style={{ fontSize: '1.1rem' }}>{formatCurrency(detail.stats?.investedBudget)}</div>
           </div>
        </div>

        <div className="noir-section-subtitle" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--nuvia-text-muted)', marginBottom: '1rem' }}>Ticket Attivi</div>

        {detail.tickets?.open?.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {detail.tickets.open.map(t => (
              <div key={t.id} className="noir-ticket-card" onClick={() => onSelectTickets([t.id])} style={{ background: 'var(--nuvia-glass)', padding: '1rem' }}>
                 <div style={{ fontWeight: '700', marginBottom: '0.25rem' }}>{t.title}</div>
                 <div style={{ fontSize: '0.8rem', color: 'var(--nuvia-text-muted)' }}>{t.status} · {t.priority}</div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--nuvia-text-muted)' }}>Nessun ticket aperto per questa camera.</p>
        )}

        <div className="noir-section-subtitle" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--nuvia-text-muted)', marginTop: '2rem', marginBottom: '1rem' }}>Allerte</div>
        {detail.alerts?.length > 0 ? (
           <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {detail.alerts.map(a => (
                <li key={a.id} style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.2)', padding: '0.75rem', borderRadius: '0.75rem', color: 'var(--nuvia-danger)', fontSize: '0.85rem' }}>
                   {a.reason}
                </li>
              ))}
           </ul>
        ) : (
          <p style={{ color: 'var(--nuvia-text-muted)' }}>Nessuna allerta attiva.</p>
        )}
      </div>
    </div>
  );
}

MobileRoomDetailSheet.propTypes = {
  detail: PropTypes.object,
  onClose: PropTypes.func.isRequired,
  onSelectTickets: PropTypes.func.isRequired,
};
