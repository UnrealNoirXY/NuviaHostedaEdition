import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import moment from "moment";
import ConfirmationDialog from "./ConfirmationDialog";

moment.locale("it");

function formatDateTime(value) {
  return value ? moment(value).format("YYYY-MM-DDTHH:mm") : "";
}

const statusLabels = {
  open: "Aperto",
  in_progress: "In lavorazione",
  resolved: "Risolto",
  closed: "Chiuso",
};

const priorityLabels = {
  low: "Bassa",
  medium: "Media",
  high: "Alta",
  urgent: "Urgente",
};

export default function TicketDetail({
  ticket,
  metadata,
  canEditDeadline,
  onUpdate,
  onAddComment,
  onClaim,
  onRelease,
  canClaim,
  currentUserId,
  onExtendDeadline,
  isCompact,
  onClose,
}) {
  const [formState, setFormState] = useState({
    status: "open",
    notes: "",
    dueDate: "",
    deadlineJustification: "",
    completionPhoto: null,
    ackDueDate: "",
    ackDirty: false,
  });
  const [commentState, setCommentState] = useState({
    comment: "",
    attachment: null,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isCommentSubmitting, setIsCommentSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);
  const [extensionState, setExtensionState] = useState({
    dueDate: "",
    justification: "",
    error: "",
    submitting: false,
  });
  const [confirmation, setConfirmation] = useState({
    open: false,
    title: "",
    message: "",
    confirmLabel: "",
    onConfirm: null,
    onError: null,
  });
  const [confirmProcessing, setConfirmProcessing] = useState(false);
  const statuses = metadata?.statuses?.length
    ? metadata.statuses
    : Object.entries(statusLabels).map(([value, label]) => ({ value, label }));

  useEffect(() => {
    if (ticket) {
      setFormState({
        status: ticket.status,
        notes: ticket.notes || "",
        dueDate: formatDateTime(ticket.due_date),
        deadlineJustification: "",
        completionPhoto: null,
        ackDueDate: formatDateTime(ticket.acknowledged_due_date || ticket.due_date),
        ackDirty: false,
      });
      setExtensionState({ dueDate: "", justification: "", error: "", submitting: false });
    }
  }, [ticket]);

  const history = useMemo(
    () => (ticket?.history || []).slice().sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp)),
    [ticket]
  );
  const ackPending = Boolean(ticket?.due_date) && !ticket?.acknowledged_due_date;
  const assignedToCurrentUser = Boolean(ticket?.assigned_to?.id) && ticket.assigned_to.id === currentUserId;
  const assignedDisplayName = ticket?.assigned_to
    ? [ticket.assigned_to.first_name, ticket.assigned_to.last_name].filter(Boolean).join(" ") || ticket.assigned_to.username
    : "";
  const canClaimTicket = Boolean(ticket) && canClaim && !ticket.assigned_to;
  const canReleaseTicket =
    Boolean(ticket) && (assignedToCurrentUser || metadata?.permissionMap?.canAssignTickets);

  const acknowledgedSummary = useMemo(() => {
    if (!ticket?.acknowledged_by) return null;
    const { first_name: firstName, last_name: lastName, username } = ticket.acknowledged_by;
    const displayName = [firstName, lastName].filter(Boolean).join(" ") || username;
    return `${displayName} · ${moment(ticket.acknowledged_at).format("DD/MM/YYYY HH:mm")}`;
  }, [ticket]);

  if (!ticket) {
    return (
      <div className="ticket-detail">
        <div className="empty-state">
          <p>Seleziona un ticket per visualizzarne i dettagli.</p>
        </div>
      </div>
    );
  }

  const handleFormChange = (field, value) => {
    setFormState((prev) => ({ ...prev, [field]: value }));
  };

  const handleAckChange = (value) => {
    setFormError(null);
    setFormState((prev) => ({ ...prev, ackDueDate: value, ackDirty: true }));
  };

  const closeConfirmation = () => {
    setConfirmation({
      open: false,
      title: "",
      message: "",
      confirmLabel: "",
      onConfirm: null,
      onError: null,
    });
  };

  const parseApiError = (error) => {
    const responseData = error?.response?.data;
    if (typeof responseData === "string") return responseData;
    if (Array.isArray(responseData)) return responseData.join(" ");
    if (responseData && typeof responseData === "object") {
      const firstKey = Object.keys(responseData)[0];
      const message = responseData[firstKey];
      return Array.isArray(message) ? message.join(" ") : String(message);
    }
    return "Si è verificato un errore. Riprova.";
  };

  const handleAckConfirm = () => {
    if (!ticket?.due_date) return;
    setConfirmation({
      open: true,
      title: "Conferma scadenza",
      message: `Confermi la scadenza proposta per il ${moment(ticket.due_date).format("DD/MM/YYYY HH:mm")}?`,
      confirmLabel: "Conferma scadenza",
      onConfirm: () => handleAckChange(formatDateTime(ticket.due_date)),
      onError: null,
    });
  };

  const handleUpdate = (event) => {
    event.preventDefault();
    if (ackPending && !formState.ackDirty) {
      setFormError("Conferma la scadenza prima di aggiornare il ticket.");
      return;
    }
    setFormError(null);

    const payload = {
      status: formState.status,
      notes: formState.notes,
      due_date: formState.dueDate ? moment(formState.dueDate).toISOString() : "",
      deadline_justification: formState.deadlineJustification,
      completion_photo: formState.completionPhoto,
    };

    if (formState.ackDirty) {
      payload.acknowledged_due_date = formState.ackDueDate
        ? moment(formState.ackDueDate).toISOString()
        : "";
    }

    setConfirmation({
      open: true,
      title: "Salva modifiche",
      message: "Confermi l'aggiornamento del ticket con le modifiche effettuate?",
      confirmLabel: "Salva",
      onConfirm: async () => {
        setIsSubmitting(true);
        try {
          await onUpdate(payload);
          setFormState((prev) => ({
            ...prev,
            completionPhoto: null,
            deadlineJustification: "",
            ackDirty: false,
          }));
        } finally {
          setIsSubmitting(false);
        }
      },
      onError: (error) => {
        setFormError(parseApiError(error));
      },
    });
  };

  const handleClaimTicket = () => {
    if (!onClaim || !canClaimTicket) return;
    setConfirmation({
      open: true,
      title: "Prendi in carico",
      message: "Vuoi prendere in carico questo ticket?",
      confirmLabel: "Prendi in carico",
      onConfirm: async () => {
        await onClaim();
      },
      onError: null,
    });
  };

  const handleReleaseTicket = () => {
    if (!onRelease || !canReleaseTicket) return;
    setConfirmation({
      open: true,
      title: "Rilascia ticket",
      message: "Vuoi rilasciare questo ticket per renderlo nuovamente disponibile?",
      confirmLabel: "Rilascia",
      onConfirm: async () => {
        await onRelease();
      },
      onError: null,
    });
  };

  const handleExtendSubmit = (event) => {
    event.preventDefault();
    if (!onExtendDeadline) return;
    if (!extensionState.dueDate || !extensionState.justification.trim()) {
      setExtensionState((prev) => ({ ...prev, error: "Specifica nuova data e motivazione." }));
      return;
    }
    setExtensionState((prev) => ({ ...prev, error: "" }));

    const newDueDate = moment(extensionState.dueDate).format("DD/MM/YYYY HH:mm");

    setConfirmation({
      open: true,
      title: "Richiedi proroga",
      message: `Vuoi richiedere la proroga della scadenza al ${newDueDate}?`,
      confirmLabel: "Invia richiesta",
      onConfirm: async () => {
        setExtensionState((prev) => ({ ...prev, submitting: true }));
        try {
          await onExtendDeadline({
            due_date: moment(extensionState.dueDate).toISOString(),
            justification: extensionState.justification,
          });
          setExtensionState({ dueDate: "", justification: "", error: "", submitting: false });
        } catch (error) {
          const message = parseApiError(error) || "Impossibile richiedere la proroga.";
          setExtensionState((prev) => ({ ...prev, error: message, submitting: false }));
          throw error;
        }
      },
      onError: () => {},
    });
  };

  const handleConfirmDialogConfirm = async () => {
    if (!confirmation.open) return;
    const { onConfirm, onError } = confirmation;
    if (!onConfirm) {
      closeConfirmation();
      return;
    }
    setConfirmProcessing(true);
    try {
      await onConfirm();
      closeConfirmation();
    } catch (error) {
      if (onError) onError(error);
      closeConfirmation();
    } finally {
      setConfirmProcessing(false);
    }
  };

  const handleConfirmDialogCancel = () => {
    if (confirmProcessing) return;
    closeConfirmation();
  };

  const handleCommentSubmit = async (event) => {
    event.preventDefault();
    if (!commentState.comment && !commentState.attachment) {
      return;
    }
    setIsCommentSubmitting(true);
    try {
      await onAddComment({
        comment: commentState.comment,
        attachment: commentState.attachment,
      });
      setCommentState({ comment: "", attachment: null });
    } finally {
      setIsCommentSubmitting(false);
    }
  };

  return (
    <div className={`ticket-detail ${isCompact ? "ticket-detail--compact" : ""}`}>
      <header className="ticket-detail__header">
        <div>
          <h3>#{ticket.id} • {ticket.title}</h3>
          <div className="ticket-card__meta">
            <span className={`badge badge--priority-${ticket.priority}`}>{priorityLabels[ticket.priority] || ticket.priority}</span>
            <span>{ticket.resort?.name}</span>
            {ticket.room && <span>Camera {ticket.room.name}</span>}
          </div>
          <p className="text-muted small">Creato {moment(ticket.created_at).fromNow()} da {ticket.created_by?.username}</p>
        </div>
        {onClose && (
          <button type="button" className="maintenance-btn maintenance-btn--ghost" onClick={onClose}>
            <span className="visually-hidden">Chiudi dettaglio ticket</span>
            <i className="fa-solid fa-xmark" aria-hidden="true" />
          </button>
        )}
      </header>

      <div className="ticket-detail__assignment-bar">
        {ticket.assigned_to ? (
          <div className="ticket-detail__assignment-status">
            <i className="fa-solid fa-user-check" aria-hidden="true" />
            <span>
              Preso in carico da {assignedToCurrentUser ? "te" : assignedDisplayName}
              {ticket.claimed_at && ` • ${moment(ticket.claimed_at).fromNow()}`}
            </span>
            {canReleaseTicket && (
              <button type="button" className="maintenance-btn maintenance-btn--ghost" onClick={handleReleaseTicket}>
                <i className="fa-solid fa-share-from-square" aria-hidden="true" /> Rilascia ticket
              </button>
            )}
          </div>
        ) : (
          <div className="ticket-detail__assignment-status ticket-detail__assignment-status--free">
            <i className="fa-solid fa-circle-dot" aria-hidden="true" /> Ticket non assegnato
            {canClaimTicket ? (
              <button type="button" className="maintenance-btn" onClick={handleClaimTicket}>
                <i className="fa-solid fa-handshake-angle" aria-hidden="true" /> Prendi in carico
              </button>
            ) : (
              <span className="text-muted small">In attesa che un manutentore lo prenda in carico.</span>
            )}
          </div>
        )}
      </div>

      <section className="ticket-detail__section">
        <div className="ticket-detail__section-header">
          <h4>Dettagli</h4>
        </div>
        <p>{ticket.description}</p>
        {ticket.attachment && (
          <a className="maintenance-btn maintenance-btn--outline" href={ticket.attachment} target="_blank" rel="noreferrer">
            <i className="fa-solid fa-paperclip" /> Apri allegato
          </a>
        )}
        {ticket.completion_photo && (
          <div>
            <p className="fw-semibold mt-3">Foto del lavoro finito</p>
            <img src={ticket.completion_photo} alt="Foto completamento" style={{ maxWidth: "100%", borderRadius: "12px" }} />
          </div>
        )}
      </section>

      <section className="ticket-detail__section">
        <div className="ticket-detail__section-header">
          <h4>Aggiorna ticket</h4>
        </div>
        {formError && <div className="alert alert-danger">{formError}</div>}
        {ackPending && (
          <div className="acknowledgement-callout">
            <div>
              <strong>Conferma la scadenza concordata</strong>
              <p className="mb-0">
                Per chiudere o avanzare il ticket è necessario confermare la scadenza impostata per il {" "}
                {moment(ticket.due_date).format("DD/MM/YYYY HH:mm")}.
              </p>
            </div>
            <button
              type="button"
              className="maintenance-btn maintenance-btn--outline"
              onClick={handleAckConfirm}
            >
              Conferma {moment(ticket.due_date).format("DD/MM/YYYY HH:mm")}
            </button>
          </div>
        )}
        <form className="ticket-form" onSubmit={handleUpdate}>
          <div className="ticket-form__grid">
            <div className="ticket-form__field">
              <label htmlFor="ticket-status">Stato</label>
              <select
                id="ticket-status"
                value={formState.status}
                onChange={(event) => handleFormChange("status", event.target.value)}
              >
                {statuses.map((status) => (
                  <option key={status.value} value={status.value}>{status.label}</option>
                ))}
              </select>
            </div>
            <div className="ticket-form__field">
              <label htmlFor="ticket-due">Scadenza</label>
              <input
                id="ticket-due"
                type="datetime-local"
                value={formState.dueDate}
                onChange={(event) => handleFormChange("dueDate", event.target.value)}
                disabled={!canEditDeadline}
              />
            </div>
          </div>
          <div className="ticket-form__grid">
            <div className="ticket-form__field">
              <label htmlFor="ticket-ack">Scadenza confermata</label>
              <input
                id="ticket-ack"
                type="datetime-local"
                value={formState.ackDueDate || ""}
                onChange={(event) => handleAckChange(event.target.value)}
                disabled={!ackPending}
              />
              {acknowledgedSummary && !ackPending && (
                <small className="text-muted">Confermata da {acknowledgedSummary}</small>
              )}
              {ackPending && (
                <small className="text-muted">Conferma la scadenza per salvare le modifiche.</small>
              )}
            </div>
            <div className="ticket-form__field">
              <label htmlFor="ticket-photo">Foto lavoro completato</label>
              <input
                id="ticket-photo"
                type="file"
                accept="image/*"
                onChange={(event) => handleFormChange("completionPhoto", event.target.files?.[0] || null)}
              />
            </div>
          </div>
          <div className="ticket-form__field">
            <label htmlFor="ticket-notes">Note interne</label>
            <textarea
              id="ticket-notes"
              rows={3}
              value={formState.notes}
              onChange={(event) => handleFormChange("notes", event.target.value)}
            />
          </div>
          {!canEditDeadline && (
            <div className="ticket-form__field">
              <label htmlFor="deadline-justification">Motivazione proroga</label>
              <textarea
                id="deadline-justification"
                rows={2}
                value={formState.deadlineJustification}
                onChange={(event) => handleFormChange("deadlineJustification", event.target.value)}
                placeholder="Obbligatoria per richiedere una proroga"
              />
            </div>
          )}
          <div className="ticket-form__footer">
            <button type="submit" className="maintenance-btn" disabled={isSubmitting}>
              {isSubmitting ? "Salvataggio..." : "Salva modifiche"}
            </button>
          </div>
        </form>
      </section>

      <section className="ticket-detail__section">
        <div className="ticket-detail__section-header">
          <h4>Richiedi proroga</h4>
        </div>
        {extensionState.error && <div className="alert alert-danger">{extensionState.error}</div>}
        <form className="ticket-form" onSubmit={handleExtendSubmit}>
          <div className="ticket-form__grid">
            <div className="ticket-form__field">
              <label htmlFor="extend-due">Nuova scadenza</label>
              <input
                id="extend-due"
                type="datetime-local"
                value={extensionState.dueDate}
                onChange={(event) => setExtensionState((prev) => ({ ...prev, dueDate: event.target.value }))}
                required
                disabled={!ticket?.due_date}
              />
            </div>
            <div className="ticket-form__field">
              <label htmlFor="extend-justification">Motivazione</label>
              <textarea
                id="extend-justification"
                rows={2}
                value={extensionState.justification}
                onChange={(event) => setExtensionState((prev) => ({ ...prev, justification: event.target.value }))}
                placeholder="Spiega perché richiedi più tempo"
                required
              />
            </div>
          </div>
          <div className="ticket-form__footer ticket-form__footer--inline">
            <button
              type="submit"
              className="maintenance-btn maintenance-btn--outline"
              disabled={extensionState.submitting || !ticket?.due_date}
            >
              {extensionState.submitting ? "Invio richiesta..." : "Invia richiesta di proroga"}
            </button>
          </div>
          {!ticket?.due_date && (
            <small className="text-muted">Imposta prima una scadenza per poter richiedere una proroga.</small>
          )}
        </form>
      </section>

      <section className="ticket-detail__section">
        <div className="ticket-detail__section-header">
          <h4>Commenti</h4>
        </div>
        <div className="comment-list">
          {(ticket.comments || []).map((comment) => (
            <div key={comment.id} className="comment-item">
              <div className="comment-item__meta">
                <span>{comment.author?.username || "Anonimo"}</span>
                <span>{moment(comment.created_at).fromNow()}</span>
              </div>
              {comment.comment && <p className="mb-1">{comment.comment}</p>}
              {comment.attachment && (
                <a href={comment.attachment} target="_blank" rel="noreferrer" className="maintenance-btn maintenance-btn--outline">
                  <i className="fa-solid fa-paperclip" /> Apri allegato
                </a>
              )}
            </div>
          ))}
          {(!ticket.comments || ticket.comments.length === 0) && (
            <p className="text-muted">Nessun commento presente.</p>
          )}
        </div>

        <form className="ticket-form ticket-form--inline" onSubmit={handleCommentSubmit}>
          <div className="ticket-form__field">
            <label htmlFor="comment-text">Aggiungi commento</label>
            <textarea
              id="comment-text"
              rows={2}
              value={commentState.comment}
              onChange={(event) => setCommentState((prev) => ({ ...prev, comment: event.target.value }))}
              placeholder="Aggiorna il team sullo stato del ticket"
            />
          </div>
          <div className="ticket-form__field">
            <label htmlFor="comment-attachment">Allega file</label>
            <input
              id="comment-attachment"
              type="file"
              onChange={(event) => setCommentState((prev) => ({ ...prev, attachment: event.target.files?.[0] || null }))}
            />
          </div>
          <div className="ticket-form__footer ticket-form__footer--inline">
            <button type="submit" className="maintenance-btn" disabled={isCommentSubmitting}>
              {isCommentSubmitting ? "Invio..." : "Invia"}
            </button>
          </div>
        </form>
      </section>

      <section className="ticket-detail__section">
        <div className="ticket-detail__section-header">
          <h4>Registro attività</h4>
        </div>
        {history.length === 0 ? (
          <p className="text-muted">Ancora nessuna attività registrata.</p>
        ) : (
          <ul className="ticket-history">
            {history.map((entry, index) => (
              <li key={`${entry.timestamp}-${index}`}>
                <span className="ticket-history__timestamp">{moment(entry.timestamp).format("DD/MM/YYYY HH:mm")}</span>
                <span className="ticket-history__actor">{entry.actor}</span>
                <span className="ticket-history__summary">{entry.summary}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <ConfirmationDialog
        open={confirmation.open}
        title={confirmation.title}
        message={confirmation.message}
        confirmLabel={confirmation.confirmLabel}
        onConfirm={handleConfirmDialogConfirm}
        onCancel={handleConfirmDialogCancel}
        confirmDisabled={confirmProcessing}
      />
    </div>
  );
}

TicketDetail.propTypes = {
  ticket: PropTypes.shape({
    id: PropTypes.number,
    title: PropTypes.string,
    status: PropTypes.string,
    notes: PropTypes.string,
    due_date: PropTypes.string,
    acknowledged_due_date: PropTypes.string,
    acknowledged_by: PropTypes.object,
    acknowledged_at: PropTypes.string,
    resort: PropTypes.shape({ name: PropTypes.string }),
    room: PropTypes.shape({ name: PropTypes.string }),
    priority: PropTypes.string,
    description: PropTypes.string,
    history: PropTypes.array,
    comments: PropTypes.array,
    assigned_to: PropTypes.shape({ id: PropTypes.number, first_name: PropTypes.string, last_name: PropTypes.string, username: PropTypes.string }),
    created_at: PropTypes.string,
    created_by: PropTypes.shape({ username: PropTypes.string }),
    claimed_at: PropTypes.string,
    attachment: PropTypes.string,
    completion_photo: PropTypes.string,
  }),
  metadata: PropTypes.shape({
    statuses: PropTypes.array,
    maintainers: PropTypes.array,
    priorities: PropTypes.array,
  }),
  canEditDeadline: PropTypes.bool,
  onUpdate: PropTypes.func,
  onAddComment: PropTypes.func,
  onClaim: PropTypes.func,
  onRelease: PropTypes.func,
  canClaim: PropTypes.bool,
  currentUserId: PropTypes.number,
  onExtendDeadline: PropTypes.func,
  isCompact: PropTypes.bool,
  onClose: PropTypes.func,
};

TicketDetail.defaultProps = {
  ticket: null,
  metadata: { statuses: [], maintainers: [], priorities: [] },
  canEditDeadline: false,
  onUpdate: () => {},
  onAddComment: () => {},
  onClaim: undefined,
  onRelease: undefined,
  canClaim: false,
  currentUserId: 0,
  onExtendDeadline: undefined,
  isCompact: false,
  onClose: undefined,
};
