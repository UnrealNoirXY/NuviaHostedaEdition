import React from "react";
import PropTypes from "prop-types";

export default function MaintenanceMissionControl({ stats, onSelectTab, onApplyQuickFilter }) {
  return (
    <div className="noir-mission-control">
      <div className="noir-section-title">Mission Control</div>

      <div className="noir-grid">
        <div className="noir-tile" onClick={() => onApplyQuickFilter({ status: "open" })}>
          <div className="tile-icon"><i className="fa-solid fa-list-check" /></div>
          <div className="tile-label">Ticket Aperti</div>
          <div className="tile-value">{stats.open || 0}</div>
        </div>

        <div className="noir-tile tile-urgent" onClick={() => onApplyQuickFilter({ due: "overdue" })}>
          <div className="tile-icon"><i className="fa-solid fa-triangle-exclamation" /></div>
          <div className="tile-label">Scaduti</div>
          <div className="tile-value">{stats.overdue || 0}</div>
        </div>

        <div className="noir-tile" onClick={() => onApplyQuickFilter({ assignment: "unassigned" })}>
          <div className="tile-icon"><i className="fa-solid fa-people-group" /></div>
          <div className="tile-label">Da Assegnare</div>
          <div className="tile-value">{stats.unassigned || 0}</div>
        </div>

        <div className="noir-tile" onClick={() => onSelectTab("rooms")}>
          <div className="tile-icon"><i className="fa-solid fa-bed" /></div>
          <div className="tile-label">Stato Camere</div>
          <div className="tile-value">{stats.roomsCritical || 0}</div>
        </div>
      </div>

      <div className="noir-section-subtitle" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--nuvia-text-muted)', marginBottom: '1rem' }}>Prossime Azioni</div>

      <button className="noir-ticket-card noir-btn-card" onClick={() => onSelectTab("new")}>
          <div className="tile-icon" style={{ width: '44px', height: '44px', background: 'rgba(56, 189, 248, 0.2)', borderRadius: '12px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#38bdf8' }}>
            <i className="fa-solid fa-plus" />
          </div>
          <div style={{ flex: 1 }}>
            <span style={{ fontWeight: '700', display: 'block', fontSize: '1rem' }}>Nuovo Ticket</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--nuvia-text-muted)' }}>Segnala un nuovo guasto</span>
          </div>
          <i className="fa-solid fa-chevron-right" style={{ opacity: 0.5 }} />
      </button>
    </div>
  );
}

MaintenanceMissionControl.propTypes = {
  stats: PropTypes.object.isRequired,
  onSelectTab: PropTypes.func.isRequired,
  onApplyQuickFilter: PropTypes.func.isRequired,
};
