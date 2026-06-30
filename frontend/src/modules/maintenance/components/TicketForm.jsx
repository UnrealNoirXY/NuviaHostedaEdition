import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";
import ConfirmationDialog from "./ConfirmationDialog";

const priorityOptions = [
  { value: "low", label: "Bassa" },
  { value: "medium", label: "Media" },
  { value: "high", label: "Alta" },
  { value: "urgent", label: "Urgente" },
];

const defaultConfirmationState = {
  open: false,
  title: "",
  message: "",
};

export default function TicketForm({ metadata, onSubmit, isSubmitting }) {
  const [formState, setFormState] = useState({
    title: "",
    description: "",
    resort: "",
    room: "",
    priority: "medium",
    assigned_to: "",
    notification_mode: "assigned",
    notify_maintainers: [],
    due_date: "",
    attachment: null,
    confirmed: false,
  });
  const [formError, setFormError] = useState("");
  const [confirmation, setConfirmation] = useState(defaultConfirmationState);
  const [confirmProcessing, setConfirmProcessing] = useState(false);

  const rooms = useMemo(() => {
    if (!formState.resort) return metadata.rooms;
    return metadata.rooms.filter((room) => `${room.resort}` === `${formState.resort}`);
  }, [metadata.rooms, formState.resort]);

  const maintainers = useMemo(() => {
    if (!formState.resort) return metadata.maintainers;
    return metadata.maintainers.filter((maint) => `${maint.resort}` === `${formState.resort}`);
  }, [metadata.maintainers, formState.resort]);

  const handleChange = (field, value) => {
    setFormState((prev) => ({ ...prev, [field]: value }));
  };

  const resetForm = () => {
    setFormState({
      title: "",
      description: "",
      resort: "",
      room: "",
      priority: "medium",
      assigned_to: "",
      notification_mode: "assigned",
      notify_maintainers: [],
      due_date: "",
      attachment: null,
      confirmed: false,
    });
    setFormError("");
  };

  const parseApiError = (error) => {
    const responseData = error?.response?.data;
    if (typeof responseData === "string") return responseData;
    if (Array.isArray(responseData)) return responseData.join(" ");
    if (responseData && typeof responseData === "object") {
      const firstKey = Object.keys(responseData)[0];
      const value = responseData[firstKey];
      return Array.isArray(value) ? value.join(" ") : String(value);
    }
    return "Impossibile creare il ticket. Riprova.";
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    setFormError("");

    if (!formState.confirmed) {
      setFormError("Conferma di aver verificato i dati prima di creare il ticket.");
      return;
    }

    if (formState.notification_mode === "assigned" && !formState.assigned_to) {
      setFormError("Seleziona un manutentore oppure scegli l'invio manuale ai manutentori in turno.");
      return;
    }

    if (formState.notification_mode === "selected" && formState.notify_maintainers.length === 0) {
      setFormError("Seleziona almeno un manutentore da notificare.");
      return;
    }

    const summary = [
      formState.due_date ? `Scadenza impostata: ${new Date(formState.due_date).toLocaleString()}` : "Scadenza non impostata",
      formState.assigned_to ? "Il ticket verrà assegnato subito." : "Il ticket resterà non assegnato finché qualcuno lo prende in carico.",
      formState.notification_mode === "assigned"
        ? "Notifica al manutentore assegnato."
        : `Notifica inviata a ${formState.notify_maintainers.length} manutentori selezionati.`,
    ]
      .filter(Boolean)
      .join("\n");

    setConfirmation({
      open: true,
      title: "Conferma creazione ticket",
      message: `Confermi la creazione del ticket con i dati inseriti?\n${summary}`,
      confirmLabel: "Crea ticket",
    });
  };

  const handleConfirmSubmit = async () => {
    setConfirmProcessing(true);
    try {
      await onSubmit({
        ...formState,
        due_date: formState.due_date,
        confirmed: true,
      });
      resetForm();
    } catch (error) {
      setFormError(parseApiError(error));
    } finally {
      setConfirmProcessing(false);
      setConfirmation(defaultConfirmationState);
    }
  };

  const handleCancelConfirmation = () => {
    if (confirmProcessing) return;
    setConfirmation(defaultConfirmationState);
  };

  return (
    <form className="ticket-form" onSubmit={handleSubmit}>
      <header className="ticket-form__header">
        <span className="ticket-form__eyebrow">Nuovo intervento</span>
        <div className="ticket-form__title">
          <h4>Crea nuovo ticket</h4>
          <p>Inserisci le informazioni necessarie per pianificare l'intervento di manutenzione.</p>
        </div>
      </header>
      {formError && <div className="ticket-form__alert">{formError}</div>}

      <section className="ticket-form__section">
        <h5>Dettagli intervento</h5>
        <div className="ticket-form__field ticket-form__field--full">
          <label htmlFor="ticket-title">Titolo</label>
          <input
            id="ticket-title"
            value={formState.title}
            onChange={(event) => handleChange("title", event.target.value)}
            placeholder="Es. Controllo condizionatore camera 108"
            required
          />
        </div>
        <div className="ticket-form__field ticket-form__field--full">
          <label htmlFor="ticket-description">Descrizione</label>
          <textarea
            id="ticket-description"
            rows={3}
            value={formState.description}
            onChange={(event) => handleChange("description", event.target.value)}
            placeholder="Descrivi attività, materiali necessari e contesto dell'intervento"
            required
          />
        </div>
      </section>

      <section className="ticket-form__section">
        <h5>Localizzazione e assegnazione</h5>
        <div className="ticket-form__grid">
          <div className="ticket-form__field">
            <label htmlFor="ticket-resort">Struttura</label>
            <select
              id="ticket-resort"
              value={formState.resort}
              onChange={(event) => {
                const resortValue = event.target.value;
                setFormState((prev) => ({
                  ...prev,
                  resort: resortValue,
                  room: "",
                  assigned_to: "",
                  notify_maintainers: [],
                }));
              }}
              required
            >
              <option value="">Seleziona struttura</option>
              {metadata.resorts.map((resort) => (
                <option key={resort.id} value={resort.id}>
                  {resort.name}
                </option>
              ))}
            </select>
          </div>
          <div className="ticket-form__field">
            <label htmlFor="ticket-room">Camera</label>
            <select
              id="ticket-room"
              value={formState.room}
              onChange={(event) => handleChange("room", event.target.value)}
            >
              <option value="">Non specificata</option>
              {rooms.map((room) => (
                <option key={room.id} value={room.id}>
                  {room.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="ticket-form__grid">
          <div className="ticket-form__field">
            <label htmlFor="ticket-priority">Priorità</label>
            <select
              id="ticket-priority"
              value={formState.priority}
              onChange={(event) => handleChange("priority", event.target.value)}
            >
              {priorityOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="ticket-form__field">
            <label htmlFor="ticket-assigned">Assegna a</label>
            <select
              id="ticket-assigned"
              value={formState.assigned_to}
              onChange={(event) => handleChange("assigned_to", event.target.value)}
            >
              <option value="">Non assegnato</option>
              {maintainers.map((maint) => (
                <option key={maint.id} value={maint.id}>
                  {maint.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="ticket-form__field ticket-form__field--full">
          <label>Notifiche manutentori</label>
          <div className="ticket-form__toggle">
            <label className="ticket-form__toggle-option">
              <input
                type="radio"
                name="notification_mode"
                value="assigned"
                checked={formState.notification_mode === "assigned"}
                onChange={() =>
                  setFormState((prev) => ({
                    ...prev,
                    notification_mode: "assigned",
                    notify_maintainers: [],
                  }))
                }
              />
              <span className="ticket-form__toggle-text">Invia solo al manutentore assegnato</span>
            </label>
            <label className="ticket-form__toggle-option">
              <input
                type="radio"
                name="notification_mode"
                value="selected"
                checked={formState.notification_mode === "selected"}
                onChange={() => handleChange("notification_mode", "selected")}
              />
              <span className="ticket-form__toggle-text">Seleziona manutentori in turno</span>
            </label>
          </div>
          {formState.notification_mode === "selected" && (
            <select
              multiple
              value={formState.notify_maintainers}
              onChange={(event) => {
                const selected = Array.from(event.target.selectedOptions).map((option) => option.value);
                handleChange("notify_maintainers", selected);
              }}
            >
              {maintainers.map((maint) => (
                <option key={maint.id} value={maint.id}>
                  {maint.name}
                </option>
              ))}
            </select>
          )}
          <p className="ticket-form__hint">
            {formState.notification_mode === "assigned"
              ? "La comunicazione viene inviata solo al manutentore assegnato."
              : "Seleziona i manutentori che sono in turno per questa struttura."}
          </p>
        </div>
        <div className="ticket-form__grid ticket-form__grid--compact">
          {metadata.deadlinePrivileges && (
            <div className="ticket-form__field">
              <label htmlFor="ticket-due">Scadenza prevista</label>
              <input
                id="ticket-due"
                type="datetime-local"
                value={formState.due_date}
                onChange={(event) => handleChange("due_date", event.target.value)}
              />
            </div>
          )}
          <div className="ticket-form__field">
            <label htmlFor="ticket-attachment">Allegato</label>
            <input
              id="ticket-attachment"
              type="file"
              onChange={(event) => handleChange("attachment", event.target.files?.[0] || null)}
            />
          </div>
        </div>
      </section>

      <section className="ticket-form__section ticket-form__section--summary">
        <div className="ticket-form__summary">
          <div className="ticket-form__summary-header">
            <h5>Riepilogo dati inseriti</h5>
            <p>Controlla le informazioni prima di procedere con la creazione.</p>
          </div>
          <ul className="ticket-form__summary-list">
            <li>
              <span>Priorità</span>
              <strong>{priorityOptions.find((option) => option.value === formState.priority)?.label}</strong>
            </li>
            <li>
              <span>Struttura</span>
              <strong>
                {metadata.resorts.find((resort) => `${resort.id}` === `${formState.resort}`)?.name || "Non selezionata"}
              </strong>
            </li>
            <li>
              <span>Camera</span>
              <strong>{rooms.find((room) => `${room.id}` === `${formState.room}`)?.name || "Non specificata"}</strong>
            </li>
            <li>
              <span>Scadenza</span>
              <strong>{formState.due_date ? new Date(formState.due_date).toLocaleString() : "Non impostata"}</strong>
            </li>
            <li>
              <span>Assegnazione iniziale</span>
              <strong>{formState.assigned_to ? "Diretta" : "Collaborativa (ticket libero)"}</strong>
            </li>
            <li>
              <span>Notifiche</span>
              <strong>
                {formState.notification_mode === "assigned"
                  ? "Solo manutentore assegnato"
                  : `Manutentori selezionati (${formState.notify_maintainers.length})`}
              </strong>
            </li>
          </ul>
          <label className="ticket-form__confirm">
            <input
              type="checkbox"
              checked={formState.confirmed}
              onChange={(event) => handleChange("confirmed", event.target.checked)}
              required
            />
            <span>Ho verificato che le informazioni inserite sono corrette.</span>
          </label>
        </div>
      </section>

      <footer className="ticket-form__footer">
        <button type="submit" className="maintenance-btn" disabled={isSubmitting}>
          {isSubmitting ? "Creazione..." : "Crea ticket"}
        </button>
      </footer>

      <ConfirmationDialog
        open={confirmation.open}
        title={confirmation.title}
        message={confirmation.message || ""}
        confirmLabel={confirmation.confirmLabel || "Conferma"}
        cancelLabel="Annulla"
        onConfirm={handleConfirmSubmit}
        onCancel={handleCancelConfirmation}
        processing={confirmProcessing || isSubmitting}
      />
    </form>
  );
}

TicketForm.propTypes = {
  metadata: PropTypes.shape({
    resorts: PropTypes.array,
    rooms: PropTypes.array,
    maintainers: PropTypes.array,
    deadlinePrivileges: PropTypes.bool,
  }).isRequired,
  onSubmit: PropTypes.func.isRequired,
  isSubmitting: PropTypes.bool,
};

TicketForm.defaultProps = {
  isSubmitting: false,
};
