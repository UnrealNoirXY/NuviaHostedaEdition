import React, { useMemo } from "react";
import PropTypes from "prop-types";
import moment from "moment";

moment.locale("it");

const toneColors = {
  primary: "maintenance-overview__card--primary",
  warning: "maintenance-overview__card--warning",
  danger: "maintenance-overview__card--danger",
  success: "maintenance-overview__card--success",
};

function StatCard({ icon, label, value, tone, onClick, isActive, isLoading }) {
  const className = [
    "maintenance-overview__card",
    toneColors[tone] || toneColors.primary,
    isActive ? "maintenance-overview__card--active" : "",
    onClick ? "maintenance-overview__card--clickable" : "",
    isLoading ? "maintenance-overview__card--skeleton" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button type="button" className={className} onClick={onClick} disabled={isLoading || !onClick}>
      <span className="maintenance-overview__icon" aria-hidden="true">
        <i className={icon} />
      </span>
      <div className="maintenance-overview__card-content">
        <span className="maintenance-overview__card-label">{label}</span>
        <span className="maintenance-overview__card-value">{isLoading ? "" : value}</span>
      </div>
    </button>
  );
}

StatCard.propTypes = {
  icon: PropTypes.string.isRequired,
  label: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  tone: PropTypes.oneOf(["primary", "warning", "danger", "success"]),
  onClick: PropTypes.func,
  isActive: PropTypes.bool,
  isLoading: PropTypes.bool,
};

StatCard.defaultProps = {
  tone: "primary",
  onClick: undefined,
  isActive: false,
  isLoading: false,
};

