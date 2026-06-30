import React, { useCallback, useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";
import moment from "moment";
import { Calendar, momentLocalizer } from "react-big-calendar";
import "react-big-calendar/lib/css/react-big-calendar.css";

moment.locale("it");
const localizer = momentLocalizer(moment);

const statusColors = {
  open: "#2563eb",
  in_progress: "#f97316",
  resolved: "#10b981",
  closed: "#64748b",
  overdue: "#ef4444",
};

const priorityColors = {
  low: "#10b981",
  medium: "#facc15",
  high: "#f97316",
  urgent: "#ef4444",
};

const gradientForEvent = (event) => {
  const base = statusColors[event.status] || "#1d4ed8";
  const accent = priorityColors[event.priority] || "#1e293b";
  return `linear-gradient(135deg, ${base} 0%, ${accent} 100%)`;
};

function CalendarEvent({ event, onSelect, isMobile }) {
  const startTime = event.start ? moment(event.start).format("HH:mm") : "";
  const endTime = event.end ? moment(event.end).format("HH:mm") : "";

  const handleOpen = useCallback(
    (e) => {
      e.stopPropagation();
      if (onSelect) {
        onSelect(event);
      }
    },
    [event, onSelect]
  );

  return (
    <div
      className={`maintenance-calendar__event ${isMobile ? "maintenance-calendar__event--mobile" : ""}`}
      data-priority={event.priority}
    >
      <header className="maintenance-calendar__event-header">
        <span className="maintenance-calendar__event-id">#{event.id}</span>
        <span className="maintenance-calendar__event-time">
          {startTime}
          {endTime && ` – ${endTime}`}
        </span>
      </header>
      <div className="maintenance-calendar__event-title">{event.title.replace(/^#\d+ •\s*/, "")}</div>
      <div className="maintenance-calendar__event-meta">
        {event.resort?.name && <span>{event.resort.name}</span>}
        {event.room?.name && <span>Camera {event.room.name}</span>}
        {!isMobile && event.assignedTo?.name && <span>{event.assignedTo.name}</span>}
      </div>
      <footer className="maintenance-calendar__event-footer">
        <span className={`maintenance-calendar__event-pill maintenance-calendar__event-pill--priority-${event.priority}`}>
          {event.priority}
        </span>
        <span className="maintenance-calendar__event-status">{event.status}</span>
        {!event.acknowledged && (
          <span className="maintenance-calendar__event-pill maintenance-calendar__event-pill--warning">Conferma scadenza</span>
        )}
        <button type="button" className="maintenance-calendar__quick" onClick={handleOpen}>
          Apri
        </button>
      </footer>
    </div>
  );
}

CalendarEvent.propTypes = {
  event: PropTypes.shape({
    id: PropTypes.number,
    title: PropTypes.string,
    status: PropTypes.string,
    priority: PropTypes.string,
    resort: PropTypes.shape({ name: PropTypes.string }),
    room: PropTypes.shape({ name: PropTypes.string }),
    assignedTo: PropTypes.shape({ name: PropTypes.string }),
    acknowledged: PropTypes.bool,
    start: PropTypes.instanceOf(Date),
    end: PropTypes.instanceOf(Date),
  }).isRequired,
  onSelect: PropTypes.func,
  isMobile: PropTypes.bool,
};

CalendarEvent.defaultProps = {
  onSelect: undefined,
  isMobile: false,
};

function CalendarToolbar({ label, onNavigate, onView, view, availableViews, isMobile }) {
  const handleViewChange = (nextView) => () => onView(nextView);

  return (
    <div className={`maintenance-calendar__toolbar ${isMobile ? "maintenance-calendar__toolbar--compact" : ""}`}>
      <div className="maintenance-calendar__toolbar-primary">
        <button type="button" onClick={() => onNavigate("PREV")} aria-label="Periodo precedente">
          <i className="fas fa-chevron-left" aria-hidden="true" />
        </button>
        <span className="maintenance-calendar__toolbar-label">{label}</span>
        <button type="button" onClick={() => onNavigate("NEXT")} aria-label="Periodo successivo">
          <i className="fas fa-chevron-right" aria-hidden="true" />
        </button>
        <button type="button" onClick={() => onNavigate("TODAY")} className="maintenance-calendar__today">
          Oggi
        </button>
      </div>
      <div className="maintenance-calendar__toolbar-views" role="group" aria-label="Seleziona vista calendario">
        {availableViews.map((calendarView) => (
          <button
            key={calendarView}
            type="button"
            onClick={handleViewChange(calendarView)}
            className={view === calendarView ? "is-active" : ""}
          >
            {calendarView === "month" && "Mese"}
            {calendarView === "week" && "Settimana"}
            {calendarView === "day" && "Giorno"}
            {calendarView === "agenda" && "Agenda"}
          </button>
        ))}
      </div>
    </div>
  );
}

CalendarToolbar.propTypes = {
  label: PropTypes.string.isRequired,
  onNavigate: PropTypes.func.isRequired,
  onView: PropTypes.func.isRequired,
  view: PropTypes.string.isRequired,
  availableViews: PropTypes.arrayOf(PropTypes.string).isRequired,
  isMobile: PropTypes.bool,
};

CalendarToolbar.defaultProps = {
  isMobile: false,
};

export default function MaintenanceCalendar({
  events,
  metadata,
  filters,
  onFilterChange,
  onSelectEvent,
  isLoading,
  error,
  onRetry,
}) {
  const calendarEvents = useMemo(() => events ?? [], [events]);
  const isClient = typeof window !== "undefined";
  const initialIsMobile = isClient ? window.matchMedia("(max-width: 768px)").matches : false;
  const [isMobile, setIsMobile] = useState(initialIsMobile);
  const [activeView, setActiveView] = useState(initialIsMobile ? "agenda" : "month");
  const [calendarHeight, setCalendarHeight] = useState(620);
  const [showLegend, setShowLegend] = useState(true);

  useEffect(() => {
    if (!isClient) return undefined;
    const media = window.matchMedia("(max-width: 768px)");
    const update = (event) => setIsMobile(event.matches);
    setIsMobile(media.matches);
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [isClient]);

  useEffect(() => {
    setShowLegend(!isMobile);
  }, [isMobile]);

  const updateCalendarHeight = useCallback(() => {
    if (!isClient) return;
    const viewport = window.innerHeight || 760;
    const baseOffset = isMobile ? 240 : 320;
    const minHeight = isMobile ? 420 : 560;
    const computed = Math.max(minHeight, viewport - baseOffset);
    setCalendarHeight(computed);
  }, [isMobile]);

  useEffect(() => {
    updateCalendarHeight();
    if (!isClient) return undefined;
    window.addEventListener("resize", updateCalendarHeight);
    return () => window.removeEventListener("resize", updateCalendarHeight);
  }, [updateCalendarHeight, isClient]);

  const eventStyleGetter = useCallback((event) => {
    const backgroundImage = gradientForEvent(event);
    const style = {
      backgroundImage,
      borderRadius: "16px",
      border: "none",
      color: "#fff",
      boxShadow: "0 12px 24px rgba(15, 23, 42, 0.18)",
      padding: "6px 8px",
    };
    return { style };
  }, []);

  const handleFilterChange = (field, value) => {
    onFilterChange({ ...filters, [field]: value });
  };

  const resetFilters = () => {
    onFilterChange({ resort: "", company: "", assigned_to: "", status: "", priority: "" });
  };

  const handleViewChange = (next) => {
    setActiveView(next);
  };

  const statusLegend = useMemo(
    () =>
      metadata.filters?.statuses?.map((status) => ({
        ...status,
        color: statusColors[status.value] || "#475569",
      })) ?? [],
    [metadata.filters?.statuses]
  );

  const priorityLegend = useMemo(
    () =>
      metadata.filters?.priorities?.map((priority) => ({
        ...priority,
        color: priorityColors[priority.value] || "#64748b",
      })) ?? [],
    [metadata.filters?.priorities]
  );

  const availableViews = useMemo(
    () => (isMobile ? ["month", "agenda", "day"] : ["month", "week", "day", "agenda"]),
    [isMobile]
  );

  useEffect(() => {
    if (!availableViews.includes(activeView)) {
      setActiveView(availableViews[0]);
    }
  }, [availableViews, activeView]);

  const calendarClassName = useMemo(
    () => `maintenance-calendar ${isMobile ? "maintenance-calendar--mobile" : ""}`.trim(),
    [isMobile]
  );

  return (
    <div className={calendarClassName}>
      <div className="maintenance-calendar__filters">
        <div className="maintenance-calendar__filters-scroll">
          {metadata.scope?.companies?.length > 0 && (
            <label>
              <span>Società</span>
              <select
                value={filters.company ?? ""}
                onChange={(event) => handleFilterChange("company", event.target.value)}
              >
                <option value="">Tutte</option>
                {metadata.scope.companies.map((company) => (
                  <option key={company.id} value={company.id}>
                    {company.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            <span>Struttura</span>
            <select value={filters.resort} onChange={(event) => handleFilterChange("resort", event.target.value)}>
              <option value="">Tutte</option>
              {metadata.filters?.resorts?.map((resort) => (
                <option key={resort.id} value={resort.id}>
                  {resort.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Manutentore</span>
            <select
              value={filters.assigned_to}
              onChange={(event) => handleFilterChange("assigned_to", event.target.value)}
            >
              <option value="">Tutti</option>
              {metadata.filters?.maintainers?.map((maint) => (
                <option key={maint.id} value={maint.id}>
                  {maint.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Stato</span>
            <select value={filters.status} onChange={(event) => handleFilterChange("status", event.target.value)}>
              <option value="">Tutti</option>
              {metadata.filters?.statuses?.map((status) => (
                <option key={status.value} value={status.value}>
                  {status.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Priorità</span>
            <select value={filters.priority} onChange={(event) => handleFilterChange("priority", event.target.value)}>
              <option value="">Tutte</option>
              {metadata.filters?.priorities?.map((priority) => (
                <option key={priority.value} value={priority.value}>
                  {priority.label}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="maintenance-btn maintenance-btn--outline" onClick={resetFilters}>
            Reimposta filtri
          </button>
        </div>
      </div>

      {isMobile && (
        <button
          type="button"
          className="maintenance-calendar__legend-toggle"
          onClick={() => setShowLegend((visible) => !visible)}
          aria-expanded={showLegend}
        >
          <span>Legenda interventi</span>
          <i className={`fa-solid fa-chevron-${showLegend ? "up" : "down"}`} aria-hidden="true" />
        </button>
      )}

      <aside
        className={`maintenance-calendar__legend ${showLegend ? "maintenance-calendar__legend--visible" : "maintenance-calendar__legend--hidden"}`}
      >
        <div>
          <h4>Legenda stato</h4>
          <ul>
            {statusLegend.map((status) => (
              <li key={status.value}>
                <span style={{ backgroundColor: status.color }} aria-hidden="true" />
                <span>{status.label}</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4>Legenda priorità</h4>
          <ul>
            {priorityLegend.map((priority) => (
              <li key={priority.value}>
                <span style={{ backgroundColor: priority.color }} aria-hidden="true" />
                <span>{priority.label}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="maintenance-calendar__legend-note">
          <p>
            {metadata.permissions?.canAssignTickets
              ? "Puoi riassegnare i ticket trascinandoli su un altro manutentore."
              : "Visualizzazione sola lettura basata sui tuoi permessi."}
          </p>
        </div>
      </aside>

      <div className="maintenance-calendar__board">
        <Calendar
          localizer={localizer}
          events={calendarEvents}
          startAccessor="start"
          endAccessor="end"
          view={activeView}
          onView={handleViewChange}
          views={availableViews}
          popup
          onSelectEvent={onSelectEvent}
          eventPropGetter={eventStyleGetter}
          components={{
            event: (props) => <CalendarEvent {...props} onSelect={onSelectEvent} isMobile={isMobile} />,
            toolbar: (toolbarProps) => (
              <CalendarToolbar
                {...toolbarProps}
                availableViews={availableViews}
                view={activeView}
                onView={(next) => {
                  toolbarProps.onView(next);
                  handleViewChange(next);
                }}
                isMobile={isMobile}
              />
            ),
          }}
          style={{ height: calendarHeight, minHeight: calendarHeight }}
          culture="it"
        />
        {isLoading && (
          <div className="maintenance-calendar__loading" aria-hidden="true">
            <div className="spinner" />
            <p>Caricamento calendario manutenzioni...</p>
          </div>
        )}
        {!isLoading && error && (
          <div className="maintenance-calendar__error" role="status">
            <p>{error}</p>
            {onRetry && (
              <button type="button" className="maintenance-btn maintenance-btn--outline" onClick={onRetry}>
                Riprova
              </button>
            )}
          </div>
        )}
        {!isLoading && !error && calendarEvents.length === 0 && (
          <div className="maintenance-calendar__empty" role="status">
            <i className="fa-regular fa-calendar" aria-hidden="true" />
            <p>Nessun intervento programmato per il periodo selezionato.</p>
          </div>
        )}
      </div>
    </div>
  );
}

MaintenanceCalendar.propTypes = {
  events: PropTypes.arrayOf(PropTypes.object),
  metadata: PropTypes.shape({
    filters: PropTypes.shape({
      resorts: PropTypes.array,
      maintainers: PropTypes.array,
      statuses: PropTypes.array,
      priorities: PropTypes.array,
    }),
    scope: PropTypes.shape({
      companies: PropTypes.array,
      resorts: PropTypes.array,
    }),
    permissions: PropTypes.shape({
      canAssignTickets: PropTypes.bool,
    }),
  }),
  filters: PropTypes.shape({
    resort: PropTypes.string,
    company: PropTypes.string,
    assigned_to: PropTypes.string,
    status: PropTypes.string,
    priority: PropTypes.string,
  }),
  onFilterChange: PropTypes.func.isRequired,
  onSelectEvent: PropTypes.func,
  isLoading: PropTypes.bool,
  error: PropTypes.string,
  onRetry: PropTypes.func,
};

MaintenanceCalendar.defaultProps = {
  events: [],
  metadata: {
    filters: { resorts: [], maintainers: [], statuses: [], priorities: [] },
    scope: { companies: [], resorts: [] },
    permissions: {},
  },
  filters: { resort: "", company: "", assigned_to: "", status: "", priority: "" },
  onSelectEvent: undefined,
  isLoading: false,
  error: "",
  onRetry: undefined,
};
