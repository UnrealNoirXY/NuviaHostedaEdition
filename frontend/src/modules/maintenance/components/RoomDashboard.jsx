import React, { useEffect, useMemo, useState } from "react";
import PropTypes from "prop-types";

const statusCopy = {
  ok: {
    label: "Tutto OK",
    icon: "fa-regular fa-circle-check",
    className: "room-card--ok",
  },
  warning: {
    label: "Attenzione",
    icon: "fa-solid fa-triangle-exclamation",
    className: "room-card--warning",
  },
  critical: {
    label: "Urgenza",
    icon: "fa-solid fa-circle-exclamation",
    className: "room-card--critical",
  },
};

const defaultSummary = {
  totalRooms: 0,
  roomsOk: 0,
  roomsWarning: 0,
  roomsCritical: 0,
  openTickets: 0,
  resolvedTickets: 0,
  alerts: 0,
  plannedBudget: "0",
  investedBudget: "0",
};

const defaultDetailStats = {
  openTickets: 0,
  inProgressTickets: 0,
  resolvedTickets: 0,
  overdueTickets: 0,
  plannedBudget: "0",
  investedBudget: "0",
};

const formatCurrency = (value) => {
  if (value === null || value === undefined) return "€0";
  const amount = Number.parseFloat(value);
  if (Number.isNaN(amount)) {
    return `€${value}`;
  }
  return amount.toLocaleString("it-IT", { style: "currency", currency: "EUR" });
};