export default function MaintenanceOverview({
  tickets,
  onApplyQuickFilter,
  onSelectTab,
  onSelectTicket,
  activeQuickFilters,
  insights,
  insightsLoading,
  ticketsLoading,
  canClaim,
  receivesUnassignedAlerts,
  onToggleAlerts,
  preferenceSaving,
  error,
}) {
  const stats = useMemo(() => {
    const total = tickets.length;
    const open = tickets.filter((ticket) => ticket.status === "open").length;
    const inProgress = tickets.filter((ticket) => ticket.status === "in_progress").length;
    const resolved = tickets.filter((ticket) => ticket.status === "resolved" || ticket.status === "closed").length;

    const now = moment();
    const overdue = tickets.filter((ticket) => ticket.due_date && moment(ticket.due_date).isBefore(now)).length;
    const dueSoon = tickets.filter((ticket) => {
      if (!ticket.due_date) return false;
      const diffHours = moment(ticket.due_date).diff(now, "hours", true);
      return diffHours >= 0 && diffHours <= 48;
    }).length;
    const ackPending = tickets.filter((ticket) => ticket.due_date && !ticket.acknowledged_due_date).length;

    const nextDeadlines = tickets
      .filter((ticket) => ticket.due_date)
      .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
      .slice(0, 4)
      .map((ticket) => ({
        id: ticket.id,
        title: ticket.title,
        due: moment(ticket.due_date).format("DD/MM HH:mm"),
        resort: ticket.resort?.name,
        room: ticket.room?.name,
        isAckPending: ticket.due_date && !ticket.acknowledged_due_date,
      }));

    return {
      total,
      open,
      inProgress,
      resolved,
      overdue,
      dueSoon,
      ackPending,
      nextDeadlines,
    };
  }, [tickets]);

  const unassignedStats = insights?.unassigned || { total: 0, overdue: 0, dueSoon: 0, withoutDeadline: 0, percentOverdue: 0 };
  const averageClaim = insights?.averages?.claimHours;

  const handleQuickFilter = (field, value) => () => {
    onApplyQuickFilter({ [field]: activeQuickFilters[field] === value ? "" : value });
  };

  const handleToggleAlertsClick = () => {
    if (!onToggleAlerts) return;
    const message = receivesUnassignedAlerts
      ? "Vuoi disattivare gli avvisi sui ticket liberi?"
      : "Vuoi ricevere gli avvisi sui ticket liberi?";
    if (window.confirm(message)) {
      onToggleAlerts(!receivesUnassignedAlerts);
    }
  };

  return (
    <section className="maintenance-overview" aria-label="Sintesi manutenzione">
      {error && (
        <div className="maintenance-alert maintenance-alert--inline" role="status">
          <i className="fa-solid fa-circle-info" aria-hidden="true" /> {error}
        </div>
      )}
      <div className="maintenance-overview__grid">
        <StatCard icon="fa-solid fa-list-check" label="Ticket totali" value={stats.total} tone="primary" isLoading={ticketsLoading} />
        <StatCard
          icon="fa-regular fa-folder-open"
          label="Aperti"
          value={stats.open}
          tone="primary"
          onClick={handleQuickFilter("status", "open")}
          isActive={activeQuickFilters.status === "open"}
          isLoading={ticketsLoading}
        />
        <StatCard
          icon="fa-solid fa-screwdriver-wrench"
          label="In lavorazione"
          value={stats.inProgress}
          tone="primary"
          onClick={handleQuickFilter("status", "in_progress")}
          isActive={activeQuickFilters.status === "in_progress"}
          isLoading={ticketsLoading}
        />
        <StatCard
          icon="fa-regular fa-circle-check"
          label="Risolti"
          value={stats.resolved}
          tone="success"
          onClick={() => onSelectTab("calendar")}
          isLoading={ticketsLoading}
        />
        <StatCard
          icon="fa-regular fa-bell"
          label="In scadenza (48h)"
          value={stats.dueSoon}
          tone="warning"
          onClick={handleQuickFilter("due", "soon")}
          isActive={activeQuickFilters.due === "soon"}
          isLoading={ticketsLoading}
        />
        <StatCard
          icon="fa-solid fa-triangle-exclamation"
          label="Scaduti"
          value={stats.overdue}
          tone="danger"
          onClick={handleQuickFilter("due", "overdue")}
          isActive={activeQuickFilters.due === "overdue"}
          isLoading={ticketsLoading}
        />
        <StatCard
          icon="fa-solid fa-user-clock"
          label="Da confermare"
          value={stats.ackPending}
          tone="warning"
          onClick={handleQuickFilter("ack", "pending")}
          isActive={activeQuickFilters.ack === "pending"}
          isLoading={ticketsLoading}
        />
        <StatCard
          icon="fa-solid fa-people-group"
          label="Ticket liberi"
          value={unassignedStats.total}
          tone={unassignedStats.overdue > 0 ? "danger" : "warning"}
          onClick={handleQuickFilter("assignment", "unassigned")}
          isActive={activeQuickFilters.assignment === "unassigned"}
          isLoading={ticketsLoading}
        />
      </div>

      <div className="maintenance-overview__cta">
        <div className="maintenance-overview__panel">
          <div className="maintenance-overview__panel-header">
            <h4>Prossime scadenze</h4>
            <button type="button" className="maintenance-link" onClick={() => onSelectTab("calendar")}>
              Vai al calendario <i className="fa-solid fa-arrow-right" aria-hidden="true" />
            </button>
          </div>
          <ul className="maintenance-overview__deadline-list">
            {stats.nextDeadlines.length === 0 ? (
              <li className="text-muted">Nessuna scadenza pianificata.</li>
            ) : (
              stats.nextDeadlines.map((deadline) => (
                <li key={deadline.id}>
                  <button type="button" onClick={() => onSelectTicket(deadline.id)}>
                    <span className="maintenance-overview__deadline-title">#{deadline.id} • {deadline.title}</span>
                    <span className="maintenance-overview__deadline-meta">
                      <span><i className="fa-regular fa-clock" aria-hidden="true" /> {deadline.due}</span>
                      {deadline.resort && <span>{deadline.resort}</span>}
                      {deadline.room && <span>Camera {deadline.room}</span>}
                      {deadline.isAckPending && (
                        <span className="maintenance-overview__deadline-pill">Conferma scadenza</span>
                      )}
                    </span>
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>

        <div className="maintenance-overview__panel">
          <div className="maintenance-overview__panel-header">
            <h4>Ticket non assegnati</h4>
            {canClaim && (
              <button
                type="button"
                className="maintenance-switch"
                onClick={handleToggleAlertsClick}
                disabled={preferenceSaving}
                aria-pressed={receivesUnassignedAlerts}
              >
                <span className={`maintenance-switch__thumb ${receivesUnassignedAlerts ? "is-active" : ""}`} />
                <span className="maintenance-switch__label">
                  {receivesUnassignedAlerts ? "Avvisi attivi" : "Avvisi disattivati"}
                </span>
              </button>
            )}
          </div>
          <div className="maintenance-overview__panel-body">
            <div className="maintenance-overview__insight">
              <span className="maintenance-overview__insight-value">{unassignedStats.overdue}</span>
              <span className="maintenance-overview__insight-label">Scaduti</span>
            </div>
            <div className="maintenance-overview__insight">
              <span className="maintenance-overview__insight-value">{unassignedStats.dueSoon}</span>
              <span className="maintenance-overview__insight-label">In scadenza</span>
            </div>
            <div className="maintenance-overview__insight">
              <span className="maintenance-overview__insight-value">{unassignedStats.withoutDeadline}</span>
              <span className="maintenance-overview__insight-label">Senza scadenza</span>
            </div>
            <div className="maintenance-overview__insight">
              <span className="maintenance-overview__insight-value">
                {insightsLoading || averageClaim === null ? "-" : `${averageClaim.toFixed(1)}h`}
              </span>
              <span className="maintenance-overview__insight-label">Ore medie di presa in carico</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

MaintenanceOverview.propTypes = {
  tickets: PropTypes.arrayOf(PropTypes.object).isRequired,
  onApplyQuickFilter: PropTypes.func.isRequired,
  onSelectTab: PropTypes.func.isRequired,
  onSelectTicket: PropTypes.func.isRequired,
  activeQuickFilters: PropTypes.shape({
    status: PropTypes.string,
    due: PropTypes.string,
    ack: PropTypes.string,
    assignment: PropTypes.string,
  }).isRequired,
  insights: PropTypes.shape({
    unassigned: PropTypes.object,
    averages: PropTypes.object,
  }),
  insightsLoading: PropTypes.bool,
  ticketsLoading: PropTypes.bool,
  canClaim: PropTypes.bool,
  receivesUnassignedAlerts: PropTypes.bool,
  onToggleAlerts: PropTypes.func,
  preferenceSaving: PropTypes.bool,
  error: PropTypes.string,
};

MaintenanceOverview.defaultProps = {
  insights: { unassigned: {}, averages: {} },
  insightsLoading: false,
  ticketsLoading: false,
  canClaim: false,
  receivesUnassignedAlerts: true,
  onToggleAlerts: undefined,
  preferenceSaving: false,
  error: "",
};
