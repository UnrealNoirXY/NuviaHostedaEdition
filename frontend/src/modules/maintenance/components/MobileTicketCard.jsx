import React from "react";
import PropTypes from "prop-types";
import moment from "moment";

const statusLabels = {
  open: "Aperto",
  in_progress: "Lavoro",
  resolved: "Finito",
  closed: "Chiuso",
};

export default function MobileTicketCard({
  ticket,
  onSelect,
  onClaim,
  onResolve,
  canClaim,
  currentUserId
}) {
  const isAssigned = !!ticket.assigned_to;
  const isMine = ticket.assigned_to?.id === currentUserId;
  const isUrgent = ticket.priority === "urgent" || ticket.priority === "high";

  return (
    <article className={`noir-ticket-card ${isUrgent ? "urgent" : ""}`} onClick={() => onSelect(ticket.id)}>
      <div className="card-header">
        <span className="ticket-id">#{ticket.id}</span>
        <span className={`status-pill status-${ticket.status}`}>
          {statusLabels[ticket.status] || ticket.status}
        </span>
      </div>

      <div className="card-body">
        <span className="ticket-title">{ticket.title}</span>
        <div className="ticket-location">
          <i className="fa-solid fa-location-dot" />
          <span>{ticket.resort?.name} · {ticket.room?.name || "Aree Comuni"}</span>
        </div>
        {ticket.due_date && (
           <div className="ticket-location" style={{ marginTop: '0.4rem', color: isUrgent ? 'var(--nuvia-danger)' : 'var(--nuvia-warning)' }}>
             <i className="fa-regular fa-clock" />
             <span>Scade {moment(ticket.due_date).fromNow()}</span>
           </div>
        )}
      </div>

      <div className="card-actions">
        {canClaim && !isAssigned && (
          <button
            type="button"
            className="noir-btn primary"
            onClick={(e) => { e.stopPropagation(); onClaim(ticket.id); }}
          >
            <i className="fa-solid fa-handshake-angle" /> Prendi
          </button>
        )}

        {isMine && ticket.status !== 'resolved' && (
          <button
            type="button"
            className="noir-btn success"
            onClick={(e) => { e.stopPropagation(); onResolve(ticket.id); }}
          >
            <i className="fa-solid fa-check" /> Risolto
          </button>
        )}

        <button
          type="button"
          className="noir-btn secondary"
          onClick={(e) => { e.stopPropagation(); onSelect(ticket.id); }}
          style={{ gridColumn: (isAssigned && !isMine) || ticket.status === 'resolved' ? 'span 2' : 'auto' }}
        >
          <i className="fa-solid fa-up-right-from-square" /> Apri
        </button>
      </div>
    </article>
  );
}

MobileTicketCard.propTypes = {
  ticket: PropTypes.object.isRequired,
  onSelect: PropTypes.func.isRequired,
  onClaim: PropTypes.func.isRequired,
  onResolve: PropTypes.func.isRequired,
  canClaim: PropTypes.bool.isRequired,
  currentUserId: PropTypes.number.isRequired,
};
