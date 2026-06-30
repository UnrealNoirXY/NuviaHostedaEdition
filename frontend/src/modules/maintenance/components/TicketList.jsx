import React, { useMemo, useState } from "react";
import PropTypes from "prop-types";
import moment from "moment";
import SkeletonPlaceholder from "./SkeletonPlaceholder";

moment.locale("it");

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

const slaLabels = {
  ok: "In SLA",
  at_risk: "A rischio",
  breached: "Violato",
};

function getDueIndicator(ticket) {
  if (!ticket.due_date) {
    return { label: "Senza scadenza", tone: "ok" };
  }
  const due = moment(ticket.due_date);
  const now = moment();
  const diffHours = due.diff(now, "hours", true);
  if (diffHours < 0) {
    return { label: `Scaduto da ${due.fromNow(true)}`, tone: "critical" };
  }
  if (diffHours <= 3) {
    return { label: `Scade in ${due.fromNow(true)}`, tone: "warning" };
  }
  return { label: `Scade ${due.fromNow()}`, tone: "ok" };
}

export default function TicketList({
  tickets,
  selectedId,
  onSelect,
  filters,
  onFilterChange,
  isLoading,
  error,
  canQuickClaim,
  canManageAssignments,
  onQuickClaim,
  onQuickRelease,
  currentUserId,
  isCompact,
  metadata,
  onResetFilters,
  presets,
  onSavePreset,
  onApplyPreset,
  onDeletePreset,
}) {
  const [showAdvancedFilters, setShowAdvancedFilters] = useState(false);
  const [presetName, setPresetName] = useState("");
  const [selectedPresetId, setSelectedPresetId] = useState("");

  const filteredTickets = useMemo(() => {
    const now = moment();
    return tickets.filter((ticket) => {
      if (filters.status && ticket.status !== filters.status) return false;
      if (filters.priority && ticket.priority !== filters.priority) return false;
      if (filters.sla) {
        const ticketSla = ticket.sla_state || ticket.slaStatus || ticket.sla?.state || "";
        if (ticketSla !== filters.sla) return false;
      }
      if (filters.resorts.length) {
        const resortId = ticket.resort?.id ? String(ticket.resort.id) : "";
        if (!filters.resorts.includes(resortId)) return false;
      }
      if (filters.skills.length) {
        const ticketSkills = (ticket.skills || ticket.required_skills || []).map((skill) =>
          typeof skill === "object" ? String(skill.id ?? skill.code ?? skill.name ?? skill) : String(skill)
        );
        const hasAllSkills = filters.skills.every((skill) => ticketSkills.includes(String(skill)));
        if (!hasAllSkills) return false;
      }
      if (filters.tags.length) {
        const tagList = (ticket.tags || []).map((tag) => (typeof tag === "object" ? tag.name ?? tag.slug ?? tag : tag));
        const hasTags = filters.tags.every((tag) => tagList.map(String).includes(String(tag)));
        if (!hasTags) return false;
      }
      if (filters.due === "overdue") {
        if (!ticket.due_date || moment(ticket.due_date).isSameOrAfter(now)) return false;
      }
      if (filters.due === "soon") {
        if (!ticket.due_date) return false;
        const diffHours = moment(ticket.due_date).diff(now, "hours", true);
        if (diffHours < 0 || diffHours > 48) return false;
      }
      if (filters.ack === "pending" && !(ticket.due_date && !ticket.acknowledged_due_date)) {
        return false;
      }
      if (filters.assignment === "unassigned" && ticket.assigned_to) {
        return false;
      }
      if (filters.search) {
        const haystack = [
          ticket.title,
          ticket.description || "",
          ticket.resort?.name,
          ticket.room?.name,
          ticket.assigned_to?.username,
          (ticket.tags || []).map((tag) => (typeof tag === "object" ? tag.name : tag)).join(" "),
          (ticket.skills || []).map((skill) => (typeof skill === "object" ? skill.name : skill)).join(" "),
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();
        if (!haystack.includes(filters.search.toLowerCase())) return false;
      }
      return true;
    });
  }, [tickets, filters]);

  const toggleFilter = (field, value) => {
    const nextValue = filters[field] === value ? "" : value;
    onFilterChange({ ...filters, [field]: nextValue });
  };

  const handleMultiSelectChange = (event, field) => {
    const values = Array.from(event.target.selectedOptions).map((option) => option.value);
    onFilterChange({ ...filters, [field]: values });
  };

  const handlePresetSave = (event) => {
    event.preventDefault();
    onSavePreset(presetName);
    setPresetName("");
  };

  const handlePresetApply = (presetId) => {
    setSelectedPresetId(presetId);
    if (presetId) {
      onApplyPreset(presetId);
    }
  };

  return (
    <div className={`ticket-list ${isCompact ? "ticket-list--compact" : ""}`}>
      <div className="ticket-list__filters" role="search">
        <div className="ticket-list__filters-main">
          <label className="visually-hidden" htmlFor="maintenance-search">
            Ricerca full-text ticket
          </label>
          <input
            id="maintenance-search"
            className="form-control"
            placeholder="Cerca titolo, descrizione, tag o stanza"
            value={filters.search}
            onChange={(event) => onFilterChange({ ...filters, search: event.target.value })}
            aria-label="Ricerca full-text ticket"
          />
          <label className="visually-hidden" htmlFor="maintenance-status-filter">
            Filtra per stato ticket
          </label>
          <select
            id="maintenance-status-filter"
            className="form-select"
            value={filters.status}
            onChange={(event) => onFilterChange({ ...filters, status: event.target.value })}
          >
            <option value="">Stato</option>
            {Object.entries(statusLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <label className="visually-hidden" htmlFor="maintenance-priority-filter">
            Filtra per priorità ticket
          </label>
          <select
            id="maintenance-priority-filter"
            className="form-select"
            value={filters.priority}
            onChange={(event) => onFilterChange({ ...filters, priority: event.target.value })}
          >
            <option value="">Priorità</option>
            <option value="low">Bassa</option>
            <option value="medium">Media</option>
            <option value="high">Alta</option>
            <option value="urgent">Urgente</option>
          </select>
          <button
            type="button"
            className="maintenance-btn maintenance-btn--ghost ticket-list__advanced-toggle"
            onClick={() => setShowAdvancedFilters((prev) => !prev)}
            aria-expanded={showAdvancedFilters}
          >
            <i className="fa-solid fa-sliders" aria-hidden="true" /> Filtri avanzati
          </button>
        </div>

        {showAdvancedFilters && (
          <div className="ticket-list__filters-advanced" role="region" aria-label="Filtri avanzati">
            <div className="ticket-list__filter-group">
              <label htmlFor="maintenance-resort-filter">Resort</label>
              <select
                id="maintenance-resort-filter"
                className="form-select"
                multiple
                value={filters.resorts}
                onChange={(event) => handleMultiSelectChange(event, "resorts")}
              >
                {metadata.resorts.map((resort) => (
                  <option key={resort.id} value={String(resort.id)}>
                    {resort.name}
                  </option>
                ))}
              </select>
              <p className="ticket-list__filter-hint">Seleziona uno o più resort</p>
            </div>
            <div className="ticket-list__filter-group">
              <label htmlFor="maintenance-sla-filter">Stato SLA</label>
              <select
                id="maintenance-sla-filter"
                className="form-select"
                value={filters.sla}
                onChange={(event) => onFilterChange({ ...filters, sla: event.target.value })}
              >
                <option value="">Tutti</option>
                {(metadata.slaStates.length ? metadata.slaStates : Object.keys(slaLabels)).map((state) => (
                  <option key={state} value={state}>
                    {slaLabels[state] || state}
                  </option>
                ))}
              </select>
            </div>
            <div className="ticket-list__filter-group">
              <label htmlFor="maintenance-skills-filter">Skill necessarie</label>
              <select
                id="maintenance-skills-filter"
                className="form-select"
                multiple
                value={filters.skills}
                onChange={(event) => handleMultiSelectChange(event, "skills")}
              >
                {metadata.skills.map((skill) => (
                  <option key={skill.id ?? skill.code ?? skill} value={String(skill.id ?? skill.code ?? skill)}>
                    {skill.name ?? skill.label ?? skill}
                  </option>
                ))}
              </select>
              <p className="ticket-list__filter-hint">Filtra ticket che richiedono tutte le skill selezionate.</p>
            </div>
            <div className="ticket-list__filter-group">
              <label htmlFor="maintenance-tags-filter">Tag</label>
              <select
                id="maintenance-tags-filter"
                className="form-select"
                multiple
                value={filters.tags}
                onChange={(event) => handleMultiSelectChange(event, "tags")}
              >
                {metadata.tags.map((tag) => (
                  <option key={tag.id ?? tag.slug ?? tag} value={String(tag.id ?? tag.slug ?? tag)}>
                    {tag.name ?? tag.label ?? tag}
                  </option>
                ))}
              </select>
              <p className="ticket-list__filter-hint">Usa i tag per isolare componenti o reparti.</p>
            </div>

            <div className="ticket-list__presets" role="form" aria-label="Gestione preset filtri">
              <div className="ticket-list__preset-row">
                <label htmlFor="maintenance-preset-select">Preset salvati</label>
                <div className="ticket-list__preset-actions">
                  <select
                    id="maintenance-preset-select"
                    className="form-select"
                    value={selectedPresetId}
                    onChange={(event) => handlePresetApply(event.target.value)}
                  >
                    <option value="">Nessun preset</option>
                    {presets.map((preset) => (
                      <option key={preset.id} value={preset.id}>
                        {preset.name}
                      </option>
                    ))}
                  </select>
                  <button
                    type="button"
                    className="maintenance-btn maintenance-btn--ghost"
                    disabled={!selectedPresetId}
                    onClick={() => {
                      onDeletePreset(selectedPresetId);
                      setSelectedPresetId("");
                    }}
                    aria-label="Elimina preset selezionato"
                  >
                    <i className="fa-solid fa-trash" aria-hidden="true" />
                  </button>
                </div>
              </div>
              <div className="ticket-list__preset-row">
                <label htmlFor="maintenance-preset-name">Salva preset</label>
                <div className="ticket-list__preset-actions">
                  <input
                    id="maintenance-preset-name"
                    className="form-control"
                    placeholder="Nome preset"
                    value={presetName}
                    onChange={(event) => setPresetName(event.target.value)}
                  />
                  <button type="button" className="maintenance-btn" onClick={handlePresetSave} disabled={!presetName.trim()}>
                    <i className="fa-solid fa-floppy-disk" aria-hidden="true" />
                    Salva
                  </button>
                  <button type="button" className="maintenance-btn maintenance-btn--ghost" onClick={onResetFilters}>
                    <i className="fa-solid fa-rotate-left" aria-hidden="true" />
                    Reset
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="ticket-list__quick-filters" role="toolbar" aria-label="Filtri rapidi">
        <button
          type="button"
          className={`chip ${filters.due === "overdue" ? "chip--active" : ""}`}
          onClick={() => toggleFilter("due", "overdue")}
          aria-pressed={filters.due === "overdue"}
        >
          <i className="fa-solid fa-triangle-exclamation" aria-hidden="true" /> Scaduti
        </button>
        <button
          type="button"
          className={`chip ${filters.due === "soon" ? "chip--active" : ""}`}
          onClick={() => toggleFilter("due", "soon")}
          aria-pressed={filters.due === "soon"}
        >
          <i className="fa-regular fa-clock" aria-hidden="true" /> In scadenza 48h
        </button>
        <button
          type="button"
          className={`chip ${filters.ack === "pending" ? "chip--active" : ""}`}
          onClick={() => toggleFilter("ack", "pending")}
          aria-pressed={filters.ack === "pending"}
        >
          <i className="fa-solid fa-user-clock" aria-hidden="true" /> Conferma richiesta
        </button>
        <button
          type="button"
          className={`chip ${filters.assignment === "unassigned" ? "chip--active" : ""}`}
          onClick={() => toggleFilter("assignment", "unassigned")}
          aria-pressed={filters.assignment === "unassigned"}
        >
          <i className="fa-solid fa-people-group" aria-hidden="true" /> Ticket liberi
        </button>
      </div>

      {error && !isLoading && (
        <div className="maintenance-alert maintenance-alert--inline" role="status">
          <i className="fa-solid fa-circle-info" aria-hidden="true" /> {error}
        </div>
      )}

      {isLoading && (
        <div className="ticket-list__skeleton" role="status" aria-label="Caricamento ticket">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={String(index)} className="ticket-card ticket-card--skeleton" aria-hidden="true">
              <SkeletonPlaceholder lines={4} />
            </div>
          ))}
        </div>
      )}

      {!isLoading && filteredTickets.length === 0 ? (
        <div className="empty-state">
          <p>Nessun ticket corrisponde ai filtri selezionati.</p>
        </div>
      ) : null}

      {!isLoading && filteredTickets.length > 0 && (
        <div className="ticket-list__items">
          {filteredTickets.map((ticket) => {
            const dueIndicator = getDueIndicator(ticket);
            const dueTimeLabel = ticket.due_date ? moment(ticket.due_date).format("HH:mm") : "—";
            const ackPending = Boolean(ticket.due_date) && !ticket.acknowledged_due_date;
            const assignedName = ticket.assigned_to
              ? [ticket.assigned_to.first_name, ticket.assigned_to.last_name]
                  .filter(Boolean)
                  .join(" ") || ticket.assigned_to.username
              : null;
            const isAssignedToCurrentUser = Boolean(ticket.assigned_to?.id) && ticket.assigned_to.id === currentUserId;
            const showClaim = canQuickClaim && !ticket.assigned_to;
            const showRelease =
              Boolean(ticket.assigned_to) && (isAssignedToCurrentUser || canManageAssignments);

            return (
              <article
                key={ticket.id}
                className={`ticket-card ${ackPending ? "ticket-card--ack-pending" : ""} ${selectedId === ticket.id ? "ticket-card--selected" : ""}`}
                role="button"
                tabIndex={0}
                onClick={() => onSelect(ticket.id)}
                onKeyPress={(event) => event.key === "Enter" && onSelect(ticket.id)}
                aria-pressed={selectedId === ticket.id}
              >
                {isCompact && (
                  <div className="ticket-card__time">
                    <span>{dueTimeLabel}</span>
                    {ticket.due_date && <small>{moment(ticket.due_date).format("DD/MM")}</small>}
                  </div>
                )}
                <header className="ticket-card__header">
                  <div className="ticket-card__title">
                    <span className="ticket-card__id">#{ticket.id}</span>
                    <span>{ticket.title}</span>
                  </div>
                  <div className="ticket-card__header-actions">
                    <span className={`badge badge--status-${ticket.status}`}>
                      {statusLabels[ticket.status] || ticket.status}
                    </span>
                    {showClaim && (
                      <button
                        type="button"
                        className="ticket-card__action"
                        onClick={(event) => {
                          event.stopPropagation();
                          onQuickClaim(ticket.id);
                        }}
                      >
                        <i className="fa-solid fa-handshake-angle" aria-hidden="true" /> Prendi
                      </button>
                    )}
                    {showRelease && (
                      <button
                        type="button"
                        className="ticket-card__action ticket-card__action--secondary"
                        onClick={(event) => {
                          event.stopPropagation();
                          onQuickRelease(ticket.id);
                        }}
                      >
                        <i className="fa-solid fa-share-from-square" aria-hidden="true" /> Rilascia
                      </button>
                    )}
                  </div>
                </header>
                <div className="ticket-card__meta">
                  <span className={`badge badge--priority-${ticket.priority}`}>
                    {priorityLabels[ticket.priority] || ticket.priority}
                  </span>
                  {!isCompact && <span>{ticket.resort?.name || "-"}</span>}
                  {!isCompact && ticket.room && <span>Camera {ticket.room.name}</span>}
                  {isCompact && (
                    <span className={`badge badge--status-${ticket.status}`}>
                      {statusLabels[ticket.status] || ticket.status}
                    </span>
                  )}
                </div>
                {!isCompact && (
                  <div className="ticket-card__assignment">
                    {ticket.assigned_to ? (
                      <span>
                        <i className="fa-solid fa-user-check" aria-hidden="true" /> {assignedName}
                        {ticket.claimed_at && (
                          <span className="ticket-card__assignment-meta">· presa {moment(ticket.claimed_at).fromNow()}</span>
                        )}
                      </span>
                    ) : (
                      <span className="ticket-card__assignment-free">
                        <i className="fa-solid fa-circle-dot" aria-hidden="true" /> Non assegnato
                      </span>
                    )}
                  </div>
                )}
                <div className={`due-indicator due-indicator--${dueIndicator.tone}`}>
                  <i className="fa-regular fa-clock" /> {dueIndicator.label}
                </div>
                {ticket.due_date && (
                  <div
                    className={`ticket-card__ack-status ${ackPending ? "" : "ticket-card__ack-status--ok"}`}
                  >
                    <i className="fa-solid fa-user-check" />
                    {ackPending ? "In attesa conferma manutentore" : "Scadenza confermata"}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

TicketList.propTypes = {
  tickets: PropTypes.arrayOf(PropTypes.object).isRequired,
  selectedId: PropTypes.number,
  onSelect: PropTypes.func.isRequired,
  filters: PropTypes.shape({
    search: PropTypes.string,
    status: PropTypes.string,
    priority: PropTypes.string,
    due: PropTypes.string,
    ack: PropTypes.string,
    assignment: PropTypes.string,
    resorts: PropTypes.arrayOf(PropTypes.string),
    sla: PropTypes.string,
    skills: PropTypes.arrayOf(PropTypes.string),
    tags: PropTypes.arrayOf(PropTypes.string),
  }).isRequired,
  onFilterChange: PropTypes.func.isRequired,
  onResetFilters: PropTypes.func,
  isLoading: PropTypes.bool,
  error: PropTypes.string,
  canQuickClaim: PropTypes.bool,
  onQuickClaim: PropTypes.func,
  onQuickRelease: PropTypes.func,
  canManageAssignments: PropTypes.bool,
  currentUserId: PropTypes.number,
  isCompact: PropTypes.bool,
  metadata: PropTypes.shape({
    resorts: PropTypes.arrayOf(PropTypes.shape({ id: PropTypes.oneOfType([PropTypes.number, PropTypes.string]), name: PropTypes.string })),
    slaStates: PropTypes.arrayOf(PropTypes.string),
    skills: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])),
    tags: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])),
  }),
  presets: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      name: PropTypes.string,
      filters: PropTypes.object,
    })
  ),
  onSavePreset: PropTypes.func,
  onApplyPreset: PropTypes.func,
  onDeletePreset: PropTypes.func,
};

TicketList.defaultProps = {
  selectedId: null,
  onResetFilters: () => {},
  isLoading: false,
  error: "",
  canQuickClaim: false,
  onQuickClaim: () => {},
  onQuickRelease: () => {},
  canManageAssignments: false,
  currentUserId: 0,
  isCompact: false,
  metadata: { resorts: [], slaStates: [], skills: [], tags: [] },
  presets: [],
  onSavePreset: () => {},
  onApplyPreset: () => {},
  onDeletePreset: () => {},
};
