import React, { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import apiClient from "../../apiClient";
import usePayslipPreviewFlow from "./hooks/usePayslipPreviewFlow";
import WorkspaceTabs from "./components/WorkspaceTabs";
import "../../hr-portal.css";

const formatDate = (value) => {
  if (!value) return "";
  try {
    return new Intl.DateTimeFormat("it-IT", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(value));
  } catch (error) {
    console.warn("Impossibile formattare la data", error);
    return value;
  }
};

const MONTH_LABELS = {
  "01": "Gennaio",
  "02": "Febbraio",
  "03": "Marzo",
  "04": "Aprile",
  "05": "Maggio",
  "06": "Giugno",
  "07": "Luglio",
  "08": "Agosto",
  "09": "Settembre",
  "10": "Ottobre",
  "11": "Novembre",
  "12": "Dicembre",
};

const extractPeriodLabel = (item) => {
  const source = [item?.file_name, item?.identifier, item?.file].filter(Boolean).join(" ");
  const match = source.match(/(20\\d{2})[-_](0[1-9]|1[0-2])/);
  if (!match) return "";
  const monthLabel = MONTH_LABELS[match[2]] || match[2];
  return `${monthLabel} ${match[1]}`;
};

const isValidPeriodInput = (value) => {
  if (!value) return true;
  return /^20\\d{2}[-/](0[1-9]|1[0-2])$/.test(value);
};

const normalizePeriodMachine = (value) => {
  if (!value) return "";
  const normalized = String(value).replace("_", "-");
  return /^20\\d{2}-(0[1-9]|1[0-2])$/.test(normalized) ? normalized : "";
};

const preferenceToForm = (preference) => ({
  allow_email: preference?.allow_email ?? true,
  allow_push: preference?.allow_push ?? true,
  allow_sms: preference?.allow_sms ?? false,
  quiet_hours_start: preference?.quiet_hours_start ? preference.quiet_hours_start.slice(0, 5) : "",
  quiet_hours_end: preference?.quiet_hours_end ? preference.quiet_hours_end.slice(0, 5) : "",
});

const EVENT_TYPE_OPTIONS = [
  { value: "", label: "Tutti gli eventi" },
  { value: "notification_created", label: "Notifiche create" },
  { value: "notification_updated", label: "Notifiche aggiornate" },
  { value: "notification_published", label: "Notifiche pubblicate" },
  { value: "notification_archived", label: "Notifiche archiviate" },
  { value: "payslip_batch_created", label: "Batch creati" },
  { value: "payslip_batch_failed", label: "Batch falliti" },
  { value: "payslip_resolved", label: "Assegnazioni manuali" },
  { value: "payslip_email_sent", label: "Email buste paga inviate" },
  { value: "payslip_email_failed", label: "Email buste paga fallite" },
  { value: "ticket_assigned", label: "Ticket assegnati" },
  { value: "ticket_closed", label: "Ticket chiusi" },
  { value: "preview_started", label: "Preview avviate" },
  { value: "preview_completed", label: "Preview completate" },
  { value: "preview_failed", label: "Preview fallite" },
  { value: "preview_confirmed", label: "Preview confermate" },
  { value: "preview_fallback_polling", label: "Fallback polling" },
];

const DOCUMENT_PAGE_SIZE = 6;
const PAYSLIP_PAGE_SIZE = 9;
const QUICK_REPLY_TEMPLATES = [
  {
    label: "Richiesta presa in carico",
    body: "Abbiamo preso in carico la tua richiesta. Ti aggiorneremo a breve con i prossimi passi.",
  },
  {
    label: "Serve maggiori dettagli",
    body: "Per procedere ci servono maggiori dettagli. Puoi indicare data, reparto e una breve descrizione?",
  },
  {
    label: "Chiusura con esito",
    body: "La richiesta è stata risolta. Se riscontri ulteriori problemi, rispondi a questo ticket.",
  },
];

const SectionHeader = ({ title, subtitle, actions, eyebrow = "HR Suite" }) => (
  <div className="hr-portal__section-header">
    <div>
      <p className="hr-portal__eyebrow">{eyebrow}</p>
      <h2 className="hr-portal__title">{title}</h2>
      {subtitle && <p className="hr-portal__subtitle">{subtitle}</p>}
    </div>
    {actions && <div className="hr-portal__actions">{actions}</div>}
  </div>
);

const StepSection = ({ step, title, subtitle, actions, children }) => (
  <section className="hr-portal__step">
    <SectionHeader
      title={title}
      subtitle={subtitle}
      actions={actions}
      eyebrow={`Step ${step}`}
    />
    <div className="hr-portal__step-body">{children}</div>
  </section>
);

const Subsection = ({ title, description, actions, children }) => (
  <section className="hr-portal__subsection">
    <div className="hr-portal__subsection-header">
      <div>
        <p className="hr-portal__eyebrow">{title}</p>
        {description && <h3 className="hr-portal__subsection-title">{description}</h3>}
      </div>
      {actions && <div className="hr-portal__actions">{actions}</div>}
    </div>
    {children}
  </section>
);

const EmptyState = ({ label }) => (
  <div className="hr-portal__empty">{label}</div>
);

const Pill = ({ tone = "neutral", children }) => (
  <span className={`hr-portal__pill hr-portal__pill--${tone}`}>{children}</span>
);

const LoadingOverlay = ({ label = "Caricamento" }) => (
  <div className="hr-portal__loading">
    <div className="hr-portal__spinner" />
    <span>{label}…</span>
  </div>
);

const SkeletonCard = ({ lines = 3 }) => (
  <div className="hr-portal__card hr-portal__card--skeleton">
    <div className="hr-portal__skeleton-line hr-portal__skeleton-line--title" />
    {Array.from({ length: lines }).map((_, idx) => (
      <div key={idx} className="hr-portal__skeleton-line" />
    ))}
  </div>
);

const Badge = ({ tone = "indigo", children }) => (
  <span className={`hr-portal__badge hr-portal__badge--${tone}`}>{children}</span>
);

const MicroBadge = ({ tone = "slate", children }) => (
  <span className={`hr-portal__micro-badge hr-portal__micro-badge--${tone}`}>{children}</span>
);

const StatCard = ({ title, value, helper }) => (
  <div className="hr-portal__stat-card">
    <p className="hr-portal__eyebrow">{title}</p>
    <h3>{value}</h3>
    {helper && <p className="hr-portal__muted">{helper}</p>}
  </div>
);

const WorkflowSteps = ({ items = [], current = 0 }) => (
  <div className="hr-portal__actions hr-portal__actions--wrap" role="list" aria-label="Workflow buste paga">
    {items.map((item, index) => {
      const done = index < current;
      const active = index === current;
      return (
        <span key={item} role="listitem" className={`hr-portal__badge ${active ? "hr-portal__badge--indigo" : done ? "hr-portal__badge--emerald" : "hr-portal__badge--slate"}`}>
          {index + 1}. {item}
        </span>
      );
    })}
  </div>
);

const EmailAutocompleteInput = ({
  value,
  onInput,
  onSelect,
  suggestions = [],
  loading = false,
  placeholder = "Inserisci email destinatario",
}) => (
  <div className="hr-portal__autocomplete">
    <input
      className="hr-portal__input"
      value={value || ""}
      placeholder={placeholder}
      onChange={(e) => onInput(e.target.value)}
      type="email"
    />
    {loading && <p className="hr-portal__hint">Ricerca email salvate…</p>}
    {!loading && suggestions?.length > 0 && (
      <div className="hr-portal__autocomplete-panel">
        {suggestions.map((item) => (
          <button key={item.email} type="button" className="hr-portal__autocomplete-item" onClick={() => onSelect(item.email)}>
            <span className="hr-portal__autocomplete-name">{item.email}</span>
            <span className="hr-portal__autocomplete-meta">Usata {item.used_count} volte</span>
          </button>
        ))}
      </div>
    )}
  </div>
);

const AssigneeInput = ({
  inputId,
  value,
  onInput,
  onSelect,
  suggestions = [],
  loading = false,
  disabled = false,
  placeholder = "Cerca per username o nome",
}) => {
  const inputDisabled = Boolean(disabled);
  return (
    <div className="hr-portal__autocomplete">
      <input
        id={inputId}
        className="hr-portal__input hr-portal__input--compact"
        value={value || ""}
        placeholder={placeholder}
        onChange={(e) => onInput(e.target.value)}
        disabled={inputDisabled}
      />
      {loading && <p className="hr-portal__hint">Ricerca collaboratori…</p>}
      {!loading && suggestions?.length > 0 && (
        <div className="hr-portal__autocomplete-panel">
          {suggestions.map((user) => (
            <button key={user.id} type="button" className="hr-portal__autocomplete-item" onClick={() => onSelect(user)}>
              <span className="hr-portal__autocomplete-name">{user.display_name || user.username}</span>
              <span className="hr-portal__autocomplete-meta">@{user.username}{user.role ? ` · ${user.role}` : ""}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

const PortalHeader = ({ context }) => {
  const scopeParts = [];
  if (context?.company?.name) scopeParts.push(context.company.name);
  if (context?.resort?.name) scopeParts.push(context.resort.name);
  const scopeLabel = scopeParts.length
    ? scopeParts.join(" / ")
    : context?.is_hr_admin
      ? "Accesso completo"
      : "Ambito non specificato";

  return (
    <header className="hr-portal__header">
      <div>
        <nav className="hr-portal__breadcrumb" aria-label="breadcrumb">
          <span className="hr-portal__breadcrumb-item">Dashboard</span>
          <span className="hr-portal__breadcrumb-separator">/</span>
          <span className="hr-portal__breadcrumb-item hr-portal__breadcrumb-item--active">HR Suite</span>
        </nav>
        <div className="hr-portal__header-title">
          <h1>HR Suite</h1>
          <p className="hr-portal__muted">Panoramica operativa e accesso rapido alle attività HR.</p>
        </div>
      </div>
      <div className="hr-portal__scope">
        <span className="hr-portal__scope-label">Ambito</span>
        <span className="hr-portal__scope-value">{scopeLabel}</span>
      </div>
    </header>
  );
};

const NotificationForm = ({ form, onChange, onSubmit, creating }) => (
  <div className="hr-portal__card hr-portal__card--form">
    <header className="hr-portal__card-header">
      <div>
        <p className="hr-portal__eyebrow">Nuova notifica</p>
        <h3>Composizione e scheduling</h3>
      </div>
      <Pill tone="indigo">{form.category || "general"}</Pill>
    </header>
    <div className="hr-portal__form-grid">
      <label className="hr-portal__field">
        <span>Titolo</span>
        <input
          className="hr-portal__input"
          value={form.title}
          onChange={(e) => onChange({ ...form, title: e.target.value })}
          placeholder="Titolo sintetico"
        />
      </label>
      <label className="hr-portal__field">
        <span>Categoria</span>
        <select
          className="hr-portal__input"
          value={form.category}
          onChange={(e) => onChange({ ...form, category: e.target.value })}
        >
          <option value="general">Generale</option>
          <option value="alert">Allerta</option>
          <option value="payroll">Buste paga</option>
          <option value="event">Evento</option>
        </select>
      </label>
      <label className="hr-portal__field hr-portal__field--wide">
        <span>Testo</span>
        <textarea
          className="hr-portal__input"
          rows={3}
          value={form.body}
          onChange={(e) => onChange({ ...form, body: e.target.value })}
          placeholder="Contenuto della comunicazione"
        />
      </label>
      <label className="hr-portal__field">
        <span>CTA label (opz.)</span>
        <input
          className="hr-portal__input"
          value={form.cta_label}
          onChange={(e) => onChange({ ...form, cta_label: e.target.value })}
          placeholder="Es. Conferma privacy"
        />
      </label>
      <label className="hr-portal__field">
        <span>CTA URL (opz.)</span>
        <input
          className="hr-portal__input"
          value={form.cta_url}
          onChange={(e) => onChange({ ...form, cta_url: e.target.value })}
          placeholder="https://... oppure /privacy-policy/"
        />
        <small className="hr-portal__hint">Sono accettati URL completi oppure percorsi relativi (es. /privacy-policy/).</small>
      </label>
      <label className="hr-portal__field">
        <span>CTA tipo</span>
        <select
          className="hr-portal__input"
          value={form.cta_type}
          onChange={(e) => onChange({ ...form, cta_type: e.target.value })}
        >
          <option value="primary">Primaria</option>
          <option value="secondary">Secondaria</option>
        </select>
      </label>
      <label className="hr-portal__field">
        <span>Programma invio (opz.)</span>
        <input
          type="datetime-local"
          className="hr-portal__input"
          value={form.scheduled_for}
          onChange={(e) => onChange({ ...form, scheduled_for: e.target.value })}
        />
      </label>
      <label className="hr-portal__field">
        <span>Scadenza (opz.)</span>
        <input
          type="datetime-local"
          className="hr-portal__input"
          value={form.expires_at}
          onChange={(e) => onChange({ ...form, expires_at: e.target.value })}
        />
      </label>
      <label className="hr-portal__field">
        <span>Ruoli destinatari (CSV, opz.)</span>
        <input
          className="hr-portal__input"
          value={form.audience_roles}
          onChange={(e) => onChange({ ...form, audience_roles: e.target.value })}
          placeholder="es. STAFF,MANAGER"
        />
      </label>
    </div>
    <div className="hr-portal__actions">
      <button className="hr-portal__button" onClick={onSubmit} disabled={creating}>
        {creating ? "Salvataggio…" : "Salva bozza"}
      </button>
    </div>
  </div>
);

const NotificationDeliveries = ({ deliveries }) => (
  <div className="hr-portal__stack">
    {deliveries.length === 0 ? (
      <p className="hr-portal__muted">Nessun recapito registrato.</p>
    ) : (
      deliveries.map((delivery) => (
        <div key={delivery.id} className="hr-portal__queue-item">
          <div>
            <p className="hr-portal__eyebrow">{delivery.channel}</p>
            <h4>{delivery.user}</h4>
            <p className="hr-portal__muted">{formatDate(delivery.sent_at || delivery.created_at)}</p>
          </div>
          <Pill tone={delivery.status === "delivered" ? "emerald" : delivery.status === "failed" ? "rose" : "amber"}>
            {delivery.status}
          </Pill>
        </div>
      ))
    )}
  </div>
);

const AuditLogList = ({ events }) => (
  <div className="hr-portal__stack">
    {events.length === 0 ? (
      <p className="hr-portal__muted">Nessun evento registrato nel periodo selezionato.</p>
    ) : (
      events.map((event) => (
        <div key={event.id} className="hr-portal__queue-item hr-portal__queue-item--stacked">
          <div>
            <p className="hr-portal__eyebrow">{event.event_type_display || event.event_type}</p>
            <h4>
              {event.target_model} #{event.target_id}
            </h4>
            <p className="hr-portal__muted">{formatDate(event.created_at)}</p>
          </div>
          <div className="hr-portal__stack">
            {event.metadata?.error && <Pill tone="rose">{event.metadata.error}</Pill>}
            {(event.metadata?.ip_address || event.metadata?.user_agent) && (
              <div className="hr-portal__meta">
                <span>IP: {event.metadata?.ip_address || "n/d"}</span>
                <span>User Agent: {event.metadata?.user_agent || "n/d"}</span>
              </div>
            )}
          </div>
        </div>
      ))
    )}
  </div>
);

const DocumentAckAuditList = ({ items }) => (
  <div className="hr-portal__stack">
    {items.length === 0 ? (
      <p className="hr-portal__muted">Nessuna presa visione registrata nel periodo selezionato.</p>
    ) : (
      items.map((entry) => (
        <div key={entry.id} className="hr-portal__queue-item hr-portal__queue-item--stacked">
          <div>
            <p className="hr-portal__eyebrow">Presa visione documento</p>
            <h4>{entry.document?.title || "Documento"}</h4>
            <p className="hr-portal__muted">
              {entry.actor?.display_name || entry.actor?.username || "Utente"} · {formatDate(entry.created_at)}
            </p>
          </div>
          <div className="hr-portal__stack">
            <div className="hr-portal__meta">
              <span>IP: {entry.ip_address || "n/d"}</span>
              <span>User Agent: {entry.user_agent || "n/d"}</span>
            </div>
          </div>
        </div>
      ))
    )}
  </div>
);

const NotificationCard = ({
  notification,
  onPublish,
  onArchive,
  onDeliver,
  onResend,
  onViewDeliveries,
  deliveryLoading,
  canManage,
}) => (
  <article className="hr-portal__card">
    <header className="hr-portal__card-header">
      <div>
        <p className="hr-portal__eyebrow">{notification.category}</p>
        <h3>{notification.title}</h3>
      </div>
      <div className="hr-portal__pill-row">
        <MicroBadge
          tone={notification.status === "published" ? "emerald" : notification.status === "archived" ? "slate" : "amber"}
        >
          {notification.status}
        </MicroBadge>
        {notification.scheduled_for && (
          <MicroBadge tone="indigo">{`Sched. ${formatDate(notification.scheduled_for)}`}</MicroBadge>
        )}
        {notification.expires_at && <MicroBadge tone="amber">{`Scade ${formatDate(notification.expires_at)}`}</MicroBadge>}
      </div>
    </header>
    <p className="hr-portal__muted">{notification.body}</p>
    <div className="hr-portal__meta">
      <span>Ultimo aggiornamento {formatDate(notification.updated_at)}</span>
      <span>Deliveries registrate: {notification.delivered_count || 0}</span>
    </div>
    {canManage && (
      <div className="hr-portal__actions hr-portal__actions--wrap">
        <button className="hr-portal__button" onClick={() => onDeliver(notification.id)}>
          Invia notifica
        </button>
        {notification.status !== "published" && notification.status !== "archived" && (
          <button className="hr-portal__button" onClick={() => onPublish(notification.id)}>
            Pubblica
          </button>
        )}
        {notification.status !== "archived" && (
          <button className="hr-portal__button hr-portal__button--ghost" onClick={() => onArchive(notification.id)}>
            Archivia
          </button>
        )}
        <button className="hr-portal__button hr-portal__button--ghost" onClick={() => onResend(notification.id)}>
          Reinvia fallite
        </button>
        <button
          className="hr-portal__link"
          onClick={() => onViewDeliveries(notification.id)}
          disabled={deliveryLoading === notification.id}
        >
          {deliveryLoading === notification.id ? "Caricamento recapiti…" : "Monitoraggio recapiti"}
        </button>
      </div>
    )}
  </article>
);

const DocumentList = ({ documents, onAcknowledge, acknowledging, layout = "default" }) => (
  <div className={layout === "bacheca" ? "hr-portal__list" : "hr-portal__grid"}>
    {documents.map((doc) => {
      const primaryLabel = doc.requires_signature
        ? "Firma"
        : doc.requires_acknowledgement
          ? "Leggi"
          : "Apri";
      return (
        <article key={doc.id} className={layout === "bacheca" ? "hr-portal__list-card" : "hr-portal__card"}>
          <header className={layout === "bacheca" ? "hr-portal__list-header" : "hr-portal__card-header"}>
            <div>
              <p className="hr-portal__eyebrow">{doc.category || "Documento"}</p>
              <h3>{doc.title}</h3>
            </div>
            <div className="hr-portal__pill-row">
              {doc.requires_signature && <MicroBadge tone="rose">Da firmare</MicroBadge>}
              {doc.requires_acknowledgement && !doc.requires_signature && <MicroBadge tone="amber">Da leggere</MicroBadge>}
              {!doc.requires_acknowledgement && !doc.requires_signature && <MicroBadge tone="emerald">Letto</MicroBadge>}
              {doc.visible_until && <MicroBadge tone="slate">Valido fino al {formatDate(doc.visible_until)}</MicroBadge>}
            </div>
          </header>
          <p className="hr-portal__muted">{doc.description || ""}</p>
          <div className="hr-portal__meta">
            <span>Ultimo aggiornamento {formatDate(doc.updated_at)}</span>
          </div>
          <div className={layout === "bacheca" ? "hr-portal__list-actions" : "hr-portal__actions"}>
            <a
              className={layout === "bacheca" ? "hr-portal__button hr-portal__button--primary" : "hr-portal__link"}
              href={doc.file}
              target="_blank"
              rel="noreferrer"
            >
              {primaryLabel}
            </a>
            {doc.requires_acknowledgement && (
              <button
                className={layout === "bacheca" ? "hr-portal__button hr-portal__button--ghost" : "hr-portal__button"}
                onClick={() => onAcknowledge(doc.id)}
                disabled={acknowledging === doc.id}
              >
                {acknowledging === doc.id ? "Registrazione…" : "Segna come letto"}
              </button>
            )}
          </div>
        </article>
      );
    })}
  </div>
);

const PayslipList = ({
  payslips,
  onRegeneratePeriod,
  regenerating,
  canRegenerate,
  onDownloadRenamed,
  downloadingRenamed,
  isOwner,
  layout = "default",
}) => (
  <div className={layout === "bacheca" ? "hr-portal__list" : "hr-portal__grid hr-portal__grid--compact"}>
    {payslips.map((payslip) => (
      <article key={payslip.id} className={layout === "bacheca" ? "hr-portal__list-card" : "hr-portal__card"}>
        <header className={layout === "bacheca" ? "hr-portal__list-header" : "hr-portal__card-header"}>
          <div>
            <p className="hr-portal__eyebrow">{payslip.period_label || extractPeriodLabel(payslip) || "Busta paga"}</p>
            <h3>{layout === "bacheca" ? (payslip.period_label || extractPeriodLabel(payslip) || "Busta paga") : `#${payslip.id}`}</h3>
          </div>
          <div className="hr-portal__pill-row">
            <MicroBadge tone="indigo">{payslip.period_label || extractPeriodLabel(payslip) || "Periodo"}</MicroBadge>
            {layout === "bacheca" ? (
              <MicroBadge tone={payslip.downloaded_at ? "emerald" : "amber"}>
                {payslip.downloaded_at ? "Scaricata" : "Da scaricare"}
              </MicroBadge>
            ) : (
              <>
                <MicroBadge tone={payslip.auto_matched ? "emerald" : "amber"}>
                  {payslip.auto_matched ? "Auto-match" : "Manuale"}
                </MicroBadge>
                {payslip.status && <MicroBadge tone="slate">{payslip.status}</MicroBadge>}
              </>
            )}
          </div>
        </header>
        <div className="hr-portal__meta">
          <span>Caricata il {formatDate(payslip.created_at)}</span>
          {payslip.downloaded_at && <span>Scaricata il {formatDate(payslip.downloaded_at)}</span>}
        </div>
        <div className={layout === "bacheca" ? "hr-portal__list-actions" : "hr-portal__actions"}>
          <a
            className={layout === "bacheca" ? "hr-portal__button hr-portal__button--primary" : "hr-portal__link"}
            href={payslip.download_url || payslip.file}
            target="_blank"
            rel="noreferrer"
          >
            Scarica busta paga
          </a>
          {layout !== "bacheca" && isOwner && (
            <button
              className="hr-portal__button hr-portal__button--ghost"
              onClick={() => onDownloadRenamed(payslip.id)}
              disabled={downloadingRenamed === payslip.id}
            >
              {downloadingRenamed === payslip.id ? "Download…" : "Scarica rinominato"}
            </button>
          )}
          {layout !== "bacheca" && canRegenerate && (
            <button
              className="hr-portal__button hr-portal__button--ghost"
              onClick={() => onRegeneratePeriod(payslip.id)}
              disabled={regenerating === payslip.id}
            >
              {regenerating === payslip.id ? "Rigenerazione…" : "Rigenera periodo"}
            </button>
          )}
        </div>
      </article>
    ))}
  </div>
);


const SegmentPreviewModal = ({
  open,
  segment,
  segments,
  selectedSegmentKey,
  loading,
  onClose,
  onSelectSegment,
  onQuickAssign,
  onQuickConfirmPeriod,
  restoreFocusRef,
  previewLocked,
}) => {
  const [currentPageIdx, setCurrentPageIdx] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragState, setDragState] = useState(null);
  const dialogRef = useRef(null);
  const touchStartRef = useRef(null);
  const titleId = useId();
  const descId = useId();
  const pageCount = Array.isArray(segment?.preview_pages) ? segment.preview_pages.length : 0;

  useEffect(() => {
    if (!open) return;
    setCurrentPageIdx(0);
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }, [open, selectedSegmentKey]);

  useEffect(() => {
    if (!open) return;
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        onClose?.();
        return;
      }
      if (event.key === "ArrowRight") {
        setCurrentPageIdx((value) => Math.min(Math.max(0, pageCount - 1), value + 1));
      }
      if (event.key === "ArrowLeft") {
        setCurrentPageIdx((value) => Math.max(0, value - 1));
      }
      if (event.altKey && event.key === "ArrowUp") {
        const currentSegmentIdx = segments.findIndex((item) => item?.segment_key === selectedSegmentKey);
        if (currentSegmentIdx > 0) onSelectSegment?.(segments[currentSegmentIdx - 1]?.segment_key);
      }
      if (event.altKey && event.key === "ArrowDown") {
        const currentSegmentIdx = segments.findIndex((item) => item?.segment_key === selectedSegmentKey);
        if (currentSegmentIdx >= 0 && currentSegmentIdx < segments.length - 1) onSelectSegment?.(segments[currentSegmentIdx + 1]?.segment_key);
      }
      if (event.key === "Tab") {
        const focusables = dialogRef.current?.querySelectorAll(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (!focusables?.length) return;
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement;
        if (event.shiftKey && active === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && active === last) {
          event.preventDefault();
          first.focus();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose, onSelectSegment, pageCount, segments, selectedSegmentKey]);

  useEffect(() => {
    if (!open) return;
    dialogRef.current?.focus();
    return () => {
      restoreFocusRef?.current?.focus?.();
    };
  }, [open, restoreFocusRef]);

  useEffect(() => {
    if (!open) return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open || !segment) return null;

  const pages = segment.preview_pages || [];
  const currentPage = pages[currentPageIdx] || null;
  const currentSegmentIdx = segments.findIndex((item) => item?.segment_key === selectedSegmentKey);
  const noImageAvailable = !loading && pages.length === 0;
  const previewErrorCode = segment?.preview_error_code;
  const canPan = zoom > 1;

  const handleZoom = (delta) => {
    setZoom((value) => {
      const next = Math.max(1, Math.min(3, Number((value + delta).toFixed(2))));
      if (next === 1) setPan({ x: 0, y: 0 });
      return next;
    });
  };

  const handlePointerDown = (event) => {
    if (!canPan) return;
    setDragState({ startX: event.clientX, startY: event.clientY, originX: pan.x, originY: pan.y });
  };

  const handlePointerMove = (event) => {
    if (!dragState || !canPan) return;
    const deltaX = event.clientX - dragState.startX;
    const deltaY = event.clientY - dragState.startY;
    setPan({ x: dragState.originX + deltaX, y: dragState.originY + deltaY });
  };

  const handlePointerEnd = () => setDragState(null);

  const handleTouchStart = (event) => {
    touchStartRef.current = event.touches?.[0]?.clientX ?? null;
  };

  const handleTouchEnd = (event) => {
    const startX = touchStartRef.current;
    const endX = event.changedTouches?.[0]?.clientX;
    if (startX == null || endX == null || canPan) return;
    const delta = endX - startX;
    if (Math.abs(delta) < 50) return;
    if (delta < 0) {
      setCurrentPageIdx((value) => Math.min(pages.length - 1, value + 1));
    } else {
      setCurrentPageIdx((value) => Math.max(0, value - 1));
    }
    touchStartRef.current = null;
  };

  return (
    <div className="hr-portal__preview-modal-backdrop" onClick={onClose}>
      <div
        className="hr-portal__preview-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        tabIndex={-1}
        ref={dialogRef}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="hr-portal__preview-modal-toolbar hr-portal__preview-modal-toolbar--sticky">
          <strong id={titleId}>{segment.segment_key || "Segmento"}</strong>
          <div className="hr-portal__preview-modal-toolbar-actions">
            <button type="button" className="hr-portal__upload-toggle" onClick={onQuickAssign} disabled={previewLocked}>Assegna</button>
            <button type="button" className="hr-portal__upload-toggle" onClick={onQuickConfirmPeriod} disabled={previewLocked}>Conferma periodo</button>
            <button type="button" className="hr-portal__upload-clear" onClick={onClose}>Chiudi</button>
          </div>
        </div>

        <div className="hr-portal__preview-modal-meta" id={descId}>
          <span>Utente suggerito: {segment?.user?.full_name || segment?.identifier || "N/D"}</span>
          <span>Periodo: {segment?.period_label || "N/D"}</span>
          <span>Confidence: {segment?.match_score || 0}/{segment?.match_threshold || 100}</span>
          <span>Pagine segmento: {segment?.page_start || "-"}–{segment?.page_end || "-"}</span>
        </div>

        <div
          className={`hr-portal__preview-modal-stage ${canPan ? "is-draggable" : ""}`}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerEnd}
          onPointerLeave={handlePointerEnd}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          {loading ? (
            <div className="hr-portal__upload-snippet">Rendering preview in corso…</div>
          ) : currentPage?.image_url ? (
            <img
              src={currentPage.image_url}
              alt={`Pagina ${currentPage.page_index}`}
              style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}
            />
          ) : (
            <div className="hr-portal__upload-snippet">
              {previewErrorCode === "segment_preview_unavailable"
                ? "Anteprima non disponibile per il segmento: usa il testo estratto per la verifica."
                : "Anteprima immagine non disponibile per questo segmento."}
            </div>
          )}
        </div>

        <div className="hr-portal__preview-modal-toolbar">
          <div>
            <button type="button" className="hr-portal__upload-toggle" onClick={() => handleZoom(-0.2)}>-</button>
            <button type="button" className="hr-portal__upload-toggle" onClick={() => handleZoom(0.2)}>+</button>
            <span className="hr-portal__muted">Zoom {Math.round(zoom * 100)}%</span>
          </div>
          <div>
            <button
              type="button"
              className="hr-portal__upload-toggle"
              disabled={currentPageIdx <= 0 || pages.length === 0}
              onClick={() => setCurrentPageIdx((value) => Math.max(0, value - 1))}
            >
              Prev pagina
            </button>
            <button
              type="button"
              className="hr-portal__upload-toggle"
              disabled={currentPageIdx >= pages.length - 1 || pages.length === 0}
              onClick={() => setCurrentPageIdx((value) => Math.min(pages.length - 1, value + 1))}
            >
              Next pagina
            </button>
            <span className="hr-portal__muted">Pagina {pages.length ? currentPageIdx + 1 : 0}/{pages.length}</span>
          </div>
        </div>

        {pages.length > 1 && (
          <div className="hr-portal__preview-modal-stepper" role="tablist" aria-label="Pagine segmento">
            {pages.map((page, idx) => (
              <button
                key={`${page.page_index}-${idx}`}
                type="button"
                role="tab"
                aria-selected={idx === currentPageIdx}
                className={`hr-portal__preview-dot ${idx === currentPageIdx ? "is-active" : ""}`}
                onClick={() => setCurrentPageIdx(idx)}
              >
                {idx + 1}
              </button>
            ))}
          </div>
        )}

        <div className="hr-portal__preview-modal-toolbar">
          <div>
            <button
              type="button"
              className="hr-portal__upload-toggle"
              disabled={currentSegmentIdx <= 0}
              onClick={() => onSelectSegment(segments[currentSegmentIdx - 1]?.segment_key)}
            >
              Prev segmento
            </button>
            <button
              type="button"
              className="hr-portal__upload-toggle"
              disabled={currentSegmentIdx < 0 || currentSegmentIdx >= segments.length - 1}
              onClick={() => onSelectSegment(segments[currentSegmentIdx + 1]?.segment_key)}
            >
              Next segmento
            </button>
          </div>
          {noImageAvailable && <span className="hr-portal__muted">Fallback attivo: solo testo estratto.</span>}
          <span className="hr-portal__muted">Scorciatoie: ESC chiude · ←/→ cambia pagina · Alt+↑/↓ cambia segmento</span>
        </div>
      </div>
    </div>
  );
};

const BatchUploadPreview = ({
  file,
  preview,
  ocrEnabled,
  ocrAvailable,
  assignments,
  assignmentInputs,
  periodInputs,
  assigneeOptions,
  assigneeLoading,
  onAssigneeInput,
  onAssigneeSelect,
  onAssigneeClear,
  bulkAssigneeInput,
  bulkAssigneeSelected,
  onBulkAssigneeInput,
  onBulkAssigneeSelect,
  onBulkAssigneeClear,
  bulkPeriodValue,
  onBulkPeriodInput,
  onAssignAllUnmatched,
  onApplyPeriodToAll,
  onPeriodInput,
  onPeriodClear,
  assignmentCount,
  periodCount,
  onAssigneeClearAll,
  previewLocked,
  onPreviewLockToggle,
  previewLocking,
}) => {
  if (!file) return null;

  const isPdf = file?.name?.toLowerCase?.().endsWith(".pdf");
  const isZip = file?.name?.toLowerCase?.().endsWith(".zip");
  const segments = preview?.segments || [];
  const scanPages = preview?.scan_pages || [];
  const [showOnlyUnmatched, setShowOnlyUnmatched] = useState(false);
  const [isPreviewModalOpen, setIsPreviewModalOpen] = useState(false);
  const [selectedSegmentKey, setSelectedSegmentKey] = useState("");
  const segmentButtonRefs = useRef({});
  const activePreviewButtonRef = useRef(null);
  const isLoading = preview?.loading;
  const error = preview?.error;
  const errorCode = preview?.errorCode;
  const liveMode = preview?.liveMode || "idle";
  const fallbackActive = Boolean(preview?.fallbackActive);
  const capabilitiesState = preview?.capabilitiesState || {};
  const previewType = preview?.preview_type;
  const zipSummary = previewType === "zip" ? preview?.summary : null;
  const isSegmentManuallyAssigned = useCallback(
    (segment) => {
      const segmentKey = segment?.segment_key;
      return Boolean(segment?.manual_assigned || assignments?.[segmentKey]?.userId || periodInputs?.[segmentKey]);
    },
    [assignments, periodInputs]
  );
  const reviewCount = segments.filter((segment) => !segment?.auto_matched && !isSegmentManuallyAssigned(segment)).length;
  const sortedSegments = useMemo(() => {
    if (!segments.length) return segments;
    return [...segments].sort((a, b) => {
      const priority = (segment) => {
        const manuallyAssigned = isSegmentManuallyAssigned(segment);
        if (!segment?.auto_matched && !manuallyAssigned) return 0;
        if (segment?.auto_matched && !manuallyAssigned) return 1;
        return 2;
      };
      return priority(a) - priority(b);
    });
  }, [segments, isSegmentManuallyAssigned]);
  const filteredSegments = showOnlyUnmatched
    ? sortedSegments.filter((segment) => !segment?.auto_matched && !isSegmentManuallyAssigned(segment))
    : sortedSegments;
  const segmentList = filteredSegments.length
    ? filteredSegments
    : segments.length
      ? segments
      : ["Segmento 01", "Segmento 02", "Segmento 03"];
  const selectedSegment = useMemo(
    () => segments.find((segment) => segment?.segment_key === selectedSegmentKey) || null,
    [segments, selectedSegmentKey]
  );

  const openSegmentPreview = useCallback((segmentKey) => {
    setSelectedSegmentKey(segmentKey);
    setIsPreviewModalOpen(true);
    activePreviewButtonRef.current = segmentButtonRefs.current[segmentKey] || null;
  }, []);

  const focusAssigneeField = useCallback((segmentKey) => {
    const input = document.getElementById(`segment-assignee-${segmentKey}`);
    input?.focus?.();
  }, []);

  const focusPeriodField = useCallback((segmentKey) => {
    const input = document.getElementById(`segment-period-${segmentKey}`);
    input?.focus?.();
  }, []);

  const nextStepHint = isLoading
    ? "Attendi la fine della scansione per iniziare la revisione."
    : previewLocked
      ? "Preview confermata: puoi procedere con la creazione del batch."
      : reviewCount > 0
        ? "Assegna i segmenti da verificare e poi conferma la preview."
        : segments.length > 0
          ? "Controlla rapidamente i segmenti e conferma la preview."
          : "Carica un file PDF o ZIP per iniziare.";

  return (
    <div className="hr-portal__upload-preview">
      <div className="hr-portal__upload-header">
        <div>
          <p className="hr-portal__eyebrow">Anteprima in tempo reale</p>
          <h4>{isLoading ? "Scansione documento" : "Anteprima segmenti"}</h4>
        </div>
        <div className="hr-portal__upload-header-actions">
          {segments.length > 0 && (
            <button
              type="button"
              className="hr-portal__upload-toggle"
              onClick={() => setShowOnlyUnmatched((prev) => !prev)}
            >
              {showOnlyUnmatched ? "Mostra tutto" : "Solo da verificare"}
            </button>
          )}
          {segments.length > 0 && (
            <button
              type="button"
              className="hr-portal__upload-lock"
              onClick={onPreviewLockToggle}
              disabled={previewLocking}
            >
              {previewLocking ? "Conferma…" : previewLocked ? "Modifica" : "Conferma"}
            </button>
          )}
          {reviewCount > 0 && <span className="hr-portal__badge hr-portal__badge--amber">{reviewCount} da verificare</span>}
          {assignmentCount > 0 && (
            <>
              <span className="hr-portal__badge hr-portal__badge--indigo">
                {assignmentCount} assegnazioni
              </span>
              <button type="button" className="hr-portal__upload-clear" onClick={onAssigneeClearAll}>
                Reset
              </button>
            </>
          )}
          {periodCount > 0 && (
            <span className="hr-portal__badge hr-portal__badge--slate">
              {periodCount} periodi manuali
            </span>
          )}
          {ocrEnabled != null && (
            <span className={`hr-portal__badge ${ocrAvailable ? "hr-portal__badge--emerald" : "hr-portal__badge--rose"}`}>
              OCR {ocrAvailable ? "attivo" : "non disponibile"}
            </span>
          )}
          <span className={`hr-portal__badge ${isLoading ? "hr-portal__badge--indigo" : "hr-portal__badge--amber"}`}>
            {isLoading ? "Live" : "Preview"}
          </span>
          {liveMode === "polling" && <span className="hr-portal__badge hr-portal__badge--amber">Modalità polling</span>}
          {capabilitiesState?.renderingAvailable === false && (
            <span className="hr-portal__badge hr-portal__badge--slate">Rendering non disponibile</span>
          )}
          {capabilitiesState?.ocrEnabled && capabilitiesState?.ocrAvailable === false && (
            <span className="hr-portal__badge hr-portal__badge--rose">OCR richiesto ma non disponibile</span>
          )}
        </div>
      </div>
      {previewLocked && (
        <div className="hr-portal__upload-locked">
          Assegnazioni confermate. Premi “Modifica” per riaprire l’editing.
        </div>
      )}
      {!zipSummary && segments.length > 0 && (
        <div className="hr-portal__upload-bulk">
          <div className="hr-portal__upload-bulk-field">
            <span className="hr-portal__muted">Assegna tutti i segmenti senza match</span>
            <AssigneeInput
              value={bulkAssigneeInput}
              onInput={onBulkAssigneeInput}
              onSelect={onBulkAssigneeSelect}
              suggestions={assigneeOptions?.segmentKey === "__bulk__" ? assigneeOptions?.items : []}
              loading={assigneeLoading?.segmentKey === "__bulk__" ? assigneeLoading.loading : false}
              disabled={previewLocked}
              placeholder="Seleziona assegnatario"
            />
            <div className="hr-portal__upload-bulk-actions">
              <button
                type="button"
                className="hr-portal__button hr-portal__button--ghost"
                onClick={() => onAssignAllUnmatched(segments, bulkAssigneeSelected)}
                disabled={previewLocked || !bulkAssigneeSelected}
              >
                Applica assegnazione
              </button>
              {bulkAssigneeInput && (
                <button
                  type="button"
                  className="hr-portal__upload-clear"
                  onClick={onBulkAssigneeClear}
                  disabled={previewLocked}
                >
                  Svuota
                </button>
              )}
            </div>
          </div>
          <div className="hr-portal__upload-bulk-field">
            <span className="hr-portal__muted">Applica periodo a tutti i segmenti</span>
            <input
              className="hr-portal__input hr-portal__input--compact"
              placeholder="Periodo (es. 2025-01)"
              value={bulkPeriodValue}
              onChange={(event) => onBulkPeriodInput(event.target.value)}
              disabled={previewLocked}
            />
            <div className="hr-portal__upload-bulk-actions">
              <button
                type="button"
                className="hr-portal__button hr-portal__button--ghost"
                onClick={() => onApplyPeriodToAll(segments, bulkPeriodValue)}
                disabled={previewLocked || !bulkPeriodValue}
              >
                Applica periodo
              </button>
            </div>
          </div>
        </div>
      )}
      {zipSummary && (
        <div className="hr-portal__upload-summary">
          <div className="hr-portal__upload-summary-title">Anteprima ZIP</div>
          <div className="hr-portal__upload-summary-grid">
            <span className="hr-portal__muted">
              {zipSummary.total_pdfs} PDF su {zipSummary.total_files} file
            </span>
            <span className="hr-portal__muted">
              Campione: {zipSummary.sampled_files} file · {zipSummary.page_limit} pagine max
            </span>
          </div>
          <div className="hr-portal__upload-summary-badges">
            <Badge tone="indigo">{zipSummary.auto_match_rate}% auto-match</Badge>
            <Badge tone="slate">{zipSummary.auto_matched_count} match certi</Badge>
            {zipSummary.errors_count > 0 && <Badge tone="rose">{zipSummary.errors_count} errori</Badge>}
          </div>
        </div>
      )}
      <div className="hr-portal__upload-stage">
        {scanPages.length > 0 ? (
          <div className="hr-portal__upload-scans" role="list" aria-label="Anteprima pagine rilevate">
            {scanPages.slice(0, 6).map((page) => (
              <a
                key={`${page.page_index}-${page.image_url}`}
                href={page.image_url}
                target="_blank"
                rel="noreferrer"
                className="hr-portal__upload-scan"
                role="listitem"
              >
                <img src={page.image_url} alt={`Anteprima pagina ${page.page_index}`} loading="lazy" />
                <span>Pag. {page.page_index}</span>
              </a>
            ))}
          </div>
        ) : (
          <div className="hr-portal__upload-pages">
            <div className="hr-portal__upload-page" />
            <div className="hr-portal__upload-page" />
            <div className="hr-portal__upload-page" />
          </div>
        )}
        <div className="hr-portal__upload-scanline" />
        <div className="hr-portal__upload-roll" />
      </div>
      <div className="hr-portal__upload-cards">
        {segmentList.map((segment, index) => {
          const label = typeof segment === "string" ? segment : `Segmento ${String(index + 1).padStart(2, "0")}`;
          const pageStart = segment?.page_start ?? 1;
          const pageEnd = segment?.page_end ?? 2;
          const identifier = segment?.identifier;
          const fileName = segment?.file_name;
          const segmentKey = segment?.segment_key || label;
          const localAssigned = Boolean(assignments?.[segmentKey]?.userId);
          const localPeriod = Boolean(periodInputs?.[segmentKey]);
          const manualAssigned = segment?.manual_assigned || localAssigned || localPeriod;
          const matchScore = segment?.match_score ?? 0;
          const matchThreshold = segment?.match_threshold ?? 0;
          const matchRatio = matchThreshold ? matchScore / matchThreshold : 0;
          const confidenceLabel =
            matchRatio >= 1
              ? "Match alto"
              : matchRatio >= 0.7
                ? "Match medio"
                : matchScore > 0
                  ? "Match basso"
                  : "Nessun match";
          const confidenceTone = matchRatio >= 1 ? "emerald" : matchRatio >= 0.7 ? "amber" : "rose";
          const textSource = segment?.text_source || "missing";
          const textSourceLabel =
            textSource === "ocr"
              ? "OCR"
              : textSource === "pdf"
                ? "Testo PDF"
                : textSource === "mixed"
                  ? "Testo misto"
                  : "Testo mancante";
          const textSourceTone = textSource === "missing" ? "rose" : textSource === "ocr" ? "indigo" : "slate";
          const isReview = !manualAssigned && !segment?.auto_matched;
          const snippet = segment?.text_preview;
          const segmentError = segment?.error;
          const statusLabel = segmentError
            ? "Errore preview"
            : manualAssigned
              ? "Assegnazione manuale"
              : segment?.auto_matched
                ? "Auto-match pronto"
                : "Match da verificare";
          const statusClass = manualAssigned || segment?.auto_matched ? "hr-portal__upload-card--matched" : "hr-portal__upload-card--review";
          const assignmentInput = assignmentInputs?.[segmentKey];
          const periodInput = periodInputs?.[segmentKey];
          const periodInvalid =
            periodInput && !/^20\\d{2}-(0[1-9]|1[0-2])$/.test(periodInput);
          return (
            <div
              key={label}
              className={`hr-portal__upload-card ${segments.length ? statusClass : ""}`}
              style={{ animationDelay: `${index * 0.12}s` }}
            >
              <span className="hr-portal__eyebrow">{label}</span>
              <strong>{segments.length ? statusLabel : "Auto-match in corso"}</strong>
              {segments.length && (
                <div className="hr-portal__upload-card-meta">
                  <MicroBadge tone={confidenceTone}>{confidenceLabel}</MicroBadge>
                  <MicroBadge tone={textSourceTone}>{textSourceLabel}</MicroBadge>
                  {isReview && <MicroBadge tone="rose">Da verificare</MicroBadge>}
                </div>
              )}
              <span className="hr-portal__muted">
                {segments.length && segment?.page_start != null
                  ? `Pagine ${pageStart}–${pageEnd}`
                  : segments.length && segment?.page_count
                    ? `Pagine totali ${segment.page_count}`
                    : "Preview pagine 1–2"}
              </span>
              {segments.length && fileName && <span className="hr-portal__muted">{fileName}</span>}
              {segments.length && identifier && <span className="hr-portal__muted">{identifier}</span>}
              {segments.length && (
                <div className="hr-portal__upload-snippet">
                  {segmentError || snippet || "Nessun testo rilevato per il segmento."}
                </div>
              )}
              {segments.length && (
                <button
                  type="button"
                  className="hr-portal__upload-toggle"
                  onClick={() => openSegmentPreview(segmentKey)}
                  ref={(node) => {
                    if (node) segmentButtonRefs.current[segmentKey] = node;
                  }}
                >
                  Apri preview
                </button>
              )}
              {segments.length && (
                <div className="hr-portal__upload-assign">
                  <AssigneeInput
                    inputId={`segment-assignee-${segmentKey}`}
                    value={assignmentInput || ""}
                    onInput={(value) => onAssigneeInput(segmentKey, value)}
                    onSelect={(user) => onAssigneeSelect(segmentKey, user)}
                    suggestions={assigneeOptions?.segmentKey === segmentKey ? assigneeOptions?.items : []}
                    loading={assigneeLoading?.segmentKey === segmentKey ? assigneeLoading.loading : false}
                    disabled={previewLocked}
                    placeholder="Assegna manualmente"
                  />
                  <input
                    id={`segment-period-${segmentKey}`}
                    className="hr-portal__input hr-portal__input--compact"
                    placeholder="Periodo (es. 2025-01)"
                    value={periodInput || ""}
                    onChange={(event) => onPeriodInput(segmentKey, event.target.value)}
                    disabled={previewLocked}
                  />
                  {periodInvalid && (
                    <span className="hr-portal__upload-warning">Formato periodo non valido</span>
                  )}
                  {periodInput && (
                    <button
                      type="button"
                      className="hr-portal__upload-clear hr-portal__upload-clear--inline"
                      onClick={() => onPeriodClear(segmentKey)}
                      disabled={previewLocked}
                    >
                      Rimuovi periodo
                    </button>
                  )}
                  {assignmentInput && (
                    <div className="hr-portal__upload-assigned">
                      <span className="hr-portal__muted">Assegnato: {assignmentInput}</span>
                      <button
                        type="button"
                        className="hr-portal__upload-clear"
                        onClick={() => onAssigneeClear(segmentKey)}
                        disabled={previewLocked}
                      >
                        Rimuovi
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <p className="hr-portal__muted hr-portal__upload-hint">{nextStepHint}</p>
      {fallbackActive && !error && (
        <div className="hr-portal__banner hr-portal__banner--warning">
          Connessione stream non stabile: aggiornamento automatico in polling attivo.
        </div>
      )}
      {error ? (
        <div className="hr-portal__banner hr-portal__banner--error">
          {error}
          {errorCode ? <div className="hr-portal__muted">Codice errore: {errorCode}</div> : null}
        </div>
      ) : (
        <p className="hr-portal__muted hr-portal__upload-hint">
          {isPdf
            ? "Anteprima sincronizzata con lo split reale: aggiorna i parametri per ricalcolare."
            : isZip
              ? "Anteprima ZIP: viene analizzato un campione iniziale dei file."
              : "L'anteprima è disponibile per PDF singoli o ZIP."}
        </p>
      )}
      {!error && isPdf && !isLoading && scanPages.length === 0 && (
        <p className="hr-portal__muted hr-portal__upload-hint">
          Anteprima grafica non disponibile: utilizzo testo estratto e segmentazione automatica.
        </p>
      )}
      <SegmentPreviewModal
        open={isPreviewModalOpen}
        segment={selectedSegment}
        segments={segments}
        selectedSegmentKey={selectedSegmentKey}
        loading={Boolean(isLoading)}
        onClose={() => setIsPreviewModalOpen(false)}
        onSelectSegment={(segmentKey) => setSelectedSegmentKey(segmentKey)}
        onQuickAssign={() => {
          if (!selectedSegment || previewLocked) {
            if (selectedSegmentKey) focusAssigneeField(selectedSegmentKey);
            setIsPreviewModalOpen(false);
            return;
          }
          if (selectedSegment?.user?.id) {
            onAssigneeSelect(selectedSegmentKey, selectedSegment.user);
          }
          focusAssigneeField(selectedSegmentKey);
          setIsPreviewModalOpen(false);
        }}
        onQuickConfirmPeriod={() => {
          if (!selectedSegmentKey || previewLocked) {
            if (selectedSegmentKey) focusPeriodField(selectedSegmentKey);
            setIsPreviewModalOpen(false);
            return;
          }
          const periodValue =
            normalizePeriodMachine(selectedSegment?.period_machine) ||
            normalizePeriodMachine(selectedSegment?.manual_period_label);
          if (periodValue) {
            onPeriodInput(selectedSegmentKey, periodValue);
          }
          focusPeriodField(selectedSegmentKey);
          setIsPreviewModalOpen(false);
        }}
        restoreFocusRef={activePreviewButtonRef}
        previewLocked={previewLocked}
      />
    </div>
  );
};

const PayslipBatchForm = ({
  form,
  onChange,
  onSubmit,
  creating,
  preview,
  assignments,
  assignmentInputs,
  periodInputs,
  assigneeOptions,
  assigneeLoading,
  onAssigneeInput,
  onAssigneeSelect,
  onAssigneeClear,
  bulkAssigneeInput,
  bulkAssigneeSelected,
  onBulkAssigneeInput,
  onBulkAssigneeSelect,
  onBulkAssigneeClear,
  bulkPeriodValue,
  onBulkPeriodInput,
  onAssignAllUnmatched,
  onApplyPeriodToAll,
  onPeriodInput,
  onPeriodClear,
  assignmentCount,
  periodCount,
  onAssigneeClearAll,
  previewLocked,
  onPreviewLockToggle,
  previewLocking,
  preSubmitChecklist,
}) => (
  <div className="hr-portal__card hr-portal__card--form">
    <header className="hr-portal__card-header">
      <div>
        <p className="hr-portal__eyebrow">Nuovo batch</p>
        <h3>Carica ZIP/PDF</h3>
      </div>
      <Pill tone="indigo">Matching {form.auto_match_strategy}</Pill>
    </header>
    <div className="hr-portal__form-grid">
      <label className="hr-portal__field hr-portal__field--wide">
        <span>File sorgente</span>
        <input
          type="file"
          accept=".zip,.pdf"
          className="hr-portal__input"
          onChange={(e) => onChange({ ...form, source_file: e.target.files?.[0] || null })}
        />
      </label>
      <label className="hr-portal__field">
        <span>Strategia di match</span>
        <select
          className="hr-portal__input"
          value={form.auto_match_strategy}
          onChange={(e) => onChange({ ...form, auto_match_strategy: e.target.value })}
        >
          <option value="fiscal_code">Codice fiscale</option>
          <option value="username">Username</option>
          <option value="email">Email</option>
          <option value="regex">Regex/CF</option>
        </select>
      </label>
      <label className="hr-portal__field">
        <span>Regex/Hint (opzionale)</span>
        <input
          className="hr-portal__input"
          value={form.manifest_hint}
          onChange={(e) => onChange({ ...form, manifest_hint: e.target.value })}
          placeholder="es. (?P<cf>[A-Z0-9]{16})"
        />
      </label>
      <label className="hr-portal__field">
        <span>OCR</span>
        <div className="hr-portal__checkbox">
          <input
            type="checkbox"
            checked={form.enable_ocr}
            onChange={(e) => onChange({ ...form, enable_ocr: e.target.checked })}
          />
          <span>Abilita OCR per PDF immagine</span>
        </div>
      </label>
      <label className="hr-portal__field">
        <span>Lingue OCR</span>
        <input
          className="hr-portal__input"
          value={form.ocr_languages}
          onChange={(e) => onChange({ ...form, ocr_languages: e.target.value })}
          placeholder="ita+eng"
        />
      </label>
    </div>
    <BatchUploadPreview
      file={form.source_file}
      preview={preview}
      ocrEnabled={preview?.ocr_enabled}
      ocrAvailable={preview?.ocr_available}
      assignments={assignments}
      assignmentInputs={assignmentInputs}
      periodInputs={periodInputs}
      assigneeOptions={assigneeOptions}
      assigneeLoading={assigneeLoading}
      onAssigneeInput={onAssigneeInput}
      onAssigneeSelect={onAssigneeSelect}
      onAssigneeClear={onAssigneeClear}
      bulkAssigneeInput={bulkAssigneeInput}
      bulkAssigneeSelected={bulkAssigneeSelected}
      onBulkAssigneeInput={onBulkAssigneeInput}
      onBulkAssigneeSelect={onBulkAssigneeSelect}
      onBulkAssigneeClear={onBulkAssigneeClear}
      bulkPeriodValue={bulkPeriodValue}
      onBulkPeriodInput={onBulkPeriodInput}
      onAssignAllUnmatched={onAssignAllUnmatched}
      onApplyPeriodToAll={onApplyPeriodToAll}
      onPeriodInput={onPeriodInput}
      onPeriodClear={onPeriodClear}
      assignmentCount={assignmentCount}
      periodCount={periodCount}
      onAssigneeClearAll={onAssigneeClearAll}
      previewLocked={previewLocked}
      onPreviewLockToggle={onPreviewLockToggle}
      previewLocking={previewLocking}
    />
    {preSubmitChecklist && (
      <div className="hr-portal__upload-checklist">
        <div className="hr-portal__upload-checklist-header">
          <p className="hr-portal__eyebrow">Checklist pre-submit</p>
          <label className="hr-portal__checkbox">
            <input
              type="checkbox"
              checked={Boolean(preSubmitChecklist.strictMode)}
              onChange={(event) => preSubmitChecklist.onStrictModeChange?.(event.target.checked)}
            />
            <span>Strict mode (blocca invio se ci sono criticità)</span>
          </label>
        </div>
        <div className="hr-portal__upload-checklist-grid">
          <div className={`hr-portal__upload-checkitem ${preSubmitChecklist.unresolvedCount > 0 ? "is-warning" : "is-ok"}`}>
            <strong>{preSubmitChecklist.unresolvedCount}</strong>
            <span>segmenti senza destinatario</span>
          </div>
          <div className={`hr-portal__upload-checkitem ${preSubmitChecklist.invalidPeriodsCount > 0 ? "is-warning" : "is-ok"}`}>
            <strong>{preSubmitChecklist.invalidPeriodsCount}</strong>
            <span>periodi invalidi</span>
          </div>
          <div className={`hr-portal__upload-checkitem ${preSubmitChecklist.previewIssuesCount > 0 ? "is-warning" : "is-ok"}`}>
            <strong>{preSubmitChecklist.previewIssuesCount}</strong>
            <span>segmenti con errore preview</span>
          </div>
        </div>
        {preSubmitChecklist.unresolvedSegments?.length > 0 && (
          <div className="hr-portal__upload-review-list">
            <span className="hr-portal__muted">Da verificare subito:</span>
            {preSubmitChecklist.unresolvedSegments.slice(0, 6).map((segment) => (
              <div key={segment.segment_key || `${segment.page_start}-${segment.page_end}`} className="hr-portal__upload-review-item">
                <strong>{segment.segment_key || `p${segment.page_start}`}</strong>
                <span>
                  {segment.identifier || "Identificativo mancante"} · pagine {segment.page_start}-{segment.page_end}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    )}
    <div className="hr-portal__actions">
      <button className="hr-portal__button" onClick={onSubmit} disabled={creating}>
        {creating ? "Caricamento…" : "Crea ed esegui batch"}
      </button>
    </div>
  </div>
);

const PayslipBatchCard = ({ batch, onProcess, processing, onDownloadZip, downloading, canManage, isOwner }) => {
  const quality = batch.quality_kpis || {};
  const matchRate = batch.auto_match_rate?.toFixed ? batch.auto_match_rate.toFixed(1) : batch.auto_match_rate;
  const errorRate = quality.error_rate?.toFixed ? quality.error_rate.toFixed(1) : quality.error_rate;
  const ocrRate = quality.ocr_success_rate?.toFixed ? quality.ocr_success_rate.toFixed(1) : quality.ocr_success_rate;

  return (
    <article className="hr-portal__card">
      <header className="hr-portal__card-header">
        <div>
          <p className="hr-portal__eyebrow">Batch</p>
          <h3>{batch.id}</h3>
          <p className="hr-portal__muted">Creato {formatDate(batch.created_at)}</p>
        </div>
        <Pill tone={batch.status === "completed" ? "emerald" : batch.status === "failed" ? "rose" : "amber"}>
          {batch.status}
        </Pill>
      </header>
      <div className="hr-portal__meta">
        <span>Totali: {batch.total_items}</span>
        <span>Assegnati: {batch.matched_items}</span>
        <span>Da assegnare: {batch.failed_items}</span>
        <span>Match rate: {matchRate}%</span>
        {quality.error_count != null && <span>Errori: {quality.error_count} ({errorRate}%)</span>}
        {batch.enable_ocr && ocrRate != null && <span>OCR ok: {ocrRate}%</span>}
      </div>
      <div className="hr-portal__stack">
        {(batch.processing_log || []).slice(-4).map((entry, idx) => (
          <div key={idx} className="hr-portal__queue-item">
            <div>
              <p className="hr-portal__eyebrow">{entry.status}</p>
              <h4>{entry.file || entry.detail || entry.identifier || "Evento"}</h4>
            </div>
            {entry.user && <Pill tone="indigo">{entry.user}</Pill>}
          </div>
        ))}
      </div>
      {canManage && (
        <div className="hr-portal__actions">
          <button className="hr-portal__button" onClick={() => onProcess(batch.id)} disabled={processing === batch.id}>
            {processing === batch.id ? "Rielaborazione…" : "Rielabora"}
          </button>
          {isOwner && (
            <button
              className="hr-portal__button hr-portal__button--ghost"
              onClick={() => onDownloadZip(batch.id)}
              disabled={downloading === batch.id}
            >
              {downloading === batch.id ? "Download…" : "Scarica ZIP"}
            </button>
          )}
        </div>
      )}
    </article>
  );
};

const UnmatchedQueue = ({
  items,
  onResolve,
  onSendEmail,
  assignments,
  onAssigneeInput,
  onAssigneeSelect,
  assigneeOptions,
  assigneeLoading,
  hasAssignee,
  setAssignments,
  resolving,
  suggestionsById,
  onLoadSuggestions,
}) => {
  const [previewItemId, setPreviewItemId] = useState("");
  const previewItem = useMemo(() => items.find((item) => item.id === previewItemId) || null, [items, previewItemId]);

  return (
    <div className="hr-portal__queue">
    {items.map((item) => {
      const suggestionsState = suggestionsById?.[item.id] || {};
      const suggestions = suggestionsState.items || [];
      const suggestionsLoading = suggestionsState.loading;
      return (
        <div key={item.id} className="hr-portal__queue-item hr-portal__queue-item--stacked">
          <div className="hr-portal__queue-main">
            <div>
              <p className="hr-portal__eyebrow">Batch {item.batch}</p>
              <h4>{item.identifier || "Anonimo"}</h4>
              <p className="hr-portal__muted">Creato {formatDate(item.created_at)}</p>
              <a className="hr-portal__link" href={item.file} target="_blank" rel="noreferrer">
                Apri PDF
              </a>
            </div>
            <Pill tone="amber">{item.status_display || "DA ASSEGNARE"}</Pill>
          </div>
          <div className="hr-portal__actions">
            <button
              className="hr-portal__button hr-portal__button--ghost"
              onClick={() => onLoadSuggestions(item.id)}
              disabled={suggestionsLoading}
            >
              {suggestionsLoading ? "Suggerimenti…" : "Suggerimenti"}
            </button>
            <button
              className="hr-portal__button hr-portal__button--ghost"
              onClick={() => setPreviewItemId(item.id)}
            >
              Apri preview
            </button>
          </div>
          {suggestions.length > 0 && (
            <div className="hr-portal__pill-row">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion.id}
                  type="button"
                  className="hr-portal__pill hr-portal__pill--indigo"
                  onClick={() => onAssigneeSelect(item.id, suggestion)}
                >
                  {suggestion.display_name || suggestion.username} · {suggestion.score}
                </button>
              ))}
            </div>
          )}
          <div className="hr-portal__form-inline hr-portal__form-inline--wide">
            <AssigneeInput
              inputId={`unmatched-assignee-${item.id}`}
              value={assignments[item.id]?.query || assignments[item.id]?.user || ""}
              onInput={(value) => onAssigneeInput(item.id, value)}
              onSelect={(user) => onAssigneeSelect(item.id, user)}
              suggestions={assigneeOptions}
              loading={assigneeLoading}
              placeholder="Cerca username e seleziona l'assegnatario"
            />
            <input
              id={`unmatched-period-${item.id}`}
              className="hr-portal__input"
              placeholder="Periodo (es. 2025-01)"
              value={assignments[item.id]?.period_label || ""}
              onChange={(e) =>
                setAssignments({ ...assignments, [item.id]: { ...assignments[item.id], period_label: e.target.value } })
              }
            />
            <button
              className="hr-portal__button"
              onClick={() => onResolve(item.id)}
              disabled={resolving === item.id || !hasAssignee(item.id)}
            >
              {resolving === item.id ? "Assegnazione…" : "Assegna busta"}
            </button>
            <button className="hr-portal__button hr-portal__button--ghost" onClick={() => onSendEmail(item)}>
              Invia via email
            </button>
          </div>
        </div>
      );
    })}
      {previewItem && (
        <div className="hr-portal__preview-modal-backdrop" onClick={() => setPreviewItemId("")}>
          <div
            className="hr-portal__preview-modal hr-portal__preview-modal--pdf"
            role="dialog"
            aria-modal="true"
            aria-label="Preview busta da assegnare"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="hr-portal__preview-modal-toolbar hr-portal__preview-modal-toolbar--sticky">
              <strong>{previewItem.identifier || "Busta da assegnare"}</strong>
              <div className="hr-portal__preview-modal-toolbar-actions">
                <button type="button" className="hr-portal__upload-toggle" onClick={() => document.getElementById(`unmatched-assignee-${previewItem.id}`)?.focus?.()}>Assegna</button>
                <button type="button" className="hr-portal__upload-toggle" onClick={() => document.getElementById(`unmatched-period-${previewItem.id}`)?.focus?.()}>Conferma periodo</button>
                <button
                  type="button"
                  className="hr-portal__upload-toggle"
                  onClick={() => {
                    onSendEmail(previewItem);
                    setPreviewItemId("");
                  }}
                >
                  Invia via mail
                </button>
                <button type="button" className="hr-portal__upload-clear" onClick={() => setPreviewItemId("")}>Chiudi</button>
              </div>
            </div>
            <div className="hr-portal__preview-modal-meta">
              <span>Batch: {previewItem.batch}</span>
              <span>Creato: {formatDate(previewItem.created_at)}</span>
              <span>Stato: {previewItem.status_display || "DA ASSEGNARE"}</span>
            </div>
            <div className="hr-portal__preview-modal-stage hr-portal__preview-modal-stage--pdf">
              <iframe src={previewItem.file} title={`Preview ${previewItem.identifier || previewItem.id}`} />
            </div>
            <div className="hr-portal__preview-modal-toolbar">
              <a className="hr-portal__link" href={previewItem.file} target="_blank" rel="noreferrer">Apri PDF in nuova scheda</a>
              <button
                type="button"
                className="hr-portal__button"
                onClick={() => {
                  onResolve(previewItem.id);
                  setPreviewItemId("");
                }}
                disabled={resolving === previewItem.id || !hasAssignee(previewItem.id)}
              >
                {resolving === previewItem.id ? "Assegnazione…" : "Assegna busta"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const NotificationPreferenceForm = ({
  form,
  onChange,
  onSubmit,
  saving,
  onClearQuietHours,
  error,
  success,
  hasPreference,
}) => {
  const hasQuietHours = Boolean(form?.quiet_hours_start && form?.quiet_hours_end);
  return (
    <div className="hr-portal__card hr-portal__card--form">
      <header className="hr-portal__card-header">
        <div>
          <p className="hr-portal__eyebrow">{hasPreference ? "Preferenze personali" : "Prima configurazione"}</p>
          <h3>Canali e quiet hours</h3>
        </div>
        <Pill tone={hasQuietHours ? "indigo" : "slate"}>
          {hasQuietHours ? `${form.quiet_hours_start} → ${form.quiet_hours_end}` : "Sempre attive"}
        </Pill>
      </header>
      <div className="hr-portal__form-grid">
        <div className="hr-portal__field hr-portal__field--wide">
          <span>Canali consentiti</span>
          <p className="hr-portal__muted">Seleziona i canali ammessi per le notifiche HR.</p>
          <div>
            <label className="hr-portal__checkbox">
              <input
                type="checkbox"
                checked={Boolean(form?.allow_email)}
                onChange={(e) => onChange({ ...form, allow_email: e.target.checked })}
              />
              Email
            </label>
            <label className="hr-portal__checkbox">
              <input
                type="checkbox"
                checked={Boolean(form?.allow_push)}
                onChange={(e) => onChange({ ...form, allow_push: e.target.checked })}
              />
              Push
            </label>
            <label className="hr-portal__checkbox">
              <input
                type="checkbox"
                checked={Boolean(form?.allow_sms)}
                onChange={(e) => onChange({ ...form, allow_sms: e.target.checked })}
              />
              SMS
            </label>
          </div>
        </div>
        <label className="hr-portal__field">
          <span>Quiet hours - inizio</span>
          <input
            type="time"
            className="hr-portal__input"
            value={form?.quiet_hours_start || ""}
            onChange={(e) => onChange({ ...form, quiet_hours_start: e.target.value })}
          />
        </label>
        <label className="hr-portal__field">
          <span>Quiet hours - fine</span>
          <input
            type="time"
            className="hr-portal__input"
            value={form?.quiet_hours_end || ""}
            onChange={(e) => onChange({ ...form, quiet_hours_end: e.target.value })}
          />
        </label>
      </div>
      <p className="hr-portal__muted">
        Imposta entrambe le estremità per sospendere le notifiche nella fascia indicata (anche oltre la mezzanotte).
      </p>
      <div className="hr-portal__actions hr-portal__actions--wrap">
        {hasQuietHours && (
          <button className="hr-portal__button hr-portal__button--ghost" onClick={onClearQuietHours}>
            Rimuovi quiet hours
          </button>
        )}
        <button className="hr-portal__button" onClick={onSubmit} disabled={saving}>
          {saving ? "Salvataggio…" : "Salva preferenze"}
        </button>
      </div>
      {error && <div className="hr-portal__banner hr-portal__banner--error">{error}</div>}
      {!error && success && <div className="hr-portal__banner">{success}</div>}
    </div>
  );
};

const TicketComposer = ({ form, onChange, onSubmit, creating }) => (
  <div className="hr-portal__card hr-portal__card--form">
    <header className="hr-portal__card-header">
      <div>
        <p className="hr-portal__eyebrow">Nuovo ticket</p>
        <h3>Sportello d'ascolto</h3>
      </div>
      <Pill tone="amber">{form.priority || "normal"}</Pill>
    </header>
    <div className="hr-portal__form-grid">
      <label className="hr-portal__field">
        <span>Oggetto</span>
        <input
          className="hr-portal__input"
          value={form.subject}
          onChange={(e) => onChange({ ...form, subject: e.target.value })}
          placeholder="Tema del ticket"
        />
      </label>
      <label className="hr-portal__field">
        <span>Priorità</span>
        <select
          className="hr-portal__input"
          value={form.priority}
          onChange={(e) => onChange({ ...form, priority: e.target.value })}
        >
          <option value="low">Bassa</option>
          <option value="normal">Normale</option>
          <option value="high">Alta</option>
        </select>
      </label>
      <label className="hr-portal__field hr-portal__field--wide">
        <span>Messaggio</span>
        <textarea
          className="hr-portal__input"
          rows={3}
          value={form.message}
          onChange={(e) => onChange({ ...form, message: e.target.value })}
          placeholder="Descrivi il problema o la richiesta"
        />
      </label>
      <label className="hr-portal__checkbox">
        <input
          type="checkbox"
          checked={form.is_anonymous}
          onChange={(e) => onChange({ ...form, is_anonymous: e.target.checked })}
        />
        Invia in forma anonima
      </label>
    </div>
    <div className="hr-portal__actions">
      <button className="hr-portal__button" onClick={onSubmit} disabled={creating}>
        {creating ? "Invio…" : "Apri ticket"}
      </button>
    </div>
  </div>
);

const TicketCard = ({
  ticket,
  onAddMessage,
  sendingMessage,
  onClose,
  closing,
  assignmentValue,
  onAssignmentChange,
  onAssigneeSelect,
  assigneeOptions,
  assigneeLoading,
  hasAssignee,
  onAssign,
  assigning,
  canAssign,
}) => {
  const [message, setMessage] = useState("");
  const [isInternal, setIsInternal] = useState(false);

  const handleSend = useCallback(() => {
    if (!message.trim()) return;
    onAddMessage(ticket.id, { body: message.trim(), is_internal: canAssign ? isInternal : false });
    setMessage("");
    setIsInternal(false);
  }, [message, isInternal, onAddMessage, ticket.id, canAssign]);

  const sentimentTone = useMemo(() => {
    if (ticket.sentiment === "negative") return "rose";
    if (ticket.sentiment === "positive") return "emerald";
    if (ticket.sentiment === "neutral") return "indigo";
    return "slate";
  }, [ticket.sentiment]);

  return (
    <article className="hr-portal__card">
      <header className="hr-portal__card-header">
        <div>
          <p className="hr-portal__eyebrow">Ticket #{ticket.id}</p>
          <h3>{ticket.subject}</h3>
        </div>
        <div className="hr-portal__pill-row">
          <Pill tone={ticket.status === "closed" ? "slate" : "amber"}>{ticket.status}</Pill>
          <Pill tone={sentimentTone}>{ticket.sentiment || "sentiment"}</Pill>
        </div>
      </header>
      <p>{ticket.message}</p>
      <div className="hr-portal__meta">
        <span>Priorità {ticket.priority}</span>
        {ticket.due_at && <span>SLA {formatDate(ticket.due_at)}</span>}
      </div>
      {ticket.assigned_to && <p className="hr-portal__muted">Assegnato a {ticket.assigned_to}</p>}
      <div className="hr-portal__messages">
        {ticket.messages && ticket.messages.length > 0 ? (
          ticket.messages.map((msg) => (
            <div key={msg.id} className="hr-portal__message">
              <div className="hr-portal__message-header">
                <span>{msg.is_internal ? "Nota interna" : "Aggiornamento"}</span>
                <span className="hr-portal__muted">{formatDate(msg.created_at)}</span>
              </div>
              <p>{msg.body}</p>
            </div>
          ))
        ) : (
          <p className="hr-portal__muted">Nessun messaggio ancora.</p>
        )}
      </div>
        <div className="hr-portal__actions hr-portal__actions--stacked">
        <div className="hr-portal__quick-replies">
          <p className="hr-portal__eyebrow">Risposte rapide</p>
          <div className="hr-portal__quick-replies-row">
            {QUICK_REPLY_TEMPLATES.map((template) => (
              <button
                key={template.label}
                type="button"
                className="hr-portal__quick-reply"
                onClick={() => setMessage(template.body)}
              >
                {template.label}
              </button>
            ))}
          </div>
        </div>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          className="hr-portal__input"
          placeholder="Aggiungi un aggiornamento"
        />
        {canAssign && (
          <label className="hr-portal__checkbox">
            <input
              type="checkbox"
              checked={isInternal}
              onChange={(e) => setIsInternal(e.target.checked)}
            />
            Nota interna HR
          </label>
        )}
        <div className="hr-portal__actions">
          <button
            className="hr-portal__button"
            onClick={handleSend}
            disabled={sendingMessage === ticket.id}
          >
            {sendingMessage === ticket.id ? "Invio…" : "Invia risposta"}
          </button>
          {canAssign && ticket.status !== "closed" && (
            <div className="hr-portal__stack hr-portal__stack--inline">
              <AssigneeInput
                value={assignmentValue?.query || assignmentValue?.user || ""}
                onInput={(value) => onAssignmentChange(ticket.id, value)}
                onSelect={(user) => onAssigneeSelect(ticket.id, user)}
                suggestions={assigneeOptions}
                loading={assigneeLoading}
                placeholder="Digita username o nome"
              />
              <button
                className="hr-portal__button hr-portal__button--ghost"
                onClick={() => onAssign(ticket.id)}
                disabled={assigning === ticket.id || !hasAssignee(ticket.id)}
              >
                {assigning === ticket.id ? "Assegnazione…" : "Assegna"}
              </button>
            </div>
          )}
          {canAssign && (
            <button
              className="hr-portal__button hr-portal__button--ghost"
              onClick={() => onClose(ticket.id)}
              disabled={closing === ticket.id || ticket.status === "closed"}
            >
              {closing === ticket.id ? "Chiusura…" : "Chiudi ticket"}
            </button>
          )}
        </div>
      </div>
    </article>
  );
};

const HrPortalApp = () => {
  const [error, setError] = useState("");
  const [portalContext, setPortalContext] = useState(null);
  const [contextLoading, setContextLoading] = useState(true);
  const [contextReady, setContextReady] = useState(false);
  const [events, setEvents] = useState([]);
  const [eventsLoading, setEventsLoading] = useState(false);
  const [eventFilters, setEventFilters] = useState({ eventType: "" });
  const [documentAcks, setDocumentAcks] = useState([]);
  const [documentAcksLoading, setDocumentAcksLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [documentsLoading, setDocumentsLoading] = useState(false);
  const [documentFilters, setDocumentFilters] = useState({ search: "", page: 1 });
  const [documentsHasMore, setDocumentsHasMore] = useState(true);
  const [batches, setBatches] = useState([]);
  const [batchesLoading, setBatchesLoading] = useState(false);
  const [payslips, setPayslips] = useState([]);
  const [payslipsLoading, setPayslipsLoading] = useState(false);
  const [payslipFilters, setPayslipFilters] = useState({ search: "", page: 1 });
  const [payslipHasMore, setPayslipHasMore] = useState(true);
  const [unmatched, setUnmatched] = useState([]);
  const [unmatchedLoading, setUnmatchedLoading] = useState(false);
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [selectedUnmatched, setSelectedUnmatched] = useState(null);
  const [emailForm, setEmailForm] = useState({ recipient_email: "", subject: "", body: "" });
  const [emailSuggestions, setEmailSuggestions] = useState([]);
  const [emailSuggestionsLoading, setEmailSuggestionsLoading] = useState(false);
  const [emailSending, setEmailSending] = useState(false);
  const [emailResult, setEmailResult] = useState(null);
  const [emailTestSending, setEmailTestSending] = useState(false);
  const [emailTestResult, setEmailTestResult] = useState(null);
  const [assigneeQuery, setAssigneeQuery] = useState("");
  const [assigneeOptions, setAssigneeOptions] = useState([]);
  const [assigneeLoading, setAssigneeLoading] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [notificationFilters, setNotificationFilters] = useState({ status: "", category: "" });
  const [notificationQuickFilter, setNotificationQuickFilter] = useState({ status: "", category: "" });
  const [notificationForm, setNotificationForm] = useState({
    title: "",
    body: "",
    category: "general",
    scheduled_for: "",
    expires_at: "",
    audience_roles: "",
    cta_label: "",
    cta_url: "",
    cta_type: "primary",
  });
  const [creatingNotification, setCreatingNotification] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [deliveriesByNotification, setDeliveriesByNotification] = useState({});
  const [deliveryLoading, setDeliveryLoading] = useState(null);
  const [deliveryStatus, setDeliveryStatus] = useState("");
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [preference, setPreference] = useState(null);
  const [preferenceForm, setPreferenceForm] = useState(preferenceToForm());
  const [preferenceSaving, setPreferenceSaving] = useState(false);
  const [preferenceStatus, setPreferenceStatus] = useState({ error: "", success: "" });
  const [tickets, setTickets] = useState([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [kpiData, setKpiData] = useState(null);
  const [kpiLoading, setKpiLoading] = useState(false);
  const [kpiWindowDays, setKpiWindowDays] = useState(30);
  const [kpiThresholds, setKpiThresholds] = useState({ completion_min: 85, failure_max: 10, fallback_max: 30 });
  const [correctiveSlaHours, setCorrectiveSlaHours] = useState(72);
  const [incidentAckNote, setIncidentAckNote] = useState("");
  const [incidentAckLoading, setIncidentAckLoading] = useState(false);
  const [incidentResolveForm, setIncidentResolveForm] = useState({ resolution_note: "", root_cause: "", action_items: "" });
  const [incidentResolveLoading, setIncidentResolveLoading] = useState(false);
  const [completingActionId, setCompletingActionId] = useState("");
  const [loading, setLoading] = useState(true);
  const [acknowledging, setAcknowledging] = useState(null);
  const [regenerating, setRegenerating] = useState(null);
  const [batchForm, setBatchForm] = useState({
    source_file: null,
    auto_match_strategy: "fiscal_code",
    manifest_hint: "",
    enable_ocr: false,
    ocr_languages: "ita+eng",
  });
  const ocrEnabled = Boolean(batchForm.enable_ocr);
  const [batchPreview, setBatchPreview] = useState({ loading: false, segments: [], error: "" });
  const [previewAssignments, setPreviewAssignments] = useState({});
  const [previewAssignmentInputs, setPreviewAssignmentInputs] = useState({});
  const [previewPeriodInputs, setPreviewPeriodInputs] = useState({});
  const [previewLocked, setPreviewLocked] = useState(false);
  const [previewLocking, setPreviewLocking] = useState(false);
  const [previewToken, setPreviewToken] = useState(null);
  const [previewAssigneeQuery, setPreviewAssigneeQuery] = useState("");
  const [previewAssigneeTarget, setPreviewAssigneeTarget] = useState("");
  const [previewAssigneeOptions, setPreviewAssigneeOptions] = useState({ segmentKey: "", items: [] });
  const [previewAssigneeLoading, setPreviewAssigneeLoading] = useState({ segmentKey: "", loading: false });
  const [bulkAssigneeInput, setBulkAssigneeInput] = useState("");
  const [bulkAssigneeSelected, setBulkAssigneeSelected] = useState(null);
  const [bulkPeriodValue, setBulkPeriodValue] = useState("");
  const [creatingBatch, setCreatingBatch] = useState(false);
  const [strictPreviewMode, setStrictPreviewMode] = useState(true);
  const [processingBatch, setProcessingBatch] = useState(null);
  const [downloadingBatch, setDownloadingBatch] = useState(null);
  const [unmatchedAssignments, setUnmatchedAssignments] = useState({});
  const [resolvingUnmatched, setResolvingUnmatched] = useState(null);
  const [unmatchedFilters, setUnmatchedFilters] = useState({ status: "to_assign", search: "", company: "", resort: "", period: "" });
  const [unmatchedSuggestions, setUnmatchedSuggestions] = useState({});
  const [sendingMessage, setSendingMessage] = useState(null);
  const [closingTicket, setClosingTicket] = useState(null);
  const [ticketForm, setTicketForm] = useState({
    subject: "",
    message: "",
    is_anonymous: false,
    priority: "normal",
  });
  const [creatingTicket, setCreatingTicket] = useState(false);
  const [ticketFilters, setTicketFilters] = useState({
    status: "",
    priority: "",
    dueWithin: "",
    slaLte: "",
    overdueOnly: false,
  });
  const [assignmentInputs, setAssignmentInputs] = useState({});
  const [assigningTicket, setAssigningTicket] = useState(null);
  const portalMode = useMemo(() => document.getElementById("root")?.dataset?.portalMode || "hr", []);
  const isHrPortal = portalMode === "hr";
  const isHrUser = Boolean(portalContext?.is_hr || portalContext?.is_superuser);
  const isSuperAdmin = Boolean(portalContext?.is_superuser);
  const canManageNotifications = Boolean(portalContext?.permissions?.can_manage_notifications);
  const canManagePayroll = Boolean(portalContext?.permissions?.can_manage_batches);
  const canAssignTickets = Boolean(portalContext?.permissions?.can_assign_tickets);
  const canViewAudit = isSuperAdmin && Boolean(portalContext?.permissions?.can_view_audit);
  const canViewMonitoringWorkspace = Boolean(isHrPortal && (portalContext?.is_hr_admin || portalContext?.is_superuser));
  const isOwner = portalContext?.user_role === 'owner';
  const ticketStep = isHrPortal ? "4" : "1";
  const preferenceStep = isHrPortal ? "6" : "2";
  const showLoading = loading || contextLoading;
  const [downloadingRenamed, setDownloadingRenamed] = useState(null);
  const [bachecaTab, setBachecaTab] = useState("documenti");
  const [bachecaDocumentFilter, setBachecaDocumentFilter] = useState("all");
  const [bachecaNotificationFilter, setBachecaNotificationFilter] = useState("all");
  const [bachecaPayslipFilter, setBachecaPayslipFilter] = useState("all");
  const [showPreviewObservability, setShowPreviewObservability] = useState(false);
  const [workspaceTab, setWorkspaceTab] = useState("operations");

  const handleOpenSidebarMenu = () => {
    const sidebarToggle = document.querySelector('[data-sidebar-toggle]');
    if (sidebarToggle instanceof HTMLElement) {
      sidebarToggle.click();
    }
  };

  useEffect(() => {
    if (workspaceTab === "monitoring" && !canViewMonitoringWorkspace) {
      setWorkspaceTab("operations");
    }
  }, [workspaceTab, canViewMonitoringWorkspace]);

  useEffect(() => {
    if (portalMode !== "bacheca") return undefined;
    document.body.classList.add("hr-portal-bacheca");
    return () => {
      document.body.classList.remove("hr-portal-bacheca");
    };
  }, [portalMode]);

  useEffect(() => {
    setPreviewAssignments({});
    setPreviewAssignmentInputs({});
    setPreviewPeriodInputs({});
    setPreviewLocked(false);
    setPreviewLocking(false);
    setPreviewToken(null);
    setPreviewAssigneeQuery("");
    setPreviewAssigneeTarget("");
    setPreviewAssigneeOptions({ segmentKey: "", items: [] });
    setPreviewAssigneeLoading({ segmentKey: "", loading: false });
    setBulkAssigneeInput("");
    setBulkAssigneeSelected(null);
    setBulkPeriodValue("");
  }, [batchForm.source_file]);

  const handlePreviewSegments = useCallback((segments) => {
    if (!segments?.length) return;
    setPreviewAssignments((prev) => {
      const next = { ...prev };
      segments.forEach((segment) => {
        if (!segment?.manual_assigned || !segment?.user?.id) return;
        const key = segment.segment_key;
        if (key && !next[key]) {
          next[key] = { userId: segment.user.id };
        }
      });
      return next;
    });
    setPreviewAssignmentInputs((prev) => {
      const next = { ...prev };
      segments.forEach((segment) => {
        if (!segment?.manual_assigned || !segment?.user?.id) return;
        const key = segment.segment_key;
        if (key && !next[key]) {
          next[key] = segment.user.display_name || segment.user.username || `${segment.user.id}`;
        }
      });
      return next;
    });
  }, []);

  usePayslipPreviewFlow({
    sourceFile: batchForm.source_file,
    autoMatchStrategy: batchForm.auto_match_strategy,
    manifestHint: batchForm.manifest_hint,
    ocrEnabled,
    ocrLanguages: batchForm.ocr_languages,
    previewLocked,
    setBatchPreview,
    handlePreviewSegments,
  });

  useEffect(() => {
    if (!previewAssigneeQuery || previewAssigneeQuery.length < 2) {
      setPreviewAssigneeOptions({ segmentKey: "", items: [] });
      setPreviewAssigneeLoading({ segmentKey: "", loading: false });
      return;
    }
    const controller = new AbortController();
    const timeout = setTimeout(async () => {
      setPreviewAssigneeLoading({ segmentKey: previewAssigneeTarget, loading: true });
      try {
        const res = await apiClient.get(`/api/hr/assignable-users/?q=${encodeURIComponent(previewAssigneeQuery)}`, {
          signal: controller.signal,
        });
        setPreviewAssigneeOptions({ segmentKey: previewAssigneeTarget, items: res.data || [] });
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error("Errore nella ricerca assegnatari preview", err);
        }
      } finally {
        if (!controller.signal.aborted) {
          setPreviewAssigneeLoading({ segmentKey: previewAssigneeTarget, loading: false });
        }
      }
    }, 200);

    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [previewAssigneeQuery, previewAssigneeTarget]);


  const loadContext = useCallback(async () => {
    setContextLoading(true);
    try {
      const res = await apiClient.get("/api/hr/context/");
      setPortalContext(res.data || {});
    } catch (err) {
      console.error("Errore nel recupero del contesto HR", err);
      setPortalContext({});
      setError("Impossibile determinare i permessi HR.");
    } finally {
      setContextLoading(false);
      setContextReady(true);
    }
  }, [kpiThresholds.completion_min, kpiThresholds.failure_max, kpiThresholds.fallback_max, kpiWindowDays]);

  useEffect(() => {
    if (!assigneeQuery || assigneeQuery.length < 2) {
      setAssigneeOptions([]);
      setAssigneeLoading(false);
      return;
    }
    const controller = new AbortController();
    const timeout = setTimeout(async () => {
      setAssigneeLoading(true);
      try {
        const res = await apiClient.get(`/api/hr/assignable-users/?q=${encodeURIComponent(assigneeQuery)}`, {
          signal: controller.signal,
        });
        setAssigneeOptions(res.data || []);
      } catch (err) {
        if (!controller.signal.aborted) {
          console.error("Errore nella ricerca assegnatari", err);
        }
      } finally {
        if (!controller.signal.aborted) {
          setAssigneeLoading(false);
        }
      }
    }, 200);

    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, [assigneeQuery]);

  const handlePreviewAssigneeInput = useCallback((segmentKey, value) => {
    setPreviewAssigneeTarget(segmentKey);
    setPreviewAssigneeQuery(value);
    setPreviewAssignmentInputs((prev) => ({
      ...prev,
      [segmentKey]: value,
    }));
  }, []);

  const handlePreviewAssigneeSelect = useCallback((segmentKey, user) => {
    const label = user?.display_name || user?.username || `${user?.id}`;
    setPreviewAssignments((prev) => ({
      ...prev,
      [segmentKey]: { userId: user?.id },
    }));
    setPreviewAssignmentInputs((prev) => ({
      ...prev,
      [segmentKey]: label,
    }));
    setPreviewAssigneeOptions({ segmentKey: "", items: [] });
    setPreviewAssigneeQuery("");
  }, []);

  const handlePreviewAssigneeClear = useCallback((segmentKey) => {
    setPreviewAssignments((prev) => {
      if (!prev[segmentKey]) return prev;
      const next = { ...prev };
      delete next[segmentKey];
      return next;
    });
    setPreviewAssignmentInputs((prev) => ({ ...prev, [segmentKey]: "" }));
    setPreviewAssigneeOptions({ segmentKey: "", items: [] });
    setPreviewAssigneeQuery("");
  }, []);

  const handlePreviewAssigneeClearAll = useCallback(() => {
    setPreviewAssignments({});
    setPreviewAssignmentInputs({});
    setPreviewPeriodInputs({});
    setPreviewAssigneeOptions({ segmentKey: "", items: [] });
    setPreviewAssigneeQuery("");
    setBulkAssigneeInput("");
    setBulkAssigneeSelected(null);
    setBulkPeriodValue("");
  }, []);

  const handlePreviewPeriodInput = useCallback((segmentKey, value) => {
    setPreviewPeriodInputs((prev) => ({
      ...prev,
      [segmentKey]: value,
    }));
  }, []);

  const handlePreviewPeriodClear = useCallback((segmentKey) => {
    setPreviewPeriodInputs((prev) => ({ ...prev, [segmentKey]: "" }));
  }, []);

  const handleBulkAssigneeInput = useCallback((value) => {
    setPreviewAssigneeTarget("__bulk__");
    setPreviewAssigneeQuery(value);
    setBulkAssigneeInput(value);
    setBulkAssigneeSelected(null);
  }, []);

  const handleBulkAssigneeSelect = useCallback((user) => {
    const label = user?.display_name || user?.username || `${user?.id}`;
    setBulkAssigneeInput(label);
    setBulkAssigneeSelected(user);
    setPreviewAssigneeOptions({ segmentKey: "", items: [] });
    setPreviewAssigneeQuery("");
  }, []);

  const handleBulkAssigneeClear = useCallback(() => {
    setBulkAssigneeInput("");
    setBulkAssigneeSelected(null);
    setPreviewAssigneeOptions({ segmentKey: "", items: [] });
    setPreviewAssigneeQuery("");
  }, []);

  const handleBulkPeriodInput = useCallback((value) => {
    setBulkPeriodValue(value);
  }, []);

  const handleAssignAllUnmatched = useCallback((segments, user) => {
    if (!user) return;
    setPreviewAssignments((prev) => {
      const next = { ...prev };
      segments.forEach((segment) => {
        const segmentKey = segment?.segment_key;
        if (!segmentKey) return;
        if (segment?.auto_matched || segment?.manual_assigned) return;
        if (next[segmentKey]?.userId) return;
        next[segmentKey] = { userId: user.id };
      });
      return next;
    });
    setPreviewAssignmentInputs((prev) => {
      const next = { ...prev };
      const label = user?.display_name || user?.username || `${user?.id}`;
      segments.forEach((segment) => {
        const segmentKey = segment?.segment_key;
        if (!segmentKey) return;
        if (segment?.auto_matched || segment?.manual_assigned) return;
        if (next[segmentKey]) return;
        next[segmentKey] = label;
      });
      return next;
    });
  }, []);

  const handleApplyPeriodToAll = useCallback((segments, value) => {
    if (!value) return;
    setPreviewPeriodInputs((prev) => {
      const next = { ...prev };
      segments.forEach((segment) => {
        const segmentKey = segment?.segment_key;
        if (!segmentKey) return;
        next[segmentKey] = value;
      });
      return next;
    });
  }, []);

  const handlePreviewLockToggle = useCallback(async () => {
    if (previewLocked) {
      setPreviewLocked(false);
      setPreviewToken(null);
      return;
    }
    if (!batchForm.source_file) {
      setError("Seleziona un PDF o ZIP prima di confermare la preview.");
      return;
    }
    const hasInvalidPeriod = Object.values(previewPeriodInputs || {}).some(
      (value) => value && !/^20\\d{2}-(0[1-9]|1[0-2])$/.test(value)
    );
    if (hasInvalidPeriod) {
      setError("Correggi i periodi non validi prima di confermare.");
      return;
    }
    setPreviewLocking(true);
    try {
      const formData = new FormData();
      formData.append("source_file", batchForm.source_file);
      const segmentKeys = new Set([
        ...Object.keys(previewAssignments || {}),
        ...Object.keys(previewPeriodInputs || {}),
      ]);
      const segmentAssignments = Array.from(segmentKeys).reduce((acc, key) => {
        const value = previewAssignments?.[key];
        const periodLabel = previewPeriodInputs?.[key];
        if (value?.userId || periodLabel) {
          acc[key] = {
            ...(value?.userId ? { user_id: value.userId } : {}),
            ...(periodLabel ? { period_label: periodLabel } : {}),
          };
        }
        return acc;
      }, {});
      if (Object.keys(segmentAssignments).length) {
        formData.append("manual_assignments", JSON.stringify({ segments: segmentAssignments }));
      }
      const res = await apiClient.post("/api/hr/payslip-batches/preview-confirm/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setPreviewToken(res.data?.token || null);
      setPreviewLocked(true);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(detail || "Impossibile confermare la preview.");
    } finally {
      setPreviewLocking(false);
    }
  }, [batchForm.source_file, previewAssignments, previewLocked, previewPeriodInputs]);

  const loadNotifications = useCallback(async () => {
    setNotificationsLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (notificationFilters.status) params.append("status", notificationFilters.status);
      if (notificationFilters.category) params.append("category", notificationFilters.category);
      const res = await apiClient.get(`/api/hr/notifications/${params.toString() ? `?${params.toString()}` : ""}`);
      setNotifications(res.data || []);
    } catch (err) {
      console.error("Errore nel caricamento notifiche", err);
      setError("Impossibile caricare le notifiche HR.");
    } finally {
      setNotificationsLoading(false);
    }
  }, [notificationFilters]);

  const updateAssigneeInput = useCallback((key, value, setter) => {
    setter((prev) => ({ ...prev, [key]: { ...(prev[key] || {}), query: value, user: undefined } }));
    setAssigneeQuery(value);
  }, []);

  const selectAssignee = useCallback((key, user, setter) => {
    setter((prev) => ({
      ...prev,
      [key]: {
        ...(prev[key] || {}),
        user: user.id,
        query: user.username,
        display: user.display_name || user.username,
      },
    }));
    setAssigneeQuery(user.username);
    setAssigneeOptions([]);
  }, []);

  const resolveAssigneeId = useCallback(
    (assignment) => {
      if (!assignment) return null;
      if (assignment.user) return assignment.user;
      const query = assignment.query || assignment.user;
      if (!query) return null;
      const match = assigneeOptions.find(
        (opt) => opt.username?.toLowerCase() === String(query).toLowerCase() || String(opt.id) === String(query)
      );
      if (match) return match.id;
      if (/^\d+$/.test(query)) return query;
      return null;
    },
    [assigneeOptions]
  );

  const hasUnmatchedAssignee = useCallback(
    (id) => Boolean(resolveAssigneeId(unmatchedAssignments[id])),
    [resolveAssigneeId, unmatchedAssignments]
  );

  const hasTicketAssignee = useCallback(
    (id) => Boolean(resolveAssigneeId(assignmentInputs[id])),
    [assignmentInputs, resolveAssigneeId]
  );

  const loadDocuments = useCallback(async () => {
    setDocumentsLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      const page = Math.max(1, documentFilters.page || 1);
      params.append("limit", DOCUMENT_PAGE_SIZE.toString());
      params.append("offset", DOCUMENT_PAGE_SIZE * (page - 1));
      if (documentFilters.search) params.append("search", documentFilters.search);
      const res = await apiClient.get(`/api/hr/documents/${params.toString() ? `?${params.toString()}` : ""}`);
      const items = res.data || [];
      setDocuments(items);
      setDocumentsHasMore(items.length === DOCUMENT_PAGE_SIZE);
    } catch (err) {
      console.error("Errore nel caricamento documenti", err);
      setError("Impossibile caricare i documenti HR.");
    } finally {
      setDocumentsLoading(false);
    }
  }, [documentFilters.page, documentFilters.search]);

  const loadPayslips = useCallback(async ({ page, append } = {}) => {
    setPayslipsLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      const resolvedPage = Math.max(1, page ?? (payslipFilters.page || 1));
      params.append("limit", PAYSLIP_PAGE_SIZE.toString());
      params.append("offset", PAYSLIP_PAGE_SIZE * (resolvedPage - 1));
      if (payslipFilters.search) params.append("search", payslipFilters.search);
      const res = await apiClient.get(`/api/hr/payslips/${params.toString() ? `?${params.toString()}` : ""}`);
      const items = res.data || [];
      setPayslips((prev) => (append ? [...prev, ...items] : items));
      setPayslipHasMore(items.length === PAYSLIP_PAGE_SIZE);
    } catch (err) {
      console.error("Errore nel caricamento buste paga", err);
      setError("Impossibile caricare le buste paga.");
    } finally {
      setPayslipsLoading(false);
    }
  }, [payslipFilters.page, payslipFilters.search]);

  const loadBatches = useCallback(async () => {
    if (!canManagePayroll) {
      setBatches([]);
      return;
    }
    setBatchesLoading(true);
    try {
      const res = await apiClient.get("/api/hr/payslip-batches/");
      setBatches(res.data || []);
    } catch (err) {
      console.error("Errore nel caricamento batch", err);
      setError("Impossibile caricare i batch di buste paga.");
    } finally {
      setBatchesLoading(false);
    }
  }, [canManagePayroll]);

  const loadUnmatched = useCallback(async () => {
    if (!canManagePayroll) {
      setUnmatched([]);
      return;
    }
    setUnmatchedLoading(true);
    try {
      const params = new URLSearchParams();
      if (unmatchedFilters.status) params.append("status", unmatchedFilters.status);
      if (unmatchedFilters.search) params.append("identifier", unmatchedFilters.search);
      if (unmatchedFilters.company) params.append("company", unmatchedFilters.company);
      if (unmatchedFilters.resort) params.append("resort", unmatchedFilters.resort);
      if (unmatchedFilters.period) params.append("period", unmatchedFilters.period);
      const res = await apiClient.get(`/api/hr/payslip-unmatched/${params.toString() ? `?${params.toString()}` : ""}`);
      setUnmatched(res.data || []);
    } catch (err) {
      console.error("Errore nel caricamento unmatched", err);
      setError("Impossibile caricare la coda DA ASSEGNARE.");
    } finally {
      setUnmatchedLoading(false);
    }
  }, [canManagePayroll, unmatchedFilters]);

  const loadUnmatchedSuggestions = useCallback(async (unmatchedId) => {
    if (!canManagePayroll) return;
    setUnmatchedSuggestions((prev) => ({ ...prev, [unmatchedId]: { ...(prev[unmatchedId] || {}), loading: true } }));
    try {
      const res = await apiClient.get(`/api/hr/payslip-unmatched/${unmatchedId}/suggestions/`);
      setUnmatchedSuggestions((prev) => ({
        ...prev,
        [unmatchedId]: { loading: false, items: res.data?.results || [] },
      }));
    } catch (err) {
      console.error("Errore nel caricamento suggerimenti", err);
      setUnmatchedSuggestions((prev) => ({ ...prev, [unmatchedId]: { loading: false, items: [] } }));
    }
  }, [canManagePayroll]);

  const loadEvents = useCallback(async () => {
    if (!canViewAudit) {
      setEvents([]);
      return;
    }
    setEventsLoading(true);
    try {
      const params = new URLSearchParams();
      if (eventFilters.eventType) params.append("event_type", eventFilters.eventType);
      const res = await apiClient.get(`/api/hr/events/${params.toString() ? `?${params.toString()}` : ""}`);
      setEvents(res.data || []);
    } catch (err) {
      console.error("Errore nel caricamento audit", err);
      setError("Impossibile caricare l'audit log.");
    } finally {
      setEventsLoading(false);
    }
  }, [canViewAudit, eventFilters.eventType]);

  const loadDocumentAcks = useCallback(async () => {
    if (!isSuperAdmin) {
      setDocumentAcks([]);
      return;
    }
    setDocumentAcksLoading(true);
    try {
      const res = await apiClient.get("/api/hr/document-acks/?limit=100");
      setDocumentAcks(res.data || []);
    } catch (err) {
      console.error("Errore nel caricamento audit prese visione", err);
      setError("Impossibile caricare l'audit delle prese visione.");
    } finally {
      setDocumentAcksLoading(false);
    }
  }, [isSuperAdmin]);

  const loadTickets = useCallback(async () => {
    if (!isSuperAdmin) {
      setTickets([]);
      return;
    }
    setTicketsLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (ticketFilters.status) params.append("status", ticketFilters.status);
      if (ticketFilters.priority) params.append("priority", ticketFilters.priority);
      if (ticketFilters.dueWithin) params.append("due_within_hours", ticketFilters.dueWithin);
      if (ticketFilters.slaLte) params.append("sla_lte", ticketFilters.slaLte);
      if (ticketFilters.overdueOnly) params.append("overdue", "true");
      const res = await apiClient.get(
        `/api/hr/listening-tickets/${params.toString() ? `?${params.toString()}` : ""}`
      );
      setTickets(res.data || []);
    } catch (err) {
      console.error("Errore nel caricamento ticket", err);
      setError("Impossibile caricare i ticket dello sportello.");
    } finally {
      setTicketsLoading(false);
    }
  }, [isSuperAdmin, ticketFilters]);

  const loadKpi = useCallback(async () => {
    setKpiLoading(true);
    try {
      const params = new URLSearchParams({
        window_days: String(kpiWindowDays),
        completion_min: String(kpiThresholds.completion_min),
        failure_max: String(kpiThresholds.failure_max),
        fallback_max: String(kpiThresholds.fallback_max),
        corrective_sla_hours: String(correctiveSlaHours),
      });
      const res = await apiClient.get(`/api/hr/kpi/?${params.toString()}`);
      setKpiData(res.data || null);
    } catch (err) {
      console.error('Errore nel caricamento KPI HR', err);
      setKpiData(null);
    } finally {
      setKpiLoading(false);
    }
  }, [correctiveSlaHours, kpiWindowDays, kpiThresholds.completion_min, kpiThresholds.failure_max, kpiThresholds.fallback_max]);

  const handleIncidentAcknowledge = useCallback(async () => {
    setIncidentAckLoading(true);
    try {
      const currentAlertLevel = kpiData?.payslip_preview_pipeline?.alert_level || 'warning';
      await apiClient.post('/api/hr/kpi/incident-ack/', {
        note: incidentAckNote,
        alert_level: currentAlertLevel,
      });
      setIncidentAckNote('');
      await loadKpi();
    } catch (err) {
      console.error('Errore nella presa in carico incidente', err);
      setError('Non è stato possibile registrare la presa in carico incidente.');
    } finally {
      setIncidentAckLoading(false);
    }
  }, [incidentAckNote, kpiData, loadKpi]);

  const handleIncidentResolve = useCallback(async () => {
    setIncidentResolveLoading(true);
    try {
      await apiClient.post('/api/hr/kpi/incident-resolve/', {
        resolution_note: incidentResolveForm.resolution_note,
        root_cause: incidentResolveForm.root_cause,
        action_items: incidentResolveForm.action_items,
      });
      setIncidentResolveForm({ resolution_note: '', root_cause: '', action_items: '' });
      await loadKpi();
    } catch (err) {
      console.error('Errore nella chiusura incidente', err);
      setError("Non è stato possibile chiudere l'incidente preview.");
    } finally {
      setIncidentResolveLoading(false);
    }
  }, [incidentResolveForm, loadKpi]);

  const handleCompleteCorrectiveAction = useCallback(async (actionId, label) => {
    setCompletingActionId(actionId);
    try {
      await apiClient.post('/api/hr/kpi/incident-action-complete/', { action_id: actionId, label });
      await loadKpi();
    } catch (err) {
      console.error('Errore nel completamento azione correttiva', err);
      setError("Non è stato possibile aggiornare lo stato dell'azione correttiva.");
    } finally {
      setCompletingActionId('');
    }
  }, [loadKpi]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      if (isSuperAdmin) {
        const prefRes = await apiClient.get("/api/hr/notification-preferences/");
        const prefData = prefRes.data?.[0] || prefRes.data || null;
        setPreference(prefData);
        setPreferenceForm(preferenceToForm(prefData));
        setPreferenceStatus({ error: "", success: "" });
      } else {
        setPreference(null);
        setPreferenceForm(preferenceToForm(null));
        setPreferenceStatus({ error: "", success: "" });
      }
      const baseLoads = [loadDocuments(), loadPayslips(), loadUnmatched(), loadBatches(), loadKpi()];
      await Promise.all(baseLoads);
    } catch (err) {
      console.error("Errore nel caricamento dati HR", err);
      setError("Impossibile caricare i dati HR. Riprova.");
    } finally {
      setLoading(false);
    }
  }, [isSuperAdmin, loadBatches, loadDocuments, loadKpi, loadPayslips, loadUnmatched]);

  useEffect(() => {
    loadContext();
  }, [loadContext]);

  useEffect(() => {
    if (contextReady) {
      loadAll();
    }
  }, [contextReady, loadAll]);

  useEffect(() => {
    if (!contextReady || !isHrPortal) return undefined;
    const timer = setInterval(() => {
      loadKpi();
    }, 60000);
    return () => clearInterval(timer);
  }, [contextReady, isHrPortal, loadKpi]);


  useEffect(() => {
    if (contextReady) {
      loadDocuments();
    }
  }, [contextReady, loadDocuments]);

  useEffect(() => {
    if (contextReady) {
      loadPayslips();
    }
  }, [contextReady, loadPayslips]);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  useEffect(() => {
    if (canManagePayroll) {
      loadUnmatched();
    } else {
      setUnmatched([]);
    }
  }, [canManagePayroll, loadUnmatched]);

  useEffect(() => {
    if (!emailModalOpen) return;
    const query = emailForm.recipient_email?.trim();
    if (!query) {
      setEmailSuggestions([]);
      return;
    }
    const timer = setTimeout(async () => {
      setEmailSuggestionsLoading(true);
      try {
        const res = await apiClient.get(`/api/hr/payslip-email-suggestions/?query=${encodeURIComponent(query)}`);
        setEmailSuggestions(res.data?.results || []);
      } catch (err) {
        console.error("Errore nel caricamento suggerimenti email", err);
      } finally {
        setEmailSuggestionsLoading(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [emailForm.recipient_email, emailModalOpen]);

  useEffect(() => {
    if (!contextReady) return;
    const interval = setInterval(() => {
      loadNotifications();
      loadBatches();
      loadPayslips();
      loadDocuments();
      if (canManagePayroll) {
        loadUnmatched();
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [
    canManagePayroll,
    contextReady,
    loadBatches,
    loadDocuments,
    loadNotifications,
    loadPayslips,
    loadUnmatched,
  ]);

  useEffect(() => {
    if (!canManageNotifications) {
      setSelectedNotification(null);
    }
  }, [canManageNotifications]);

  useEffect(() => {
    setPreferenceForm(preferenceToForm(preference));
  }, [preference]);

  const handleClearQuietHours = useCallback(() => {
    setPreferenceForm((prev) => ({ ...prev, quiet_hours_start: "", quiet_hours_end: "" }));
  }, []);

  const handleDocumentPageChange = useCallback((direction) => {
    setDocumentFilters((prev) => {
      const nextPage = Math.max(1, (prev.page || 1) + direction);
      return { ...prev, page: nextPage };
    });
  }, []);

  const handlePayslipPageChange = useCallback((direction) => {
    setPayslipFilters((prev) => {
      const nextPage = Math.max(1, (prev.page || 1) + direction);
      return { ...prev, page: nextPage };
    });
  }, []);

  const handleSavePreference = useCallback(async () => {
    if (
      (preferenceForm.quiet_hours_start && !preferenceForm.quiet_hours_end) ||
      (!preferenceForm.quiet_hours_start && preferenceForm.quiet_hours_end)
    ) {
      setPreferenceStatus({ error: "Imposta sia inizio sia fine delle quiet hours.", success: "" });
      return;
    }
    setPreferenceSaving(true);
    setPreferenceStatus({ error: "", success: "" });
    try {
      const payload = {
        allow_email: preferenceForm.allow_email,
        allow_push: preferenceForm.allow_push,
        allow_sms: preferenceForm.allow_sms,
        quiet_hours_start: preferenceForm.quiet_hours_start || null,
        quiet_hours_end: preferenceForm.quiet_hours_end || null,
      };
      const endpoint = preference?.id
        ? `/api/hr/notification-preferences/${preference.id}/`
        : "/api/hr/notification-preferences/";
      const method = preference?.id ? "patch" : "post";
      const res = await apiClient[method](endpoint, payload);
      setPreference(res.data);
      setPreferenceStatus({ error: "", success: "Preferenze salvate correttamente." });
    } catch (err) {
      console.error("Errore nel salvataggio preferenze", err);
      const data = err.response?.data;
      let message = "Impossibile salvare le preferenze.";
      if (typeof data === "string") {
        message = data;
      } else if (data?.detail) {
        message = data.detail;
      } else if (Array.isArray(data?.non_field_errors) && data.non_field_errors.length) {
        message = data.non_field_errors[0];
      } else if (Array.isArray(data?.quiet_hours_start) && data.quiet_hours_start.length) {
        message = data.quiet_hours_start[0];
      } else if (Array.isArray(data?.quiet_hours_end) && data.quiet_hours_end.length) {
        message = data.quiet_hours_end[0];
      }
      setPreferenceStatus({ error: message, success: "" });
    } finally {
      setPreferenceSaving(false);
    }
  }, [preference, preferenceForm]);

  const handleAcknowledge = useCallback(
    async (docId) => {
      setAcknowledging(docId);
      try {
        await apiClient.post(`/api/hr/documents/${docId}/acknowledge/`);
        setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
      } catch (err) {
        console.error("Impossibile registrare la lettura", err);
        setError("Non è stato possibile confermare la lettura del documento.");
      } finally {
        setAcknowledging(null);
      }
    },
    []
  );

  const handleRegeneratePeriod = useCallback(
    async (payslipId) => {
      if (!canManagePayroll) {
        setError("Solo HR può rigenerare il periodo delle buste paga.");
        return;
      }
      setRegenerating(payslipId);
      try {
        const res = await apiClient.post(`/api/hr/payslips/${payslipId}/regenerate_period/`);
        setPayslips((prev) => prev.map((p) => (p.id === payslipId ? res.data : p)));
      } catch (err) {
        console.error("Errore nella rigenerazione periodo", err);
        setError("Impossibile rigenerare il periodo della busta paga.");
      } finally {
        setRegenerating(null);
      }
    },
    [canManagePayroll]
  );

  const preSubmitChecklist = useMemo(() => {
    const segments = batchPreview?.segments || [];
    const unresolvedSegments = segments.filter((segment) => {
      const key = segment?.segment_key;
      const autoMatched = Boolean(segment?.auto_matched || segment?.user?.id);
      const manualAssigned = Boolean(key && previewAssignments?.[key]?.userId);
      return !autoMatched && !manualAssigned;
    });
    const invalidPeriodsCount = Object.values(previewPeriodInputs || {}).filter(
      (value) => value && !/^20\d{2}-(0[1-9]|1[0-2])$/.test(value)
    ).length;
    const previewIssuesCount = segments.filter((segment) => Boolean(segment?.error)).length;
    return {
      unresolvedSegments,
      unresolvedCount: unresolvedSegments.length,
      invalidPeriodsCount,
      previewIssuesCount,
      strictMode: strictPreviewMode,
      onStrictModeChange: setStrictPreviewMode,
    };
  }, [batchPreview?.segments, previewAssignments, previewPeriodInputs, strictPreviewMode]);

  const handleCreateBatch = useCallback(async () => {
    if (!canManagePayroll) {
      setError("Solo il team HR può caricare batch di buste paga.");
      return;
    }
    const previewAssignmentsCount = Object.values(previewAssignments).filter((item) => item?.userId).length;
    if (previewAssignmentsCount > 0 && !previewLocked) {
      setError("Conferma le assegnazioni manuali prima di creare il batch.");
      return;
    }
    if (!batchForm.source_file) {
      setError("Seleziona un file ZIP o PDF per creare il batch.");
      return;
    }
    if (previewLocked && !previewToken) {
      setError("Conferma la preview prima di creare il batch.");
      return;
    }
    if (strictPreviewMode && preSubmitChecklist.invalidPeriodsCount > 0) {
      setError("Strict mode: correggi i periodi manuali con formato non valido (YYYY-MM).");
      return;
    }
    if (strictPreviewMode && preSubmitChecklist.previewIssuesCount > 0) {
      setError("Strict mode: risolvi i segmenti con errori di preview prima di creare il batch.");
      return;
    }
    if (strictPreviewMode && preSubmitChecklist.unresolvedCount > 0) {
      setError("Strict mode: assegna tutti i segmenti senza destinatario prima di creare il batch.");
      return;
    }
    setCreatingBatch(true);
    setError("");
    try {
      const formData = new FormData();
      formData.append("source_file", batchForm.source_file);
      formData.append("auto_match_strategy", batchForm.auto_match_strategy);
      formData.append("manifest_hint", batchForm.manifest_hint || "");
      formData.append("enable_ocr", ocrEnabled ? "true" : "false");
      formData.append("ocr_languages", batchForm.ocr_languages || "");
      const segmentKeys = new Set([
        ...Object.keys(previewAssignments || {}),
        ...Object.keys(previewPeriodInputs || {}),
      ]);
      const segmentAssignments = Array.from(segmentKeys).reduce((acc, key) => {
        const value = previewAssignments?.[key];
        const periodLabel = previewPeriodInputs?.[key];
        if (value?.userId || periodLabel) {
          acc[key] = {
            ...(value?.userId ? { user_id: value.userId } : {}),
            ...(periodLabel ? { period_label: periodLabel } : {}),
          };
        }
        return acc;
      }, {});
      if (previewToken) {
        formData.append("preview_token", previewToken);
      }
      if (Object.keys(segmentAssignments).length) {
        formData.append("manual_assignments", JSON.stringify({ segments: segmentAssignments }));
      }
      const res = await apiClient.post("/api/hr/payslip-batches/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setBatchForm({ ...batchForm, source_file: null });
      setBatches((prev) => [res.data, ...prev]);
      await Promise.all([loadPayslips(), loadUnmatched()]);
    } catch (err) {
      console.error("Errore nella creazione batch", err);
      setError("Impossibile creare il batch. Controlla i campi obbligatori e i permessi.");
    } finally {
      setCreatingBatch(false);
    }
  }, [
    batchForm,
    canManagePayroll,
    loadPayslips,
    loadUnmatched,
    previewAssignments,
    previewLocked,
    previewPeriodInputs,
    previewToken,
    preSubmitChecklist.invalidPeriodsCount,
    preSubmitChecklist.previewIssuesCount,
    preSubmitChecklist.unresolvedCount,
    strictPreviewMode,
  ]);

  const handleProcessBatch = useCallback(
    async (batchId) => {
      if (!canManagePayroll) {
        setError("Solo il team HR può rielaborare i batch.");
        return;
      }
      setProcessingBatch(batchId);
      try {
        const res = await apiClient.post(`/api/hr/payslip-batches/${batchId}/process/`);
        setBatches((prev) => prev.map((b) => (b.id === batchId ? res.data.batch : b)));
        await Promise.all([loadPayslips(), loadUnmatched()]);
      } catch (err) {
        console.error("Errore nella lavorazione batch", err);
        setError("Rielaborazione batch non riuscita.");
      } finally {
        setProcessingBatch(null);
      }
    },
    [canManagePayroll, loadPayslips, loadUnmatched]
  );

  const handleDownloadZip = useCallback(async (batchId) => {
    if (!canManagePayroll) {
      setError("Solo il team HR può scaricare gli ZIP dei batch.");
      return;
    }
    setDownloadingBatch(batchId);
    setError("");
    try {
      const response = await apiClient.post(`/api/hr/payslip-batches/${batchId}/download-payslips-zip/`, {}, {
        responseType: 'blob', // Important for file downloads
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      let filename = `buste_paga_batch_${batchId}.zip`;
      const contentDisposition = response.headers['content-disposition'];
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1];
        }
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Errore nel download dello ZIP", err);
      setError("Download del file ZIP non riuscito.");
    } finally {
      setDownloadingBatch(null);
    }
  }, [canManagePayroll]);

  const handleDownloadRenamed = useCallback(async (payslipId) => {
    if (!isOwner) {
      setError("Solo i proprietari possono scaricare i file rinominati.");
      return;
    }
    setDownloadingRenamed(payslipId);
    setError("");
    try {
      const response = await apiClient.get(`/api/hr/payslips/${payslipId}/download-renamed/`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;

      let filename = `payslip_${payslipId}.pdf`;
      const contentDisposition = response.headers['content-disposition'];
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch && filenameMatch.length > 1) {
          filename = filenameMatch[1];
        }
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Errore nel download del file rinominato", err);
      setError("Download del file rinominato non riuscito.");
    } finally {
      setDownloadingRenamed(null);
    }
  }, [isOwner]);

  const handleUnmatchedAssigneeInput = useCallback(
    (unmatchedId, value) => updateAssigneeInput(unmatchedId, value, setUnmatchedAssignments),
    [updateAssigneeInput]
  );

  const handleUnmatchedAssigneeSelect = useCallback(
    (unmatchedId, user) => selectAssignee(unmatchedId, user, setUnmatchedAssignments),
    [selectAssignee]
  );

  const handleResolveUnmatched = useCallback(
    async (unmatchedId) => {
      if (!canManagePayroll) {
        setError("Non hai i permessi per risolvere le buste paga da assegnare.");
        return;
      }
      const assignment = unmatchedAssignments[unmatchedId] || {};
      const assigneeId = resolveAssigneeId(assignment);
      if (!assigneeId) {
        setError("Seleziona un utente dalla lista o inserisci un ID valido.");
        return;
      }
      setResolvingUnmatched(unmatchedId);
      try {
        const res = await apiClient.post(`/api/hr/payslip-unmatched/${unmatchedId}/resolve/`, {
          user: assigneeId,
          period_label: assignment.period_label || "",
        });
        if (res.data?.payslip) {
          setPayslips((prev) => [res.data.payslip, ...prev]);
        }
        setUnmatched((prev) => prev.filter((item) => item.id !== unmatchedId));
      } catch (err) {
        console.error("Errore nell'assegnazione manuale", err);
        const detail = err?.response?.data?.detail;
        setError(detail || "Assegnazione non riuscita. Verifica ID utente e permessi.");
      } finally {
        setResolvingUnmatched(null);
      }
    },
    [canManagePayroll, unmatchedAssignments, resolveAssigneeId]
  );

  const handleOpenEmailModal = useCallback((item) => {
    const periodLabel = extractPeriodLabel(item);
    const subject = `Busta Paga${periodLabel ? ` [${periodLabel}]` : ""}`;
    const body = "Gentile Collega,\n\nin allegato trovi la tua busta paga.";
    setSelectedUnmatched(item);
    setEmailForm({ recipient_email: "", subject, body });
    setEmailResult(null);
    setEmailTestResult(null);
    setEmailSuggestions([]);
    setEmailModalOpen(true);
  }, []);

  const handleCloseEmailModal = useCallback(() => {
    setEmailModalOpen(false);
    setSelectedUnmatched(null);
    setEmailTestResult(null);
  }, []);

  const handleSendPayslipEmail = useCallback(async () => {
    if (!selectedUnmatched) return;
    setEmailSending(true);
    setEmailResult(null);
    setEmailTestResult(null);
    try {
      const res = await apiClient.post(`/api/hr/payslip-unmatched/${selectedUnmatched.id}/send_email/`, emailForm);
      setEmailResult({ success: true, ...res.data });
      setEmailModalOpen(false);
    } catch (err) {
      const data = err.response?.data;
      setEmailResult({
        success: false,
        detail: data?.detail || "Errore tecnico durante l'invio.",
        recipient_email: data?.recipient_email || emailForm.recipient_email,
        subject: data?.subject || emailForm.subject,
        body: data?.body || emailForm.body,
        attachment_name: data?.attachment_name || "busta_paga.pdf",
      });
    } finally {
      setEmailSending(false);
    }
  }, [emailForm, selectedUnmatched]);

  const handleTestPayslipEmail = useCallback(async () => {
    const recipient = emailForm.recipient_email?.trim();
    if (!recipient) {
      setEmailTestResult({ success: false, detail: "Inserisci un'email destinatario per il test." });
      return;
    }
    setEmailTestSending(true);
    setEmailTestResult(null);
    try {
      const res = await apiClient.post("/api/hr/payslip-email-test/", { recipient_email: recipient });
      setEmailTestResult({ success: true, detail: "Test SMTP riuscito.", ...res.data });
    } catch (err) {
      const data = err?.response?.data;
      setEmailTestResult({
        success: false,
        detail: data?.detail || "Test SMTP non riuscito.",
        recipient_email: data?.recipient_email || recipient,
      });
    } finally {
      setEmailTestSending(false);
    }
  }, [emailForm.recipient_email]);

  const handleSelectSuggestedEmail = useCallback((email) => {
    setEmailForm((prev) => ({ ...prev, recipient_email: email }));
    setEmailSuggestions([]);
  }, []);

  const handleCreateTicket = useCallback(async () => {
    if (!ticketForm.subject.trim() || !ticketForm.message.trim()) {
      setError("Compila oggetto e messaggio per aprire un ticket.");
      return;
    }
    setCreatingTicket(true);
    try {
      const res = await apiClient.post("/api/hr/listening-tickets/", ticketForm);
      setTickets((prev) => [res.data, ...prev]);
      setTicketForm({ subject: "", message: "", is_anonymous: false, priority: "normal" });
    } catch (err) {
      console.error("Errore nella creazione ticket", err);
      setError("Impossibile aprire il ticket. Verifica i campi o i permessi.");
    } finally {
      setCreatingTicket(false);
    }
  }, [ticketForm]);

  const handleCreateNotification = useCallback(async () => {
    if (!canManageNotifications) {
      setError("Non hai i permessi per gestire le notifiche.");
      return;
    }
    if (!notificationForm.title || !notificationForm.body) {
      setError("Titolo e testo della notifica sono obbligatori.");
      return;
    }
    if (notificationForm.cta_label && !notificationForm.cta_url) {
      setError("Inserisci anche l'URL della CTA oppure rimuovi la label.");
      return;
    }
    if (notificationForm.cta_url && !notificationForm.cta_label) {
      setError("Inserisci anche la label della CTA oppure rimuovi l'URL.");
      return;
    }
    setCreatingNotification(true);
    setError("");
    try {
      const payload = {
        ...notificationForm,
        audience_roles: notificationForm.audience_roles
          ? notificationForm.audience_roles.split(",").map((role) => role.trim()).filter(Boolean)
          : [],
      };
      const res = await apiClient.post("/api/hr/notifications/", payload);
      setNotificationForm({
        title: "",
        body: "",
        category: "general",
        scheduled_for: "",
        expires_at: "",
        audience_roles: "",
        cta_label: "",
        cta_url: "",
        cta_type: "primary",
      });
      setSelectedNotification(res.data?.id || null);
      await loadNotifications();
    } catch (err) {
      console.error("Errore nella creazione notifica", err);
      const data = err?.response?.data;
      if (data?.cta_label) {
        setError(data.cta_label);
      } else if (data?.cta_url) {
        setError(data.cta_url);
      } else if (Array.isArray(data?.non_field_errors) && data.non_field_errors.length) {
        setError(data.non_field_errors[0]);
      } else {
        setError("Impossibile salvare la notifica. Verifica i permessi o i campi obbligatori.");
      }
    } finally {
      setCreatingNotification(false);
    }
  }, [canManageNotifications, notificationForm, loadNotifications]);

  const handlePublishNotification = useCallback(
    async (notificationId) => {
      if (!canManageNotifications) {
        setError("Non hai i permessi per pubblicare notifiche.");
        return;
      }
      try {
        const res = await apiClient.post(`/api/hr/notifications/${notificationId}/publish/`);
        setNotifications((prev) => prev.map((n) => (n.id === notificationId ? res.data : n)));
      } catch (err) {
        console.error("Errore nella pubblicazione", err);
        setError("Pubblicazione non riuscita.");
      }
    },
    [canManageNotifications]
  );

  const handleArchiveNotification = useCallback(
    async (notificationId) => {
      if (!canManageNotifications) {
        setError("Non hai i permessi per archiviare notifiche.");
        return;
      }
      try {
        const res = await apiClient.post(`/api/hr/notifications/${notificationId}/archive/`);
        setNotifications((prev) => prev.map((n) => (n.id === notificationId ? res.data : n)));
      } catch (err) {
        console.error("Errore nell'archiviazione", err);
        setError("Archiviazione non riuscita.");
      }
    },
    [canManageNotifications]
  );

  const handleDeliverNotification = useCallback(
    async (notificationId) => {
      if (!canManageNotifications) {
        setError("Non hai i permessi per inviare notifiche.");
        return;
      }
      try {
        await apiClient.post(`/api/hr/notifications/${notificationId}/deliver/`);
        await loadNotifications();
      } catch (err) {
        console.error("Errore nell'invio notifica", err);
        setError("Invio notifica non riuscito.");
      }
    },
    [canManageNotifications, loadNotifications]
  );

  const loadDeliveries = useCallback(
    async (notificationId, status = "") => {
      if (!canManageNotifications) return;
      setDeliveryLoading(notificationId);
      setError("");
      try {
        const params = new URLSearchParams({ notification: notificationId });
        if (status) params.append("status", status);
        const res = await apiClient.get(`/api/hr/notification-deliveries/?${params.toString()}`);
        setSelectedNotification(notificationId);
        setDeliveriesByNotification((prev) => ({ ...prev, [notificationId]: res.data || [] }));
      } catch (err) {
        console.error("Errore nel recupero recapiti", err);
        setError("Impossibile caricare i recapiti.");
      } finally {
        setDeliveryLoading(null);
      }
    },
    [canManageNotifications]
  );

  const handleResendFailed = useCallback(
    async (notificationId) => {
      if (!canManageNotifications) {
        setError("Non hai i permessi per gestire il re-invio.");
        return;
      }
      try {
        await apiClient.post(`/api/hr/notifications/${notificationId}/resend_failed/`);
        await loadNotifications();
        if (selectedNotification === notificationId) {
          await loadDeliveries(notificationId);
        }
      } catch (err) {
        console.error("Errore nel re-invio", err);
        setError("Re-invio fallito.");
      }
    },
    [canManageNotifications, loadDeliveries, loadNotifications, selectedNotification]
  );

  const handleAssignTicket = useCallback(
    async (ticketId) => {
      if (!canAssignTickets) {
        setError("Solo HR può assegnare i ticket.");
        return;
      }
      const assignment = assignmentInputs[ticketId];
      const assigneeId = resolveAssigneeId(assignment);
      if (!assigneeId) {
        setError("Seleziona un utente dalla lista o inserisci un ID valido.");
        return;
      }
      setAssigningTicket(ticketId);
      try {
        const res = await apiClient.post(`/api/hr/listening-tickets/${ticketId}/assign/`, {
          assigned_to: assigneeId,
        });
        setTickets((prev) => prev.map((t) => (t.id === ticketId ? res.data : t)));
      } catch (err) {
        console.error("Errore nell'assegnazione del ticket", err);
        setError("Assegnazione non riuscita. Controlla il collaboratore o i permessi.");
      } finally {
        setAssigningTicket(null);
      }
    },
    [assignmentInputs, canAssignTickets, resolveAssigneeId]
  );

  const handleAssignmentChange = useCallback(
    (ticketId, value) => updateAssigneeInput(ticketId, value, setAssignmentInputs),
    [updateAssigneeInput]
  );

  const handleTicketAssigneeSelect = useCallback(
    (ticketId, user) => selectAssignee(ticketId, user, setAssignmentInputs),
    [selectAssignee]
  );

  const handleAddMessage = useCallback(async (ticketId, payload) => {
    setSendingMessage(ticketId);
    try {
      const res = await apiClient.post(`/api/hr/listening-tickets/${ticketId}/add_message/`, payload);
      setTickets((prev) =>
        prev.map((t) => (t.id === ticketId ? { ...t, messages: [...(t.messages || []), res.data] } : t))
      );
    } catch (err) {
      console.error("Errore nell'invio del messaggio", err);
      setError("Non è stato possibile inviare il messaggio.");
    } finally {
      setSendingMessage(null);
    }
  }, []);

  const handleCloseTicket = useCallback(async (ticketId) => {
    if (!canAssignTickets) {
      setError("Solo HR può chiudere i ticket.");
      return;
    }
    setClosingTicket(ticketId);
    try {
      const res = await apiClient.post(`/api/hr/listening-tickets/${ticketId}/close/`);
      setTickets((prev) => prev.map((t) => (t.id === ticketId ? res.data : t)));
    } catch (err) {
      console.error("Errore nella chiusura del ticket", err);
      setError("Chiusura ticket non riuscita.");
    } finally {
      setClosingTicket(null);
    }
  }, [canAssignTickets]);

  const dueSoonTickets = useMemo(() => {
    const now = Date.now();
    const cutoff = now + 1000 * 60 * 60 * 24;
    return tickets.filter(
      (t) => t.status !== "closed" && t.due_at && new Date(t.due_at).getTime() <= cutoff
    );
  }, [tickets]);

  const publishedNotificationsCount = useMemo(
    () => notifications.filter((n) => n.status === "published").length,
    [notifications]
  );

  const unmatchedToAssign = useMemo(
    () => unmatched.filter((item) => item.status === "to_assign").length,
    [unmatched]
  );

  const activeNotifications = useMemo(() => {
    const now = Date.now();
    return notifications.filter(
      (notification) =>
        notification.status === "published" &&
        (!notification.expires_at || new Date(notification.expires_at).getTime() > now)
    );
  }, [notifications]);

  const expiredNotifications = useMemo(() => {
    const now = Date.now();
    return notifications.filter(
      (notification) => notification.expires_at && new Date(notification.expires_at).getTime() <= now
    );
  }, [notifications]);

  const documentsToReadCount = useMemo(
    () => documents.filter((doc) => doc.requires_acknowledgement).length,
    [documents]
  );
  const documentsToSignCount = useMemo(
    () => documents.filter((doc) => doc.requires_signature).length,
    [documents]
  );
  const allDocumentsRead = useMemo(
    () => documentsToReadCount === 0 && documentsToSignCount === 0,
    [documentsToReadCount, documentsToSignCount]
  );

  const visibleNotifications = useMemo(() => {
    const now = Date.now();
    return notifications.filter((notification) => {
      if (notificationQuickFilter.status === "active") {
        return (
          notification.status === "published" &&
          (!notification.expires_at || new Date(notification.expires_at).getTime() > now)
        );
      }
      if (notificationQuickFilter.status === "expired") {
        return notification.expires_at && new Date(notification.expires_at).getTime() <= now;
      }
      if (notificationQuickFilter.status && notification.status !== notificationQuickFilter.status) {
        return false;
      }
      if (notificationQuickFilter.category && notification.category !== notificationQuickFilter.category) {
        return false;
      }
      return true;
    });
  }, [notifications, notificationQuickFilter]);

  const notificationHighlights = useMemo(
    () => activeNotifications.slice(0, 3),
    [activeNotifications]
  );

  const documentHighlights = useMemo(
    () => documents.filter((doc) => doc.requires_acknowledgement).slice(0, 3),
    [documents]
  );

  const heroNotification = notifications.find((n) => n.status !== "archived");
  const latestPayslip = useMemo(() => {
    if (!payslips.length) return null;
    return payslips.reduce((latest, item) => {
      if (!latest) return item;
      const latestDate = new Date(latest.created_at || 0).getTime();
      const itemDate = new Date(item.created_at || 0).getTime();
      return itemDate > latestDate ? item : latest;
    }, null);
  }, [payslips]);
  const latestPayslipLabel =
    latestPayslip?.period_label || extractPeriodLabel(latestPayslip) || "Busta paga recente";
  const latestPayslipStatus = latestPayslip?.downloaded_at ? "Scaricata" : "Da scaricare";
  const documentsRequiringAck = useMemo(
    () => documents.filter((doc) => doc.requires_acknowledgement),
    [documents]
  );

  const quickStatusFilters = [
    { label: "Tutte", value: "" },
    { label: "Attive", value: "active" },
    { label: "Scadute", value: "expired" },
    { label: "Bozze", value: "draft" },
    { label: "Pubblicate", value: "published" },
    { label: "Archiviate", value: "archived" },
  ];

  const quickCategoryFilters = [
    { label: "Tutte", value: "" },
    { label: "Generali", value: "general" },
    { label: "Allerte", value: "alert" },
    { label: "Buste paga", value: "payroll" },
    { label: "Eventi", value: "event" },
  ];

  const bachecaTabs = [
    { id: "documenti", label: "Documenti", count: documents.length },
    { id: "buste_paga", label: "Buste paga", count: payslips.length },
    { id: "comunicazioni", label: "Comunicazioni", count: activeNotifications.length },
  ];

  const bachecaDocuments = useMemo(() => {
    if (bachecaDocumentFilter === "to_read") {
      return documents.filter((doc) => doc.requires_acknowledgement);
    }
    if (bachecaDocumentFilter === "to_sign") {
      return documents.filter((doc) => doc.requires_signature);
    }
    return documents;
  }, [bachecaDocumentFilter, documents]);

  const bachecaNotifications = useMemo(() => {
    if (bachecaNotificationFilter === "active") {
      return activeNotifications;
    }
    if (bachecaNotificationFilter === "archived") {
      return notifications.filter((notification) => notification.status === "archived");
    }
    return notifications;
  }, [activeNotifications, bachecaNotificationFilter, notifications]);

  const bachecaPayslips = useMemo(() => {
    if (bachecaPayslipFilter === "to_download") {
      return payslips.filter((payslip) => !payslip.downloaded_at);
    }
    if (bachecaPayslipFilter === "downloaded") {
      return payslips.filter((payslip) => payslip.downloaded_at);
    }
    return payslips;
  }, [bachecaPayslipFilter, payslips]);

  const previewKpi = kpiData?.payslip_preview_pipeline || {};
  const previewCompletionRate = previewKpi?.completion_rate ?? 0;
  const previewFailureRate = previewKpi?.failure_rate ?? 0;
  const previewFallbackRate = previewKpi?.fallback_rate ?? 0;
  const previewHealthStatus = previewKpi?.health_status || "healthy";
  const completionDelta = previewKpi?.completion_rate_delta ?? 0;
  const failureDelta = previewKpi?.failure_rate_delta ?? 0;
  const fallbackDelta = previewKpi?.fallback_rate_delta ?? 0;
  const previewAlertLevel = previewKpi?.alert_level || "none";
  const previewAlerts = previewKpi?.alert_messages || [];
  const previewBreaches = previewKpi?.breaches || {};
  const previewDailySeries = previewKpi?.daily_preview_series || [];
  const previewFailureReasons = previewKpi?.top_failure_reasons || [];
  const previewIncidentState = previewKpi?.incident_state || {};
  const previewIncidentPlaybook = previewKpi?.incident_playbook || [];
  const previewIncidentJournal = previewKpi?.incident_journal || [];
  const previewIncidentResponseMetrics = previewKpi?.incident_response_metrics || {};
  const previewCorrectiveActions = previewKpi?.corrective_actions || [];
  const previewCorrectiveActionMetrics = previewKpi?.corrective_action_metrics || {};
  const previewToConfirmRate = previewKpi?.preview_to_confirm_rate ?? 0;
  const confirmToBatchRate = previewKpi?.confirm_to_batch_rate ?? 0;
  const avgPreviewCompletionMinutes = previewKpi?.avg_preview_completion_minutes;
  const avgPreviewFailureMinutes = previewKpi?.avg_preview_failure_minutes;
  const avgPreviewToConfirmMinutes = previewKpi?.avg_preview_to_confirm_minutes;
  const firstPassResolutionRate = previewKpi?.first_pass_resolution_rate ?? 0;
  const manualAssignmentErrorReductionRate = previewKpi?.manual_assignment_error_reduction_rate ?? 0;
  const phase4Summary = previewKpi?.phase4_summary || {};
  const phase4Status = phase4Summary?.status || {};
  const previewMatchingMix = previewKpi?.matching_mix || {};
  const previewFunnel = previewKpi?.funnel || {};
  const incidentTargets = previewIncidentResponseMetrics?.targets || {};
  const incidentBreaches = previewIncidentResponseMetrics?.breaches || {};

  return (
    <div className="hr-portal">
      {showLoading && <LoadingOverlay />}
      {error && <div className="hr-portal__banner hr-portal__banner--error">{error}</div>}
      {isHrPortal && <PortalHeader context={portalContext} />}
      {isHrPortal && (
        <WorkspaceTabs
          value={workspaceTab}
          onChange={setWorkspaceTab}
          canViewMonitoring={canViewMonitoringWorkspace}
        />
      )}
      {isHrPortal && workspaceTab === "operations" ? (
        <StepSection
          step="1"
          title="Documenti personali"
          subtitle="Documenti personali e presa visione"
        >
          <div className="hr-portal__summary-grid">
            <StatCard title="Documenti da leggere" value={documentsToReadCount} helper="In attesa di presa visione" />
            <StatCard title="Ultima busta paga" value={latestPayslipLabel} helper={latestPayslipStatus} />
            <StatCard title="Comunicazioni attive" value={activeNotifications.length} helper="Notifiche personali" />
          </div>
          <div className="hr-portal__overview-grid">
            <div className="hr-portal__overview-card">
              <p className="hr-portal__eyebrow">Documenti da leggere</p>
              {documentHighlights.length === 0 ? (
                <p className="hr-portal__muted">Nessun documento in attesa.</p>
              ) : (
                <ul className="hr-portal__overview-list">
                  {documentHighlights.map((doc) => (
                    <li key={doc.id}>
                      <span>{doc.title}</span>
                      <MicroBadge tone="amber">Da leggere</MicroBadge>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="hr-portal__overview-card">
              <p className="hr-portal__eyebrow">Ultima busta paga</p>
              {latestPayslip ? (
                <div className="hr-portal__stack">
                  <p>{latestPayslipLabel}</p>
                  <MicroBadge tone={latestPayslip.downloaded_at ? "emerald" : "amber"}>{latestPayslipStatus}</MicroBadge>
                </div>
              ) : (
                <p className="hr-portal__muted">Nessuna busta paga disponibile.</p>
              )}
            </div>
            <div className="hr-portal__overview-card">
              <p className="hr-portal__eyebrow">Comunicazioni attive</p>
              {notificationHighlights.length === 0 ? (
                <p className="hr-portal__muted">Nessuna comunicazione attiva.</p>
              ) : (
                <ul className="hr-portal__overview-list">
                  {notificationHighlights.map((notification) => (
                    <li key={notification.id}>
                      <span>{notification.title}</span>
                      <MicroBadge tone="emerald">Attiva</MicroBadge>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <Subsection
            title="Documenti personali"
            description="Repository documenti personali"
            actions={
              <div className="hr-portal__actions">
                <Badge tone="indigo">Pagina {documentFilters.page}</Badge>
                <button className="hr-portal__button" onClick={loadDocuments} disabled={documentsLoading}>
                  {documentsLoading ? "Ricerca…" : "Aggiorna"}
                </button>
              </div>
            }
          >
            <div className="hr-portal__filters hr-portal__filters--wrap">
              <label className="hr-portal__field hr-portal__field--wide">
                <span>Ricerca</span>
                <input
                  className="hr-portal__input"
                  placeholder="Cerca per titolo o categoria"
                  value={documentFilters.search}
                  onChange={(e) => setDocumentFilters({ ...documentFilters, search: e.target.value, page: 1 })}
                />
              </label>
              <div className="hr-portal__actions">
                <button className="hr-portal__button hr-portal__button--ghost" onClick={loadDocuments} disabled={documentsLoading}>
                  Applica
                </button>
                <button
                  className="hr-portal__button hr-portal__button--ghost"
                  onClick={() => handleDocumentPageChange(-1)}
                  disabled={documentFilters.page <= 1 || documentsLoading}
                >
                  ← Prec.
                </button>
                <button
                  className="hr-portal__button hr-portal__button--ghost"
                  onClick={() => handleDocumentPageChange(1)}
                  disabled={!documentsHasMore || documentsLoading}
                >
                  Succ. →
                </button>
              </div>
            </div>
            {documentsLoading ? (
              <div className="hr-portal__grid">
                {[...Array(3)].map((_, idx) => (
                  <SkeletonCard key={idx} lines={4} />
                ))}
              </div>
            ) : documents.length === 0 ? (
              <EmptyState label="Nessun documento in attesa" />
            ) : (
              <DocumentList documents={documents} onAcknowledge={handleAcknowledge} acknowledging={acknowledging} />
            )}
          </Subsection>
        </StepSection>
      ) : (
        <section className="hr-portal__bacheca">
          <div className="hr-portal__bacheca-topbar">
            <button
              type="button"
              className="hr-portal__bacheca-menu"
              onClick={handleOpenSidebarMenu}
              aria-label="Apri il menu principale"
            >
              <i className="fas fa-bars" aria-hidden="true"></i>
            </button>
            <div className="hr-portal__bacheca-topbar-text">
              <span className="hr-portal__eyebrow">Bacheca Nuvia</span>
              <strong>Documenti &amp; Comunicazioni</strong>
            </div>
          </div>
          <div className="hr-portal__bacheca-header">
            <div>
              <p className="hr-portal__eyebrow">Bacheca personale</p>
              <h2>La tua bacheca HR</h2>
              <p className="hr-portal__muted">Comunicazioni, documenti e buste paga in un flusso semplice.</p>
            </div>
            <div className="hr-portal__bacheca-summary">
              <div>
                <span className="hr-portal__summary-label">Comunicazioni</span>
                <strong>{activeNotifications.length}</strong>
              </div>
              <div>
                <span className="hr-portal__summary-label">Documenti</span>
                <strong>{documentsRequiringAck.length}</strong>
              </div>
              <div>
                <span className="hr-portal__summary-label">Buste paga</span>
                <strong>{payslips.length}</strong>
              </div>
            </div>
          </div>

          <div className="hr-portal__tab-bar" role="tablist" aria-label="Sezioni bacheca">
            {bachecaTabs.map((tab) => (
              <button
                key={tab.id}
                className={`hr-portal__tab-button${bachecaTab === tab.id ? " is-active" : ""}`}
                onClick={() => setBachecaTab(tab.id)}
                role="tab"
                aria-selected={bachecaTab === tab.id}
                type="button"
              >
                <span>{tab.label}</span>
                <span className="hr-portal__tab-count">{tab.count}</span>
              </button>
            ))}
          </div>

          <div className="hr-portal__tab-panel" role="tabpanel">
            {bachecaTab === "comunicazioni" && (
              <>
                <div className="hr-portal__tab-header">
                  <h3>Comunicazioni</h3>
                </div>
                <div className="hr-portal__quick-filters">
                  <span className="hr-portal__eyebrow">Filtro</span>
                  <div className="hr-portal__quick-filters-row">
                    {[
                      { id: "all", label: "Tutte" },
                      { id: "active", label: "Attive" },
                      { id: "archived", label: "Archiviate" },
                    ].map((filter) => (
                      <button
                        key={filter.id}
                        type="button"
                        className={`hr-portal__quick-filter ${bachecaNotificationFilter === filter.id ? "is-active" : ""}`}
                        onClick={() => setBachecaNotificationFilter(filter.id)}
                      >
                        {filter.label}
                      </button>
                    ))}
                  </div>
                </div>
                {notificationsLoading ? (
                  <div className="hr-portal__list">
                    {[...Array(3)].map((_, idx) => (
                      <SkeletonCard key={idx} lines={3} />
                    ))}
                  </div>
                ) : bachecaNotifications.length === 0 ? (
                  <EmptyState label="Nessuna comunicazione attiva" />
                ) : (
                  <div className="hr-portal__list">
                    {bachecaNotifications.map((notification) => (
                      <article key={notification.id} className="hr-portal__list-card">
                        <p className="hr-portal__eyebrow">{notification.category}</p>
                        <h3>{notification.title}</h3>
                        <p className="hr-portal__muted">{notification.body}</p>
                      </article>
                    ))}
                  </div>
                )}
              </>
            )}

            {bachecaTab === "documenti" && (
              <>
                <div className="hr-portal__tab-header">
                  <h3>Documenti</h3>
                </div>
                <div className="hr-portal__quick-filters">
                  <span className="hr-portal__eyebrow">Filtro</span>
                  <div className="hr-portal__quick-filters-row">
                    {[
                      { id: "all", label: "Tutti" },
                      { id: "to_read", label: "Da leggere" },
                      { id: "to_sign", label: "Da firmare" },
                    ].map((filter) => (
                      <button
                        key={filter.id}
                        type="button"
                        className={`hr-portal__quick-filter ${bachecaDocumentFilter === filter.id ? "is-active" : ""}`}
                        onClick={() => setBachecaDocumentFilter(filter.id)}
                      >
                        {filter.label}
                      </button>
                    ))}
                  </div>
                </div>
                {allDocumentsRead && <p className="hr-portal__muted">Tutto letto ✅</p>}
                {documentsLoading ? (
                  <div className="hr-portal__list">
                    {[...Array(3)].map((_, idx) => (
                      <SkeletonCard key={idx} lines={3} />
                    ))}
                  </div>
                ) : bachecaDocuments.length === 0 ? (
                  <EmptyState label="Nessun documento in attesa" />
                ) : (
                  <DocumentList
                    layout="bacheca"
                    documents={bachecaDocuments}
                    onAcknowledge={handleAcknowledge}
                    acknowledging={acknowledging}
                  />
                )}
              </>
            )}

            {bachecaTab === "buste_paga" && (
              <>
                <div className="hr-portal__tab-header">
                  <h3>Buste paga</h3>
                </div>
                <div className="hr-portal__quick-filters">
                  <span className="hr-portal__eyebrow">Filtro</span>
                  <div className="hr-portal__quick-filters-row">
                    {[
                      { id: "all", label: "Tutte" },
                      { id: "to_download", label: "Da scaricare" },
                      { id: "downloaded", label: "Scaricate" },
                    ].map((filter) => (
                      <button
                        key={filter.id}
                        type="button"
                        className={`hr-portal__quick-filter ${bachecaPayslipFilter === filter.id ? "is-active" : ""}`}
                        onClick={() => setBachecaPayslipFilter(filter.id)}
                      >
                        {filter.label}
                      </button>
                    ))}
                  </div>
                </div>
                {payslipsLoading ? (
                  <div className="hr-portal__list">
                    {[...Array(3)].map((_, idx) => (
                      <SkeletonCard key={idx} lines={3} />
                    ))}
                  </div>
                ) : bachecaPayslips.length === 0 ? (
                  <EmptyState label="Nessuna busta paga disponibile" />
                ) : (
                  <PayslipList
                    layout="bacheca"
                    payslips={bachecaPayslips}
                    onRegeneratePeriod={handleRegeneratePeriod}
                    regenerating={regenerating}
                    canRegenerate={false}
                    onDownloadRenamed={handleDownloadRenamed}
                    downloadingRenamed={downloadingRenamed}
                    isOwner={isOwner}
                  />
                )}
                {payslipHasMore && !payslipsLoading && (
                  <button
                    className="hr-portal__button hr-portal__button--ghost"
                    onClick={() => {
                      const nextPage = (payslipFilters.page || 1) + 1;
                      setPayslipFilters((prev) => ({ ...prev, page: nextPage }));
                      loadPayslips({ page: nextPage, append: true });
                    }}
                  >
                    Carica altre buste paga
                  </button>
                )}
              </>
            )}
          </div>
        </section>
      )}

      {isHrPortal && workspaceTab === "monitoring" && canViewMonitoringWorkspace && (
        <section className="hr-portal__card">
          <div className="hr-portal__section-header">
            <div>
              <p className="hr-portal__eyebrow">Step 1.5</p>
              <h2 className="hr-portal__title">Osservabilità preview buste paga</h2>
              <p className="hr-portal__subtitle">Sezione avanzata: monitoraggio pipeline, fallback e conversione.</p>
            </div>
            <div className="hr-portal__actions">
              <button
                className="hr-portal__button hr-portal__button--ghost"
                onClick={() => setShowPreviewObservability((prev) => !prev)}
              >
                {showPreviewObservability ? "Nascondi dettagli avanzati" : "Mostra dettagli avanzati"}
              </button>
            </div>
          </div>
          {showPreviewObservability && (
            <div className="hr-portal__step-body">
              <div className="hr-portal__actions">
                <select className="hr-portal__input" value={kpiWindowDays} onChange={(e) => setKpiWindowDays(Number(e.target.value) || 30)}>
                <option value={7}>Ultimi 7 giorni</option>
                <option value={30}>Ultimi 30 giorni</option>
                <option value={90}>Ultimi 90 giorni</option>
              </select>
              <input
                className="hr-portal__input"
                type="number"
                min="50"
                max="100"
                value={kpiThresholds.completion_min}
                onChange={(e) => setKpiThresholds((prev) => ({ ...prev, completion_min: Number(e.target.value) || 85 }))}
                title="Soglia minima completion rate"
              />
              <input
                className="hr-portal__input"
                type="number"
                min="0"
                max="100"
                value={kpiThresholds.failure_max}
                onChange={(e) => setKpiThresholds((prev) => ({ ...prev, failure_max: Number(e.target.value) || 10 }))}
                title="Soglia massima failure rate"
              />
              <input
                className="hr-portal__input"
                type="number"
                min="0"
                max="100"
                value={kpiThresholds.fallback_max}
                onChange={(e) => setKpiThresholds((prev) => ({ ...prev, fallback_max: Number(e.target.value) || 30 }))}
                title="Soglia massima fallback rate"
              />
              <input
                className="hr-portal__input"
                type="number"
                min="1"
                max="720"
                value={correctiveSlaHours}
                onChange={(e) => setCorrectiveSlaHours(Number(e.target.value) || 72)}
                title="SLA ore azioni correttive"
              />
                <button className="hr-portal__button hr-portal__button--ghost" onClick={loadKpi} disabled={kpiLoading}>
                  {kpiLoading ? 'Aggiornamento…' : 'Aggiorna KPI'}
                </button>
              </div>
          <div className="hr-portal__actions hr-portal__actions--wrap">
            <Badge tone={previewHealthStatus === 'critical' ? 'rose' : previewHealthStatus === 'warning' ? 'amber' : 'emerald'}>
              Stato pipeline: {previewHealthStatus}
            </Badge>
            <Badge tone="slate">Failure rate {previewFailureRate}% ({failureDelta >= 0 ? '+' : ''}{failureDelta})</Badge>
            <Badge tone="indigo">Fallback rate {previewFallbackRate}% ({fallbackDelta >= 0 ? '+' : ''}{fallbackDelta})</Badge>
            <Badge tone="emerald">Completion Δ {completionDelta >= 0 ? '+' : ''}{completionDelta}</Badge>
            {previewBreaches.completion && <Badge tone="rose">Soglia completion superata</Badge>}
            {previewBreaches.failure && <Badge tone="rose">Soglia failure superata</Badge>}
            {previewBreaches.fallback && <Badge tone="amber">Soglia fallback superata</Badge>}
          </div>
          {previewAlertLevel !== 'none' && (
            <div className={`hr-portal__banner ${previewAlertLevel === 'critical' ? 'hr-portal__banner--error' : 'hr-portal__banner--warning'}`}>
              <strong>Alert pipeline preview ({previewAlertLevel})</strong>
              {previewAlerts.length > 0 && (
                <ul className="hr-portal__list">
                  {previewAlerts.map((msg) => (
                    <li key={msg}>{msg}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {(previewIncidentState.incident_open || previewIncidentPlaybook.length > 0) && (
            <div className="hr-portal__card hr-portal__incident-card">
              <div className="hr-portal__incident-header">
                <div>
                  <p className="hr-portal__eyebrow">Step 10 · Playbook incidenti</p>
                  <h3>Runbook operativo preview</h3>
                </div>
                {previewIncidentState.acknowledged ? (
                  <Badge tone="emerald">
                    Preso in carico da {previewIncidentState.acknowledged_by || 'operatore'}
                  </Badge>
                ) : (
                  <Badge tone={previewAlertLevel === 'critical' ? 'rose' : 'amber'}>Incidente aperto</Badge>
                )}
              </div>
              {previewIncidentPlaybook.length > 0 && (
                <ul className="hr-portal__incident-playbook">
                  {previewIncidentPlaybook.map((item) => (
                    <li key={item.id}>
                      <strong>{item.title}</strong>
                      <p className="hr-portal__muted">{item.description}</p>
                      {item.command_hint && <code className="hr-portal__muted">{item.command_hint}</code>}
                    </li>
                  ))}
                </ul>
              )}
              {previewIncidentState.acknowledged_at && (
                <p className="hr-portal__muted">
                  Ultima presa in carico: {formatDate(previewIncidentState.acknowledged_at)}
                </p>
              )}
              {previewIncidentState.note && <p className="hr-portal__muted">Nota: {previewIncidentState.note}</p>}
              {previewIncidentState.incident_open && !previewIncidentState.acknowledged && (
                <div className="hr-portal__incident-actions">
                  <textarea
                    className="hr-portal__input"
                    rows={3}
                    placeholder="Nota operativa (facoltativa): es. verifico worker e proxy SSE"
                    value={incidentAckNote}
                    onChange={(e) => setIncidentAckNote(e.target.value)}
                  />
                  <button className="hr-portal__button" onClick={handleIncidentAcknowledge} disabled={incidentAckLoading}>
                    {incidentAckLoading ? 'Registrazione…' : 'Prendi in carico incidente'}
                  </button>
                </div>
              )}
              <div className="hr-portal__incident-resolution">
                <p className="hr-portal__eyebrow">Step 11 · Chiusura incidente</p>
                <div className="hr-portal__incident-actions">
                  <textarea
                    className="hr-portal__input"
                    rows={2}
                    placeholder="Root cause sintetica"
                    value={incidentResolveForm.root_cause}
                    onChange={(e) => setIncidentResolveForm((prev) => ({ ...prev, root_cause: e.target.value }))}
                  />
                  <textarea
                    className="hr-portal__input"
                    rows={2}
                    placeholder="Nota di risoluzione"
                    value={incidentResolveForm.resolution_note}
                    onChange={(e) => setIncidentResolveForm((prev) => ({ ...prev, resolution_note: e.target.value }))}
                  />
                  <textarea
                    className="hr-portal__input"
                    rows={3}
                    placeholder="Action items (una riga per voce)"
                    value={incidentResolveForm.action_items}
                    onChange={(e) => setIncidentResolveForm((prev) => ({ ...prev, action_items: e.target.value }))}
                  />
                  <button
                    className="hr-portal__button hr-portal__button--ghost"
                    onClick={handleIncidentResolve}
                    disabled={incidentResolveLoading}
                  >
                    {incidentResolveLoading ? 'Chiusura…' : 'Chiudi incidente'}
                  </button>
                </div>
                {previewIncidentState.resolved_at && (
                  <p className="hr-portal__muted">
                    Ultima chiusura: {formatDate(previewIncidentState.resolved_at)} da {previewIncidentState.resolved_by || 'operatore'}
                  </p>
                )}
              </div>
              {previewIncidentJournal.length > 0 && (
                <div className="hr-portal__incident-journal">
                  <p className="hr-portal__eyebrow">Journal incidenti (ultimi 10 eventi)</p>
                  <ul className="hr-portal__list">
                    {previewIncidentJournal.map((item, idx) => (
                      <li key={`${item.event_type}-${item.created_at || idx}`} className="hr-portal__muted">
                        [{item.event_type}] {formatDate(item.created_at)} · {item.actor || 'sistema'} · {item.note || item.root_cause || '—'}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="hr-portal__incident-retro">
                <p className="hr-portal__eyebrow">Step 12 · Retrospettiva incidenti</p>
                <div className="hr-portal__summary-grid">
                  <StatCard title="Incidenti rilevati" value={previewIncidentResponseMetrics.incidents_detected ?? 0} helper="Eventi preview_failed" />
                  <StatCard title="Copertura ACK" value={`${previewIncidentResponseMetrics.ack_coverage_rate ?? 0}%`} helper={`Aperti stimati: ${previewIncidentResponseMetrics.open_incidents_estimate ?? 0}`} />
                  <StatCard title="Resolution rate" value={`${previewIncidentResponseMetrics.resolution_rate ?? 0}%`} helper={`Risolti: ${previewIncidentResponseMetrics.incidents_resolved ?? 0}`} />
                  <StatCard title="MTTA medio" value={previewIncidentResponseMetrics.avg_mtta_minutes != null ? `${previewIncidentResponseMetrics.avg_mtta_minutes} min` : '—'} helper="Tempo medio presa in carico" />
                  <StatCard title="MTTR medio" value={previewIncidentResponseMetrics.avg_mttr_minutes != null ? `${previewIncidentResponseMetrics.avg_mttr_minutes} min` : '—'} helper="Tempo medio risoluzione" />
                </div>
                <div className="hr-portal__actions hr-portal__actions--wrap">
                  <Badge tone="slate">Target MTTA: {incidentTargets.mtta_minutes ?? 15} min</Badge>
                  <Badge tone="slate">Target MTTR: {incidentTargets.mttr_minutes ?? 30} min</Badge>
                  {incidentBreaches.mtta && <Badge tone="rose">Sforamento MTTA</Badge>}
                  {incidentBreaches.mttr && <Badge tone="rose">Sforamento MTTR</Badge>}
                </div>
              </div>
              <div className="hr-portal__incident-retro">
                <p className="hr-portal__eyebrow">Step 13 · Follow-up azioni correttive</p>
                <div className="hr-portal__actions hr-portal__actions--wrap">
                  <Badge tone="indigo">Totali: {previewCorrectiveActionMetrics.total ?? 0}</Badge>
                  <Badge tone="emerald">Completate: {previewCorrectiveActionMetrics.completed ?? 0}</Badge>
                  <Badge tone="amber">Aperte: {previewCorrectiveActionMetrics.open ?? 0}</Badge>
                  <Badge tone="rose">Scadute: {previewCorrectiveActionMetrics.overdue ?? 0}</Badge>
                  <Badge tone="indigo">In scadenza: {previewCorrectiveActionMetrics.due_soon ?? 0}</Badge>
                  <Badge tone="slate">SLA {previewCorrectiveActionMetrics.sla_hours ?? correctiveSlaHours}h</Badge>
                  <Badge tone="slate">Completion {previewCorrectiveActionMetrics.completion_rate ?? 0}%</Badge>
                </div>
                {previewCorrectiveActions.length === 0 ? (
                  <p className="hr-portal__muted">Nessuna azione correttiva registrata nell'ultima chiusura incidente.</p>
                ) : (
                  <div className="hr-portal__stack">
                    {previewCorrectiveActions.map((item) => (
                      <div key={item.id} className="hr-portal__queue-item">
                        <div>
                          <p className="hr-portal__eyebrow">{item.id}</p>
                          <p>{item.label}</p>
                        </div>
                        <div className="hr-portal__stack">
                          {item.due_at && <p className="hr-portal__muted">Scadenza: {formatDate(item.due_at)}</p>}
                          {item.completed && item.completed_at && (
                            <p className="hr-portal__muted">Completata: {formatDate(item.completed_at)}{item.completed_by ? ` · ${item.completed_by}` : ''}</p>
                          )}
                          {item.completed ? (
                            <Badge tone="emerald">Completata</Badge>
                          ) : item.status === 'overdue' ? (
                            <Badge tone="rose">Scaduta</Badge>
                          ) : item.status === 'due_soon' ? (
                            <Badge tone="amber">In scadenza</Badge>
                          ) : (
                            <Badge tone="indigo">Aperta</Badge>
                          )}
                          {!item.completed && (
                            <button
                              className="hr-portal__button hr-portal__button--ghost"
                              onClick={() => handleCompleteCorrectiveAction(item.id, item.label)}
                              disabled={completingActionId === item.id}
                            >
                              {completingActionId === item.id ? 'Aggiornamento…' : 'Segna completata'}
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
          <div className="hr-portal__summary-grid">
            <StatCard title="Preview avviate" value={previewKpi.started ?? 0} helper="Totale job preview" />
            <StatCard title="Preview completate" value={previewKpi.completed ?? 0} helper={`${previewCompletionRate}% completion rate`} />
            <StatCard title="Preview fallite" value={previewKpi.failed ?? 0} helper="Incidenti pipeline" />
            <StatCard title="Fallback polling" value={previewKpi.fallback_polling ?? 0} helper="SSE -> polling" />
            <StatCard title="Preview confermate" value={previewKpi.confirmed ?? 0} helper="Pronte al create batch" />
            <StatCard title="Batch creati" value={previewKpi.batch_created ?? 0} helper={`${confirmToBatchRate}% conferma→batch`} />
            <StatCard title="Conv. preview→conferma" value={`${previewToConfirmRate}%`} helper="Funnel fase review" />
            <StatCard title="Avg completion" value={avgPreviewCompletionMinutes != null ? `${avgPreviewCompletionMinutes} min` : '—'} helper="Tempo medio preview→completed" />
            <StatCard title="Avg failure" value={avgPreviewFailureMinutes != null ? `${avgPreviewFailureMinutes} min` : '—'} helper="Tempo medio preview→failed" />
            <StatCard title="Avg preview→conferma" value={avgPreviewToConfirmMinutes != null ? `${avgPreviewToConfirmMinutes} min` : '—'} helper="Tempo medio preview→conferma" />
            <StatCard title="Risolti al primo passaggio" value={`${firstPassResolutionRate}%`} helper={`First pass: ${previewKpi.first_pass_resolved ?? 0}/${previewKpi.confirmed ?? 0}`} />
            <StatCard title="Riduzione errori assignment" value={`${manualAssignmentErrorReductionRate}%`} helper={`Prev: ${previewKpi.manual_assignment_errors_previous ?? 0} · Corrente: ${previewKpi.manual_assignment_errors_current ?? 0}`} />
          </div>
          <div className="hr-portal__card">
            <p className="hr-portal__eyebrow">Monitoraggio Fase 4 (2 settimane)</p>
            <div className="hr-portal__stack">
              <div className="hr-portal__upload-summary-badges">
                <Badge tone={phase4Status.preview_to_confirm_time === "ok" ? "emerald" : "amber"}>Tempo preview→conferma {phase4Status.preview_to_confirm_time || "n/d"}</Badge>
                <Badge tone={phase4Status.first_pass_resolution === "ok" ? "emerald" : "amber"}>Risoluzione primo passaggio {phase4Status.first_pass_resolution || "n/d"}</Badge>
                <Badge tone={phase4Status.manual_assignment_error_reduction === "ok" ? "emerald" : "amber"}>Riduzione errori assignment {phase4Status.manual_assignment_error_reduction || "n/d"}</Badge>
              </div>
              <p className="hr-portal__muted">
                Target: ≤ {phase4Summary?.targets?.preview_to_confirm_minutes_max ?? 15} min ·
                first-pass ≥ {phase4Summary?.targets?.first_pass_resolution_rate_min ?? 70}% ·
                riduzione errori ≥ {phase4Summary?.targets?.manual_assignment_error_reduction_rate_min ?? 0}%.
              </p>
            </div>
          </div>
          <div className="hr-portal__card">
            <p className="hr-portal__eyebrow">Matching mix (finestra KPI)</p>
            <div className="hr-portal__summary-grid">
              <StatCard title="Auto matched" value={previewMatchingMix.auto_matched ?? 0} helper={`${previewMatchingMix.auto_match_share ?? 0}%`} />
              <StatCard title="Manual/review" value={previewMatchingMix.manual_or_review ?? 0} helper={`${previewMatchingMix.manual_match_share ?? 0}%`} />
            </div>
          </div>
          <div className="hr-portal__card">
            <p className="hr-portal__eyebrow">Funnel preview → batch</p>
            <div className="hr-portal__summary-grid">
              <StatCard title="Started" value={previewFunnel.started ?? 0} helper="Preview avviate" />
              <StatCard title="Confirmed" value={previewFunnel.confirmed ?? 0} helper={`Dropoff: ${previewFunnel.dropoff_before_confirm ?? 0}`} />
              <StatCard title="Batch created" value={previewFunnel.batch_created ?? 0} helper={`Dropoff: ${previewFunnel.dropoff_before_batch ?? 0}`} />
            </div>
          </div>
          {(previewKpi.recommendations || []).length > 0 && (
            <div className="hr-portal__card">
              <p className="hr-portal__eyebrow">Raccomandazioni operative</p>
              <ul className="hr-portal__list">
                {(previewKpi.recommendations || []).map((item) => (
                  <li key={item} className="hr-portal__muted">• {item}</li>
                ))}
              </ul>
            </div>
          )}
          {previewDailySeries.length > 0 && (
            <div className="hr-portal__card">
              <p className="hr-portal__eyebrow">Trend giornaliero preview</p>
              <div className="hr-portal__meta">
                {previewDailySeries.slice(-7).map((row) => (
                  <span key={row.date}>
                    {row.date}: {row.completed}/{row.started} ok · fail {row.failed} · fb {row.fallback_polling}
                  </span>
                ))}
              </div>
            </div>
          )}
          {previewFailureReasons.length > 0 && (
            <div className="hr-portal__card">
              <p className="hr-portal__eyebrow">Top cause errore preview</p>
              <ul className="hr-portal__list">
                {previewFailureReasons.map((item) => (
                  <li key={item.reason} className="hr-portal__muted">• {item.reason} ({item.count})</li>
                ))}
              </ul>
            </div>
          )}
            </div>
          )}
        </section>
      )}

      {isHrPortal && (
        <>
          <StepSection
            step="2"
            title="Buste paga"
            subtitle="Disponibili, da assegnare e storico batch"
            actions={
              <div className="hr-portal__actions">
                <Badge tone="indigo">Pagina {payslipFilters.page}</Badge>
                <button className="hr-portal__button" onClick={loadPayslips} disabled={payslipsLoading}>
                  {payslipsLoading ? "Ricerca…" : "Aggiorna"}
                </button>
              </div>
            }
          >
            <Subsection
              title="Da assegnare"
              description="Coda di revisione manuale"
              actions={
                canManagePayroll && (
                  <div className="hr-portal__actions">
                    <Badge tone="rose">{unmatchedToAssign} in coda</Badge>
                    <button className="hr-portal__button hr-portal__button--ghost" onClick={loadUnmatched} disabled={unmatchedLoading}>
                      {unmatchedLoading ? "Aggiornamento…" : "Ricarica"}
                    </button>
                  </div>
                )
              }
            >
              <WorkflowSteps
                items={["Upload", "Preview", "Correzioni", "Conferma", "Crea batch"]}
                current={
                  !batchForm.source_file
                    ? 0
                    : previewLocked
                      ? 3
                      : (batchPreview?.segments || []).length > 0
                        ? 2
                        : batchPreview?.loading
                          ? 1
                          : 1
                }
              />
              {canManagePayroll ? (
                <>
                  <div className="hr-portal__actions hr-portal__actions--wrap">
                    <select
                      className="hr-portal__input"
                      value={unmatchedFilters.status}
                      onChange={(e) => setUnmatchedFilters({ ...unmatchedFilters, status: e.target.value })}
                    >
                      <option value="">Tutti</option>
                      <option value="to_assign">DA ASSEGNARE</option>
                      <option value="resolved">Assegnato</option>
                    </select>
                    <input
                      className="hr-portal__input"
                      placeholder="Cerca identificativo"
                      value={unmatchedFilters.search}
                      onChange={(e) => setUnmatchedFilters({ ...unmatchedFilters, search: e.target.value })}
                    />
                    <input
                      className="hr-portal__input"
                      placeholder="Company ID"
                      value={unmatchedFilters.company}
                      onChange={(e) => setUnmatchedFilters({ ...unmatchedFilters, company: e.target.value })}
                    />
                    <input
                      className="hr-portal__input"
                      placeholder="Resort ID"
                      value={unmatchedFilters.resort}
                      onChange={(e) => setUnmatchedFilters({ ...unmatchedFilters, resort: e.target.value })}
                    />
                    <input
                      className="hr-portal__input"
                      type="month"
                      value={unmatchedFilters.period}
                      onChange={(e) => setUnmatchedFilters({ ...unmatchedFilters, period: e.target.value })}
                    />
                    <button className="hr-portal__button hr-portal__button--ghost" onClick={loadUnmatched} disabled={unmatchedLoading}>
                      {unmatchedLoading ? "Filtri…" : "Applica filtri"}
                    </button>
                  </div>
                  {unmatchedLoading ? (
                    <div className="hr-portal__grid hr-portal__grid--compact">
                      {[...Array(2)].map((_, idx) => (
                        <SkeletonCard key={idx} lines={3} />
                      ))}
                    </div>
                  ) : unmatched.length === 0 ? (
                    <EmptyState label="Nessuna busta paga in coda" />
                  ) : (
                    <UnmatchedQueue
                      items={unmatched}
                      onResolve={handleResolveUnmatched}
                      onSendEmail={handleOpenEmailModal}
                      assignments={unmatchedAssignments}
                      onAssigneeInput={handleUnmatchedAssigneeInput}
                      onAssigneeSelect={handleUnmatchedAssigneeSelect}
                      assigneeOptions={assigneeOptions}
                      assigneeLoading={assigneeLoading}
                      hasAssignee={hasUnmatchedAssignee}
                      setAssignments={setUnmatchedAssignments}
                      resolving={resolvingUnmatched}
                      suggestionsById={unmatchedSuggestions}
                      onLoadSuggestions={loadUnmatchedSuggestions}
                    />
                  )}
                </>
              ) : (
                <div className="hr-portal__banner hr-portal__banner--muted">
                  <p className="hr-portal__muted">La coda DA ASSEGNARE è disponibile solo agli operatori HR.</p>
                </div>
              )}
            </Subsection>

            <Subsection title="Storico batch" description="Carica batch e monitora i processamenti">
              {canManagePayroll ? (
                <div className="hr-portal__grid">
                  <PayslipBatchForm
                    form={batchForm}
                    onChange={setBatchForm}
                    onSubmit={handleCreateBatch}
                    creating={creatingBatch}
                    preview={batchPreview}
                    assignments={previewAssignments}
                    assignmentInputs={previewAssignmentInputs}
                    periodInputs={previewPeriodInputs}
                    assigneeOptions={previewAssigneeOptions}
                    assigneeLoading={previewAssigneeLoading}
                    onAssigneeInput={handlePreviewAssigneeInput}
                    onAssigneeSelect={handlePreviewAssigneeSelect}
                    onAssigneeClear={handlePreviewAssigneeClear}
                    bulkAssigneeInput={bulkAssigneeInput}
                    bulkAssigneeSelected={bulkAssigneeSelected}
                    onBulkAssigneeInput={handleBulkAssigneeInput}
                    onBulkAssigneeSelect={handleBulkAssigneeSelect}
                    onBulkAssigneeClear={handleBulkAssigneeClear}
                    bulkPeriodValue={bulkPeriodValue}
                    onBulkPeriodInput={handleBulkPeriodInput}
                    onAssignAllUnmatched={handleAssignAllUnmatched}
                    onApplyPeriodToAll={handleApplyPeriodToAll}
                    onPeriodInput={handlePreviewPeriodInput}
                    onPeriodClear={handlePreviewPeriodClear}
                    assignmentCount={Object.values(previewAssignments).filter((item) => item?.userId).length}
                    periodCount={Object.values(previewPeriodInputs).filter((value) => value).length}
                    onAssigneeClearAll={handlePreviewAssigneeClearAll}
                    previewLocked={previewLocked}
                    onPreviewLockToggle={handlePreviewLockToggle}
                    previewLocking={previewLocking}
                    preSubmitChecklist={preSubmitChecklist}
                  />
                  {batchesLoading ? (
                    <SkeletonCard lines={3} />
                  ) : batches.length === 0 ? (
                    <EmptyState label="Nessun batch caricato" />
                  ) : (
                    batches.slice(0, 3).map((batch) => (
                      <PayslipBatchCard
                        key={batch.id}
                        batch={batch}
                        onProcess={handleProcessBatch}
                        processing={processingBatch}
                        onDownloadZip={handleDownloadZip}
                        downloading={downloadingBatch}
                        canManage={canManagePayroll}
                        isOwner={isOwner}
                      />
                    ))
                  )}
                </div>
              ) : (
                <div className="hr-portal__banner hr-portal__banner--muted">
                  <p className="hr-portal__muted">Il caricamento dei batch è disponibile solo al team HR.</p>
                </div>
              )}
            </Subsection>

            <Subsection title="Disponibili" description="Elenco buste paga disponibili">
              <div className="hr-portal__filters hr-portal__filters--wrap">
                <label className="hr-portal__field hr-portal__field--wide">
                  <span>Ricerca</span>
                  <input
                    className="hr-portal__input"
                    placeholder="Cerca per periodo o username"
                    value={payslipFilters.search}
                    onChange={(e) => setPayslipFilters({ ...payslipFilters, search: e.target.value, page: 1 })}
                  />
                </label>
                <div className="hr-portal__actions">
                  <button className="hr-portal__button hr-portal__button--ghost" onClick={loadPayslips} disabled={payslipsLoading}>
                    Applica
                  </button>
                  <button
                    className="hr-portal__button hr-portal__button--ghost"
                    onClick={() => handlePayslipPageChange(-1)}
                    disabled={payslipFilters.page <= 1 || payslipsLoading}
                  >
                    ← Prec.
                  </button>
                  <button
                    className="hr-portal__button hr-portal__button--ghost"
                    onClick={() => handlePayslipPageChange(1)}
                    disabled={!payslipHasMore || payslipsLoading}
                  >
                    Succ. →
                  </button>
                </div>
              </div>
              {payslipsLoading ? (
                <div className="hr-portal__grid hr-portal__grid--compact">
                  {[...Array(6)].map((_, idx) => (
                    <SkeletonCard key={idx} lines={3} />
                  ))}
                </div>
              ) : payslips.length === 0 ? (
                <EmptyState label="Nessuna busta paga disponibile" />
              ) : (
                <PayslipList
                  payslips={payslips}
                  onRegeneratePeriod={handleRegeneratePeriod}
                  regenerating={regenerating}
                  canRegenerate={canManagePayroll}
                  onDownloadRenamed={handleDownloadRenamed}
                  downloadingRenamed={downloadingRenamed}
                  isOwner={isOwner}
                />
              )}
            </Subsection>
          </StepSection>

          <StepSection
            step="3"
            title="Comunicazioni"
            subtitle="Notifiche personali e aggiornamenti HR"
          >
            <Subsection
              title="Notifiche"
              description="Dashboard comunicazioni"
              actions={
                <div className="hr-portal__actions">
                  <Badge tone="amber">{publishedNotificationsCount} pubblicate</Badge>
                  <button className="hr-portal__button" onClick={loadNotifications} disabled={notificationsLoading}>
                    {notificationsLoading ? "Aggiornamento…" : "Aggiorna"}
                  </button>
                </div>
              }
            >
              <div className="hr-portal__quick-filters">
                <span className="hr-portal__eyebrow">Filtro rapido stato</span>
                <div className="hr-portal__quick-filters-row">
                  {quickStatusFilters.map((filter) => (
                    <button
                      key={filter.value || "all"}
                      type="button"
                      className={`hr-portal__quick-filter ${notificationQuickFilter.status === filter.value ? "is-active" : ""}`}
                      onClick={() => setNotificationQuickFilter((prev) => ({ ...prev, status: filter.value }))}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>
                <span className="hr-portal__eyebrow">Filtro rapido categoria</span>
                <div className="hr-portal__quick-filters-row">
                  {quickCategoryFilters.map((filter) => (
                    <button
                      key={filter.value || "all"}
                      type="button"
                      className={`hr-portal__quick-filter ${notificationQuickFilter.category === filter.value ? "is-active" : ""}`}
                      onClick={() => setNotificationQuickFilter((prev) => ({ ...prev, category: filter.value }))}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>
              </div>
              {canManageNotifications && (
                <div className="hr-portal__filters">
                  <label className="hr-portal__field">
                    <span>Stato</span>
                    <select
                      className="hr-portal__input"
                      value={notificationFilters.status}
                      onChange={(e) => setNotificationFilters((prev) => ({ ...prev, status: e.target.value }))}
                    >
                      <option value="">Tutti</option>
                      <option value="draft">Bozze</option>
                      <option value="published">Pubblicate</option>
                      <option value="archived">Archiviate</option>
                    </select>
                  </label>
                  <label className="hr-portal__field">
                    <span>Categoria</span>
                    <select
                      className="hr-portal__input"
                      value={notificationFilters.category}
                      onChange={(e) => setNotificationFilters((prev) => ({ ...prev, category: e.target.value }))}
                    >
                      <option value="">Tutte</option>
                      <option value="general">Generale</option>
                      <option value="alert">Allerta</option>
                      <option value="payroll">Buste paga</option>
                      <option value="event">Evento</option>
                    </select>
                  </label>
                  <div className="hr-portal__actions">
                    <button className="hr-portal__button hr-portal__button--ghost" onClick={loadNotifications}>
                      Applica filtri
                    </button>
                  </div>
                </div>
              )}

              <div className="hr-portal__grid hr-portal__grid--two">
                <div className="hr-portal__card hr-portal__card--form">
                  <header className="hr-portal__card-header">
                    <div>
                      <p className="hr-portal__eyebrow">Comunicazioni personali</p>
                      <h3>Bacheca notifiche in sola lettura</h3>
                    </div>
                  </header>
                  <p className="hr-portal__muted">
                    La composizione e lo scheduling delle notifiche sono disponibili nel pannello amministrativo.
                  </p>
                </div>
                <div className="hr-portal__stack">
                  {notificationsLoading ? (
                    [...Array(3)].map((_, idx) => <SkeletonCard key={idx} lines={4} />)
                  ) : visibleNotifications.length === 0 ? (
                    <EmptyState label="Nessuna notifica disponibile" />
                  ) : (
                    visibleNotifications.map((notification) => (
                      <NotificationCard
                        key={notification.id}
                        notification={notification}
                        onPublish={handlePublishNotification}
                        onArchive={handleArchiveNotification}
                        onDeliver={handleDeliverNotification}
                        onResend={handleResendFailed}
                        onViewDeliveries={(id) => loadDeliveries(id, deliveryStatus)}
                        deliveryLoading={deliveryLoading}
                        canManage={canManageNotifications}
                      />
                    ))
                  )}
                </div>
              </div>

              {canManageNotifications && selectedNotification && (
                <div className="hr-portal__card">
                  <header className="hr-portal__card-header">
                    <div>
                      <p className="hr-portal__eyebrow">Monitoraggio recapiti</p>
                      <h3>Notifica #{selectedNotification}</h3>
                    </div>
                    <div className="hr-portal__actions">
                      <select
                        className="hr-portal__input"
                        value={deliveryStatus}
                        onChange={(e) => {
                          setDeliveryStatus(e.target.value);
                          loadDeliveries(selectedNotification, e.target.value);
                        }}
                      >
                        <option value="">Tutti gli stati</option>
                        <option value="pending">In attesa</option>
                        <option value="delivered">Consegnato</option>
                        <option value="failed">Fallito</option>
                        <option value="skipped">Ignorato</option>
                      </select>
                      <button
                        className="hr-portal__button hr-portal__button--ghost"
                        onClick={() => loadDeliveries(selectedNotification, deliveryStatus)}
                        disabled={deliveryLoading === selectedNotification}
                      >
                        {deliveryLoading === selectedNotification ? "Aggiornamento…" : "Ricarica"}
                      </button>
                    </div>
                  </header>
                  <NotificationDeliveries deliveries={deliveriesByNotification[selectedNotification] || []} />
                </div>
              )}
            </Subsection>

            {heroNotification && (
              <div className="hr-portal__banner">
                <div>
                  <p className="hr-portal__eyebrow">Notifica HR</p>
                  <h2>{heroNotification.title}</h2>
                  <p className="hr-portal__muted">{heroNotification.body}</p>
                  {heroNotification.cta_label && heroNotification.cta_url && (
                    <a
                      className={`hr-portal__button ${
                        heroNotification.cta_type === "secondary" ? "hr-portal__button--ghost" : ""
                      }`}
                      href={heroNotification.cta_url}
                      target={heroNotification.cta_url.startsWith("/") ? undefined : "_blank"}
                      rel={heroNotification.cta_url.startsWith("/") ? undefined : "noreferrer"}
                    >
                      {heroNotification.cta_label}
                    </a>
                  )}
                </div>
                {heroNotification.expires_at && (
                  <Pill tone="amber">Scade {formatDate(heroNotification.expires_at)}</Pill>
                )}
              </div>
            )}

          </StepSection>

        </>
      )}




      {isSuperAdmin && (
        <StepSection
          step={preferenceStep}
          title="Preferenze di notifica"
          subtitle="Canali attivi e quiet hours personalizzate"
        >
          <NotificationPreferenceForm
            form={preferenceForm}
            onChange={setPreferenceForm}
            onSubmit={handleSavePreference}
            saving={preferenceSaving}
            onClearQuietHours={handleClearQuietHours}
            error={preferenceStatus.error}
            success={preferenceStatus.success}
            hasPreference={Boolean(preference)}
          />
        </StepSection>
      )}

      {emailModalOpen && selectedUnmatched && (
        <div className="hr-portal__modal-overlay" role="dialog" aria-modal="true">
          <div className="hr-portal__modal" onClick={(event) => event.stopPropagation()}>
            <header className="hr-portal__modal-header">
              <div>
                <p className="hr-portal__eyebrow">Coda DA ASSEGNARE</p>
                <h3>Invia busta paga via email</h3>
              </div>
              <button type="button" className="hr-portal__modal-close" onClick={handleCloseEmailModal}>
                ×
              </button>
            </header>
            <div className="hr-portal__modal-body">
              <div className="hr-portal__form-grid">
                <label className="hr-portal__field hr-portal__field--wide">
                  <span>Destinatario</span>
                  <EmailAutocompleteInput
                    value={emailForm.recipient_email}
                    onInput={(value) => setEmailForm((prev) => ({ ...prev, recipient_email: value }))}
                    onSelect={handleSelectSuggestedEmail}
                    suggestions={emailSuggestions}
                    loading={emailSuggestionsLoading}
                    placeholder="Inserisci l'email del destinatario"
                  />
                </label>
                <label className="hr-portal__field hr-portal__field--wide">
                  <span>Oggetto</span>
                  <input
                    className="hr-portal__input"
                    value={emailForm.subject}
                    onChange={(e) => setEmailForm((prev) => ({ ...prev, subject: e.target.value }))}
                  />
                </label>
                <label className="hr-portal__field hr-portal__field--wide">
                  <span>Corpo</span>
                  <textarea
                    className="hr-portal__input"
                    rows={5}
                    value={emailForm.body}
                    onChange={(e) => setEmailForm((prev) => ({ ...prev, body: e.target.value }))}
                  />
                </label>
              </div>
              <div className="hr-portal__email-preview">
                <p className="hr-portal__eyebrow">Preview email</p>
                <div className="hr-portal__email-card">
                  <div className="hr-portal__email-row">
                    <span className="hr-portal__email-label">Oggetto</span>
                    <span>{emailForm.subject || "—"}</span>
                  </div>
                  <div className="hr-portal__email-row">
                    <span className="hr-portal__email-label">Corpo</span>
                    <p className="hr-portal__email-body">{emailForm.body || "—"}</p>
                  </div>
                  <div className="hr-portal__email-row">
                    <span className="hr-portal__email-label">Allegato</span>
                    <span>{"busta_paga.pdf"}</span>
                  </div>
                </div>
              </div>
              {emailTestResult && (
                <div
                  className={`hr-portal__banner ${emailTestResult.success ? "" : "hr-portal__banner--error"}`}
                  role="status"
                >
                  {emailTestResult.detail}
                </div>
              )}
            </div>
            <footer className="hr-portal__modal-footer">
              <button type="button" className="hr-portal__button hr-portal__button--ghost" onClick={handleCloseEmailModal}>
                Annulla
              </button>
              <button
                type="button"
                className="hr-portal__button hr-portal__button--ghost"
                onClick={handleTestPayslipEmail}
                disabled={emailTestSending}
              >
                {emailTestSending ? "Test SMTP…" : "Test invio"}
              </button>
              <button type="button" className="hr-portal__button" onClick={handleSendPayslipEmail} disabled={emailSending}>
                {emailSending ? "Invio…" : "Invia"}
              </button>
            </footer>
          </div>
        </div>
      )}

      {emailResult && (
        <div className="hr-portal__modal-overlay" role="status" aria-live="polite">
          <div className="hr-portal__modal hr-portal__modal--small" onClick={(event) => event.stopPropagation()}>
            <header className="hr-portal__modal-header">
              <div>
                <p className="hr-portal__eyebrow">Esito invio</p>
                <h3>{emailResult.success ? "✅ Invio riuscito" : "❌ Errore invio"}</h3>
              </div>
              <button type="button" className="hr-portal__modal-close" onClick={() => setEmailResult(null)}>
                ×
              </button>
            </header>
            <div className="hr-portal__modal-body">
              {!emailResult.success && emailResult.detail && (
                <p className="hr-portal__banner hr-portal__banner--error">{emailResult.detail}</p>
              )}
              <div className="hr-portal__email-card">
                <div className="hr-portal__email-row">
                  <span className="hr-portal__email-label">Oggetto</span>
                  <span>{emailResult.subject || "—"}</span>
                </div>
                <div className="hr-portal__email-row">
                  <span className="hr-portal__email-label">Corpo</span>
                  <p className="hr-portal__email-body">{emailResult.body || "—"}</p>
                </div>
                <div className="hr-portal__email-row">
                  <span className="hr-portal__email-label">Allegato</span>
                  <span>{emailResult.attachment_name || "busta_paga.pdf"}</span>
                </div>
              </div>
            </div>
            <footer className="hr-portal__modal-footer">
              <button type="button" className="hr-portal__button" onClick={() => setEmailResult(null)}>
                Chiudi
              </button>
            </footer>
          </div>
        </div>
      )}
    </div>
  );
};

export default HrPortalApp;