const formatDateTime = (value) => {
  if (!value) return "";
  return new Date(value).toLocaleString("it-IT", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

function SummaryCard({ icon, title, value, subtitle }) {
  return (
    <div className="room-summary-card">
      <div className="room-summary-card__icon">
        <i className={icon} />
      </div>
      <div className="room-summary-card__content">
        <div className="room-summary-card__value">{value}</div>
        <div className="room-summary-card__title">{title}</div>
        {subtitle && <div className="room-summary-card__subtitle">{subtitle}</div>}
      </div>
    </div>
  );
}

SummaryCard.propTypes = {
  icon: PropTypes.string.isRequired,
  title: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  subtitle: PropTypes.string,
};

SummaryCard.defaultProps = {
  subtitle: null,
};

function RoomDetailPanel({ detail, isLoading, onSelectTickets }) {
  if (isLoading) {
    return (
      <div className="room-detail-panel room-detail-panel--loading">
        <div className="spinner" aria-hidden="true" />
        <p>Caricamento dettagli camera...</p>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="room-detail-panel room-detail-panel--empty">
        <p>Seleziona una camera dalla lista per visualizzare lo storico.</p>
      </div>
    );
  }

  const stats = detail.stats ?? defaultDetailStats;
  const hasAlerts = detail.alerts && detail.alerts.length > 0;

  return (
    <div className={`room-detail-panel room-detail-panel--${detail.room?.status || "ok"}`}>
      <header className="room-detail-panel__header">
        <div>
          <h3>{detail.room?.name}</h3>
          <p>
            {detail.room?.resort?.name}
            {detail.room?.company ? ` · ${detail.room.company.name}` : ""}
          </p>
        </div>
        {detail.ticketIds?.length > 0 && (
          <button
            type="button"
            className="maintenance-btn maintenance-btn--outline"
            onClick={() => onSelectTickets(detail.ticketIds)}
          >
            Vai ai ticket
          </button>
        )}
      </header>

      <section className="room-detail-panel__stats">
        <div className="room-detail-panel__stat">
          <span>Ticket aperti</span>
          <strong>{stats.openTickets}</strong>
        </div>
        <div className="room-detail-panel__stat">
          <span>In lavorazione</span>
          <strong>{stats.inProgressTickets}</strong>
        </div>
        <div className="room-detail-panel__stat">
          <span>Risolti</span>
          <strong>{stats.resolvedTickets}</strong>
        </div>
        <div className="room-detail-panel__stat">
          <span>Budget investito</span>
          <strong>{formatCurrency(stats.investedBudget)}</strong>
        </div>
        <div className="room-detail-panel__stat">
          <span>Budget da investire</span>
          <strong>{formatCurrency(stats.plannedBudget)}</strong>
        </div>
      </section>

      <section className="room-detail-panel__section">
        <h4>Allerte manutenzione</h4>
        {hasAlerts ? (
          <ul className="room-detail-panel__alerts">
            {detail.alerts.map((alert) => (
              <li key={alert.id}>
                <div>{alert.reason}</div>
                <span className="room-detail-panel__alert-date">{formatDateTime(alert.createdAt)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">Nessuna allerta attiva per questa camera.</p>
        )}
      </section>

      <section className="room-detail-panel__section">
        <h4>Ticket da fare</h4>
        {detail.tickets?.open?.length ? (
          <ul className="room-detail-panel__ticket-list">
            {detail.tickets.open.map((ticket) => (
              <li key={ticket.id}>
                <div>
                  <strong>{ticket.title}</strong>
                  <div className="room-detail-panel__ticket-meta">
                    <span className={`badge badge--status-${ticket.status}`}>
                      {ticket.status}
                    </span>
                    {ticket.priority && <span className={`badge badge--priority-${ticket.priority}`}>{ticket.priority}</span>}
                    {ticket.dueDate && <span>Scadenza: {formatDateTime(ticket.dueDate)}</span>}
                    {ticket.estimatedCost && <span>Previsto: {formatCurrency(ticket.estimatedCost)}</span>}
                    {ticket.assignedTo && <span>Assegnato a {ticket.assignedTo}</span>}
                  </div>
                </div>
                <button
                  type="button"
                  className="maintenance-btn maintenance-btn--outline"
                  onClick={() => onSelectTickets([ticket.id])}
                >
                  Apri ticket
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">Nessun ticket aperto: ottimo lavoro!</p>
        )}
      </section>

      <section className="room-detail-panel__section">
        <h4>Storico ticket risolti</h4>
        {detail.tickets?.resolved?.length ? (
          <ul className="room-detail-panel__timeline">
            {detail.tickets.resolved.map((ticket) => (
              <li key={ticket.id}>
                <div className="room-detail-panel__timeline-header">
                  <strong>{ticket.title}</strong>
                  <span>{formatDateTime(ticket.closedAt)}</span>
                </div>
                <div className="room-detail-panel__timeline-body">
                  <span className={`badge badge--status-${ticket.status}`}>{ticket.status}</span>
                  {ticket.actualCost && <span>{formatCurrency(ticket.actualCost)}</span>}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-muted">Ancora nessun ticket risolto registrato.</p>
        )}
      </section>
    </div>
  );
}

RoomDetailPanel.propTypes = {
  detail: PropTypes.shape({
    room: PropTypes.shape({
      id: PropTypes.number,
      name: PropTypes.string,
      status: PropTypes.string,
      resort: PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
      company: PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
      }),
    }),
    stats: PropTypes.shape({
      openTickets: PropTypes.number,
      inProgressTickets: PropTypes.number,
      resolvedTickets: PropTypes.number,
      overdueTickets: PropTypes.number,
      plannedBudget: PropTypes.string,
      investedBudget: PropTypes.string,
    }),
    alerts: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        reason: PropTypes.string,
        createdAt: PropTypes.string,
      })
    ),
    tickets: PropTypes.shape({
      open: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number.isRequired,
          title: PropTypes.string.isRequired,
          status: PropTypes.string,
          priority: PropTypes.string,
          dueDate: PropTypes.string,
          estimatedCost: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
          assignedTo: PropTypes.string,
        })
      ),
      resolved: PropTypes.arrayOf(
        PropTypes.shape({
          id: PropTypes.number.isRequired,
          title: PropTypes.string.isRequired,
          status: PropTypes.string,
          closedAt: PropTypes.string,
          actualCost: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
        })
      ),
    }),
    ticketIds: PropTypes.arrayOf(PropTypes.number),
  }),
  isLoading: PropTypes.bool,
  onSelectTickets: PropTypes.func.isRequired,
};

RoomDetailPanel.defaultProps = {
  detail: null,
  isLoading: false,
};

export default function RoomDashboard({
  hierarchy,
  summary,
  selectedRoomId,
  roomDetail,
  isRoomDetailLoading,
  onSelectRoom,
  onSelectTickets,
  isLoading,
  error,
}) {
  const companyOptions = useMemo(
    () =>
      (hierarchy?.companies ?? []).map((company, index) => ({
        key: company.id ?? `none-${index}`,
        id: company.id,
        name: company.name,
        resorts: company.resorts ?? [],
      })),
    [hierarchy]
  );

  const [activeCompanyKey, setActiveCompanyKey] = useState(companyOptions[0]?.key ?? null);

  useEffect(() => {
    if (!companyOptions.length) {
      setActiveCompanyKey(null);
      return;
    }
    const found = companyOptions.find((option) => option.key === activeCompanyKey);
    if (!found) {
      setActiveCompanyKey(companyOptions[0].key);
    }
  }, [companyOptions, activeCompanyKey]);

  const activeCompany = useMemo(
    () => companyOptions.find((option) => option.key === activeCompanyKey) ?? companyOptions[0] ?? null,
    [companyOptions, activeCompanyKey]
  );

  const resortOptions = activeCompany?.resorts?.map((resort) => ({
    id: resort.id,
    name: resort.name,
    rooms: resort.rooms ?? [],
    stats: resort.stats ?? defaultSummary,
  })) ?? [];

  const [activeResortId, setActiveResortId] = useState(resortOptions[0]?.id ?? null);

  useEffect(() => {
    if (!resortOptions.length) {
      setActiveResortId(null);
      return;
    }
    const found = resortOptions.find((resort) => resort.id === activeResortId);
    if (!found) {
      setActiveResortId(resortOptions[0].id);
    }
  }, [resortOptions, activeResortId]);

  const activeResort = resortOptions.find((resort) => resort.id === activeResortId) ?? resortOptions[0] ?? null;
  const rooms = activeResort?.rooms ?? [];
  const combinedSummary = summary ?? defaultSummary;

  if (isLoading) {
    return (
      <div className="rooms-dashboard rooms-dashboard--loading">
        <div className="rooms-dashboard__summary rooms-dashboard__summary--skeleton">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={String(index)} className="room-summary-card room-summary-card--skeleton" aria-hidden="true">
              <div className="room-summary-card__icon" />
              <div className="room-summary-card__content">
                <div className="room-summary-card__value" />
                <div className="room-summary-card__title" />
              </div>
            </div>
          ))}
        </div>
        <div className="rooms-dashboard__placeholder">
          <div className="spinner" aria-hidden="true" />
          <p>Caricamento panoramica camere...</p>
        </div>
      </div>
    );
  }

  if (!companyOptions.length) {
    return (
      <div className="empty-state">
        <p>Nessuna camera disponibile per il tuo profilo.</p>
      </div>
    );
  }

  return (
    <div className="rooms-dashboard">
      <div className="rooms-dashboard__summary">
        <SummaryCard icon="fa-solid fa-house" title="Camere monitorate" value={combinedSummary.totalRooms} />
        <SummaryCard icon="fa-solid fa-screwdriver-wrench" title="Ticket aperti" value={combinedSummary.openTickets} />
        <SummaryCard
          icon="fa-solid fa-bell"
          title="Allerte attive"
          value={combinedSummary.alerts}
          subtitle={`${combinedSummary.roomsCritical} camere critiche`}
        />
        <SummaryCard
          icon="fa-solid fa-coins"
          title="Budget investito"
          value={formatCurrency(combinedSummary.investedBudget)}
          subtitle={`Da investire ${formatCurrency(combinedSummary.plannedBudget)}`}
        />
      </div>

      <div className="rooms-dashboard__filters">
        {error && (
          <div className="maintenance-alert maintenance-alert--inline" role="status">
            <i className="fa-solid fa-circle-info" aria-hidden="true" /> {error}
          </div>
        )}
        {companyOptions.length > 1 && (
          <label className="rooms-dashboard__selector">
            <span>Società</span>
            <select value={activeCompanyKey ?? ""} onChange={(event) => setActiveCompanyKey(event.target.value)}>
              {companyOptions.map((option) => (
                <option key={option.key} value={option.key}>
                  {option.name}
                </option>
              ))}
            </select>
          </label>
        )}

        {resortOptions.length > 1 && (
          <label className="rooms-dashboard__selector">
            <span>Struttura</span>
            <select
              value={activeResortId ?? ""}
              onChange={(event) => setActiveResortId(Number.parseInt(event.target.value, 10))}
            >
              {resortOptions.map((resort) => (
                <option key={resort.id} value={resort.id}>
                  {resort.name}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="rooms-dashboard__content">
        <div className="rooms-dashboard__grid">
          {rooms.length ? (
            rooms.map((room) => {
              const copy = statusCopy[room.status] || statusCopy.ok;
              const isActive = room.id === selectedRoomId;
              const alerts = room.alerts ?? [];
              return (
                <button
                  type="button"
                  key={room.id}
                  className={`room-card ${copy.className} ${isActive ? "room-card--active" : ""}`}
                  onClick={() => onSelectRoom(room.id)}
                >
                  <div className="room-card__header">
                    <span className="room-card__title">{room.name}</span>
                    <span className="room-card__tag">
                      <i className={copy.icon} aria-hidden="true" /> {copy.label}
                    </span>
                  </div>
                  <div className="room-card__metrics">
                    <span>
                      <i className="fa-regular fa-note-sticky" aria-hidden="true" /> {room.openTickets} aperti
                    </span>
                    <span>
                      <i className="fa-solid fa-wallet" aria-hidden="true" /> {formatCurrency(room.plannedBudget)}
                    </span>
                    <span>
                      <i className="fa-solid fa-chart-line" aria-hidden="true" /> {formatCurrency(room.investedBudget)}
                    </span>
                  </div>
                  {alerts.length > 0 && (
                    <div className="room-card__alerts">
                      <i className="fa-solid fa-bell" aria-hidden="true" /> {alerts.length} alert
                    </div>
                  )}
                </button>
              );
            })
          ) : (
            <div className="empty-state">
              <p>Nessuna camera configurata per questa struttura.</p>
            </div>
          )}
        </div>

        <RoomDetailPanel detail={roomDetail} isLoading={isRoomDetailLoading} onSelectTickets={onSelectTickets} />
      </div>
    </div>
  );
}

RoomDashboard.propTypes = {
  hierarchy: PropTypes.shape({
    companies: PropTypes.arrayOf(
      PropTypes.shape({
        id: PropTypes.number,
        name: PropTypes.string,
        resorts: PropTypes.array,
      })
    ),
  }),
  summary: PropTypes.shape({
    totalRooms: PropTypes.number,
    roomsOk: PropTypes.number,
    roomsWarning: PropTypes.number,
    roomsCritical: PropTypes.number,
    openTickets: PropTypes.number,
    resolvedTickets: PropTypes.number,
    alerts: PropTypes.number,
    plannedBudget: PropTypes.string,
    investedBudget: PropTypes.string,
  }),
  selectedRoomId: PropTypes.number,
  roomDetail: RoomDetailPanel.propTypes.detail,
  isRoomDetailLoading: PropTypes.bool,
  onSelectRoom: PropTypes.func.isRequired,
  onSelectTickets: PropTypes.func.isRequired,
  isLoading: PropTypes.bool,
  error: PropTypes.string,
};

RoomDashboard.defaultProps = {
  hierarchy: { companies: [] },
  summary: defaultSummary,
  selectedRoomId: null,
  roomDetail: RoomDetailPanel.defaultProps.detail,
  isRoomDetailLoading: false,
  isLoading: false,
  error: "",
};
