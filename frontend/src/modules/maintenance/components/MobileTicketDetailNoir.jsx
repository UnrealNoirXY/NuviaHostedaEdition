import React, { useState, useEffect } from "react";
import PropTypes from "prop-types";
import moment from "moment";

moment.locale("it");

const statusLabels = {
  open: "Aperto",
  in_progress: "In lavorazione",
  resolved: "Risolto",
  closed: "Chiuso",
};

export default function MobileTicketDetailNoir({
  ticket,
  onClose,
  onUpdate,
  onAddComment,
  onClaim,
  onRelease,
  canClaim,
  currentUserId,
  metadata,
}) {
  const [comment, setComment] = useState("");
  const [attachment, setAttachment] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!ticket) return null;

  const isAssigned = !!ticket.assigned_to;
  const isMine = ticket.assigned_to?.id === currentUserId;
  const canRelease = isMine || (metadata?.permissionMap?.canAssignTickets);
  const canAssign = metadata?.permissionMap?.canAssignTickets;

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!comment && !attachment) return;
    setIsSubmitting(true);
    try {
      await onAddComment({ comment, attachment });
      setComment("");
      setAttachment(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleQuickResolve = async () => {
    if (!window.confirm("Hai completato il lavoro?")) return;
    await onUpdate({ status: "resolved" });
  };

  return (
    <div className="noir-sheet">
      <header className="sheet-header">
        <div className="title">Dettaglio Ticket #{ticket.id}</div>
        <button type="button" className="close-btn" onClick={onClose}>
          <i className="fa-solid fa-xmark" />
        </button>
      </header>

      <div className="sheet-body">
        <div className="noir-section-title" style={{ fontSize: '1.4rem' }}>{ticket.title}</div>

        <div className="noir-ticket-card" style={{ background: 'var(--nuvia-glass)', marginBottom: '1.5rem' }}>
           <div className="card-body">
              <div className="ticket-location" style={{ marginBottom: '0.5rem' }}>
                <i className="fa-solid fa-location-dot" />
                <span>{ticket.resort?.name} · {ticket.room?.name || "Aree Comuni"}</span>
              </div>
              <div className="ticket-location">
                <i className="fa-solid fa-user" />
                <span>Creato da {ticket.created_by?.username}</span>
              </div>
              {ticket.due_date && (
                <div className="ticket-location" style={{ marginTop: '0.5rem', color: 'var(--nuvia-warning)' }}>
                   <i className="fa-regular fa-clock" />
                   <span>Scade {moment(ticket.due_date).fromNow()}</span>
                </div>
              )}
           </div>
        </div>

        <div className="noir-section-subtitle" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--nuvia-text-muted)', marginBottom: '0.75rem' }}>Descrizione</div>
        <p style={{ lineHeight: '1.6', fontSize: '0.95rem', marginBottom: '2rem' }}>{ticket.description}</p>

        {ticket.attachment && (
          <div style={{ marginBottom: '2rem' }}>
             <a href={ticket.attachment} target="_blank" rel="noreferrer" className="noir-btn secondary" style={{ width: '100%' }}>
                <i className="fa-solid fa-paperclip" /> Vedi Allegato Originale
             </a>
          </div>
        )}

        <div className="card-actions" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '2rem' }}>
          {canClaim && !isAssigned && (
            <button type="button" className="noir-btn primary" style={{ gridColumn: 'span 2' }} onClick={() => onClaim()}>
              <i className="fa-solid fa-handshake-angle" /> Prendi in Carico
            </button>
          )}

          {isMine && ticket.status !== 'resolved' && (
            <button type="button" className="noir-btn success" style={{ gridColumn: 'span 2' }} onClick={handleQuickResolve}>
              <i className="fa-solid fa-check" /> Segna come Risolto
            </button>
          )}

          {canRelease && isAssigned && (
             <button type="button" className="noir-btn secondary" onClick={() => onRelease()}>
                <i className="fa-solid fa-share-from-square" /> Rilascia
             </button>
          )}

          <button type="button" className="noir-btn secondary" onClick={() => {
            document.getElementById('noir-comment-input').scrollIntoView({ behavior: 'smooth' });
            document.getElementById('noir-comment-input').focus();
          }}>
             <i className="fa-solid fa-comment" /> Commenta
          </button>
        </div>

        {canAssign && (
          <div style={{ marginBottom: '2rem' }}>
            <div className="noir-section-subtitle" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--nuvia-text-muted)', marginBottom: '0.75rem' }}>Assegnazione</div>
            <select
              value={ticket.assigned_to?.id || ""}
              onChange={(e) => onUpdate({ assigned_to: e.target.value })}
              style={{ width: '100%', background: 'var(--nuvia-surface)', border: '1px solid var(--nuvia-border)', borderRadius: '12px', padding: '0.75rem', color: '#fff' }}
            >
              <option value="">Non assegnato</option>
              {metadata.maintainers?.map(m => (
                <option key={m.id} value={m.id}>{m.first_name} {m.last_name}</option>
              ))}
            </select>
          </div>
        )}

        <div className="noir-section-subtitle" style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--nuvia-text-muted)', marginBottom: '1rem' }}>Aggiornamenti e Foto</div>

        <div className="comment-list" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '2rem' }}>
          {(ticket.comments || []).map(c => (
            <div key={c.id} style={{ background: 'var(--nuvia-glass)', padding: '1rem', borderRadius: '1rem', border: '1px solid var(--nuvia-border)' }}>
               <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--nuvia-text-muted)', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: '700', color: 'var(--nuvia-blue)' }}>{c.author?.username}</span>
                  <span>{moment(c.created_at).fromNow()}</span>
               </div>
               <p style={{ margin: 0, fontSize: '0.9rem' }}>{c.comment}</p>
               {c.attachment && (
                 <img src={c.attachment} alt="Allegato" style={{ maxWidth: '100%', borderRadius: '0.75rem', marginTop: '0.75rem' }} />
               )}
            </div>
          ))}
        </div>

        <form onSubmit={handleAddComment} style={{ background: 'var(--nuvia-surface)', padding: '1.25rem', borderRadius: '1.5rem', border: '1px solid var(--nuvia-border)', marginBottom: '2rem' }}>
           <textarea
             id="noir-comment-input"
             placeholder="Aggiungi una nota o descrivi il lavoro..."
             value={comment}
             onChange={(e) => setComment(e.target.value)}
             style={{ width: '100%', background: 'transparent', border: 'none', color: '#fff', outline: 'none', resize: 'none', minHeight: '80px', fontSize: '0.95rem' }}
           />
           <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', borderTop: '1px solid var(--nuvia-border)', paddingTop: '1rem' }}>
              <label style={{ cursor: 'pointer', color: 'var(--nuvia-blue)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                 <i className="fa-solid fa-camera" />
                 <span style={{ fontSize: '0.85rem', fontWeight: '600' }}>{attachment ? "Foto pronta" : "Aggiungi Foto"}</span>
                 <input type="file" accept="image/*" capture="environment" hidden onChange={(e) => setAttachment(e.target.files[0])} />
              </label>
              <button type="submit" className="noir-btn primary" disabled={isSubmitting || (!comment && !attachment)} style={{ padding: '0.5rem 1.25rem' }}>
                 Invia
              </button>
           </div>
        </form>
      </div>
    </div>
  );
}

MobileTicketDetailNoir.propTypes = {
  ticket: PropTypes.object,
  onClose: PropTypes.func.isRequired,
  onUpdate: PropTypes.func.isRequired,
  onAddComment: PropTypes.func.isRequired,
  onClaim: PropTypes.func.isRequired,
  onRelease: PropTypes.func.isRequired,
  canClaim: PropTypes.bool.isRequired,
  currentUserId: PropTypes.number.isRequired,
  metadata: PropTypes.object.isRequired,
};
