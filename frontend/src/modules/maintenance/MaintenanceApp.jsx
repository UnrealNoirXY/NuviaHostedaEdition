import React, { useCallback, useEffect, useState } from "react";
import moment from "moment";
import {
  fetchTickets,
  fetchTicket,
  fetchRoomDashboard,
  fetchMaintenanceMetadata,
  fetchRoomDetail,
  createTicket,
  updateTicket,
  addComment,
  fetchCalendar,
  claimTicket,
  releaseTicket,
  updateUnassignedAlertsPreference,
  fetchTicketInsights,
  extendDeadline,
} from "../../api/maintenanceApi";
import usePwaRegistration from "../../hooks/usePwaRegistration";
import PwaStatusToast from "../../components/PwaStatusToast";
import TicketList from "./components/TicketList";
import TicketDetail from "./components/TicketDetail";
import RoomDashboard from "./components/RoomDashboard";
import TicketForm from "./components/TicketForm";
import MaintenanceCalendar from "./components/MaintenanceCalendar";
import MaintenanceOverview from "./components/MaintenanceOverview";
import MaintenanceToast from "./components/MaintenanceToast";
import SkeletonPlaceholder from "./components/SkeletonPlaceholder";
import MaintenanceMissionControl from "./components/MaintenanceMissionControl";
import MobileTicketCard from "./components/MobileTicketCard";
import MobileTicketDetailNoir from "./components/MobileTicketDetailNoir";
import MobileRoomDetailSheet from "./components/MobileRoomDetailSheet";
import apiClient from "../../apiClient";
import "./maintenance.scss";
import "./maintenance-mobile-noir.scss";

moment.locale("it");

const defaultPermissionMap = {
  canCreateTickets: false,
  canAssignTickets: false,
  canAcknowledgeDeadline: false,
  canRescheduleDeadline: false,
  canClaimTickets: false,
};

const defaultMetadata = {
  resorts: [],
  rooms: [],
  maintainers: [],
  statuses: [],
  priorities: [],
  slaStates: [],
  skills: [],
  tags: [],
  deadlinePrivileges: false,
  canClaimTickets: false,
  receivesUnassignedAlerts: true,
  currentUser: null,
  permissionMap: { ...defaultPermissionMap },
};

const defaultRoomSummary = {
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

const defaultRoomHierarchy = { companies: [], summary: defaultRoomSummary };
const defaultCalendarMetadata = {
  filters: { resorts: [], maintainers: [], statuses: [], priorities: [] },
  scope: { companies: [], resorts: [] },
  permissions: { ...defaultPermissionMap },
};

const parseErrorMessage = (error) => {
  if (!error) return "Si è verificato un errore inatteso.";
  const responseData = error?.response?.data;
  if (typeof responseData === "string") return responseData;
  if (Array.isArray(responseData)) return responseData.join(" ");
  if (responseData && typeof responseData === "object") {
    const firstKey = Object.keys(responseData)[0];
    const message = responseData[firstKey];
    if (Array.isArray(message)) return message.join(" ");
    if (typeof message === "string") return message;
  }
  const detail = error?.message || error?.response?.statusText;
  return detail ? `Operazione non riuscita: ${detail}` : "Si è verificato un errore inatteso.";
};

const filtersStorageKey = "maintenance.filters";
const presetsStorageKey = "maintenance.filterPresets";

const defaultFilters = {
  search: "",
  status: "",
  priority: "",
  due: "",
  ack: "",
  assignment: "",
  resorts: [],
  sla: "",
  skills: [],
  tags: [],
};

const loadStoredValue = (key, fallback) => {
  if (typeof window === "undefined") return fallback;
  try {
    const stored = window.localStorage.getItem(key);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...fallback, ...parsed };
    }
  } catch (error) {
    // Ignore parsing errors and return fallback
  }
  return fallback;
};

const loadStoredPresets = () => {
  if (typeof window === "undefined") return [];
  try {
    const stored = window.localStorage.getItem(presetsStorageKey);
    if (stored) {
      return JSON.parse(stored);
    }
  } catch (error) {
    // Ignore parsing errors and return empty
  }
  return [];
};

export default function MaintenanceApp() {
  const [tickets, setTickets] = useState([]);
  const [selectedTicketId, setSelectedTicketId] = useState(null);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [roomHierarchy, setRoomHierarchy] = useState(defaultRoomHierarchy);
  const [selectedRoomId, setSelectedRoomId] = useState(null);
  const [roomDetail, setRoomDetail] = useState(null);
  const [roomDetailLoading, setRoomDetailLoading] = useState(false);
  const [metadata, setMetadata] = useState(defaultMetadata);
  const [filters, setFilters] = useState(() => loadStoredValue(filtersStorageKey, defaultFilters));
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [activeTab, setActiveTab] = useState(() => {
    if (typeof window === "undefined") return "tickets";
    return window.matchMedia("(max-width: 768px)").matches ? "calendar" : "tickets";
  });
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [calendarMetadata, setCalendarMetadata] = useState(defaultCalendarMetadata);
  const [calendarFilters, setCalendarFilters] = useState({ resort: "", company: "", assigned_to: "", status: "", priority: "" });
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [calendarError, setCalendarError] = useState("");
  const [insights, setInsights] = useState({
    unassigned: { total: 0, overdue: 0, dueSoon: 0, withoutDeadline: 0, percentOverdue: 0 },
    averages: { claimHours: null },
  });
  const [insightsLoading, setInsightsLoading] = useState(false);
  const [preferenceSaving, setPreferenceSaving] = useState(false);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [ticketsError, setTicketsError] = useState("");
  const [roomsLoading, setRoomsLoading] = useState(false);
  const [roomsError, setRoomsError] = useState("");
  const [overviewError, setOverviewError] = useState("");
  const [initializeError, setInitializeError] = useState("");
  const [filterPresets, setFilterPresets] = useState(loadStoredPresets);
  const [toast, setToast] = useState({ message: "", tone: "info" });
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === "undefined") {
      return false;
    }
    return window.matchMedia("(max-width: 768px)").matches;
  });
  const [isDetailSheetOpen, setIsDetailSheetOpen] = useState(false);
  const [isRoomSheetOpen, setIsRoomSheetOpen] = useState(false);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const {
    offlineReady,
    needsRefresh,
    error: pwaError,
    refreshApp,
    dismissNotification,
  } = usePwaRegistration();

  const currentUserId = metadata.currentUser?.id ?? 0;
  const canEditDeadline = Boolean(metadata.deadlinePrivileges || metadata.currentUser?.isSuperuser);

  const showToast = useCallback((message, tone = "info") => {
    setToast({ message, tone });
  }, []);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.body.classList.add("maintenance-mobile-safe");
    }
    return () => {
      if (typeof document !== "undefined") {
        document.body.classList.remove("maintenance-mobile-safe");
      }
    };
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    window.localStorage.setItem(filtersStorageKey, JSON.stringify(filters));
    return undefined;
  }, [filters]);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    window.localStorage.setItem(presetsStorageKey, JSON.stringify(filterPresets));
    return undefined;
  }, [filterPresets]);

  useEffect(() => {
    if (typeof window === "undefined") return undefined;
    const media = window.matchMedia("(max-width: 768px)");
    const handleChange = (event) => setIsMobile(event.matches);
    setIsMobile(media.matches);
    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, []);

  const loadInsights = useCallback(async () => {
    setInsightsLoading(true);
    setOverviewError("");
    try {
      const data = await fetchTicketInsights();
      setInsights({
        unassigned: { total: 0, overdue: 0, dueSoon: 0, withoutDeadline: 0, percentOverdue: 0 },
        averages: { claimHours: null },
        ...data,
      });
    } catch (error) {
      setOverviewError(parseErrorMessage(error));
      showToast(parseErrorMessage(error), "error");
    } finally {
      setInsightsLoading(false);
    }
  }, [showToast]);

  const loadTickets = useCallback(
    async (refreshInsights = true) => {
      setTicketsLoading(true);
      setTicketsError("");
      try {
        const data = await fetchTickets();
        setTickets(data);
        if (refreshInsights) {
          await loadInsights();
        }
      } catch (error) {
        setTicketsError(parseErrorMessage(error));
        showToast(parseErrorMessage(error), "error");
      } finally {
        setTicketsLoading(false);
      }
    },
    [loadInsights, showToast]
  );

  const loadTicket = useCallback(
    async (ticketId) => {
      if (!ticketId) {
        setSelectedTicket(null);
        return;
      }
      try {
        const detail = await fetchTicket(ticketId);
        setSelectedTicket(detail);
      } catch (error) {
        setOverviewError(parseErrorMessage(error));
        showToast(parseErrorMessage(error), "error");
      }
    },
    [showToast]
  );

  const loadCalendar = useCallback(async (filters = {}) => {
    setCalendarLoading(true);
    setCalendarError("");
    try {
      const { events = [], metadata: meta = {} } = await fetchCalendar(filters);
      setCalendarEvents(
        events.map((event) => ({
          ...event,
          start: event.start ? new Date(event.start) : new Date(),
          end: event.end ? new Date(event.end) : new Date(),
          allDay: Boolean(event.allDay),
        }))
      );
      setCalendarMetadata({
        filters: {
          resorts: meta.filters?.resorts ?? [],
          maintainers: meta.filters?.maintainers ?? [],
          statuses: meta.filters?.statuses ?? [],
          priorities: meta.filters?.priorities ?? [],
        },
        scope: {
          companies: meta.scope?.companies ?? [],
          resorts: meta.scope?.resorts ?? [],
        },
        permissions: { ...defaultPermissionMap, ...(meta.permissions ?? {}) },
      });
    } catch (error) {
      setCalendarError(parseErrorMessage(error));
      showToast(parseErrorMessage(error), "error");
    } finally {
      setCalendarLoading(false);
    }
  }, [showToast]);

  const roomExistsInHierarchy = useCallback((roomId, hierarchy) => {
    if (!roomId) return false;
    return hierarchy.companies?.some((company) =>
      company.resorts?.some((resort) => resort.rooms?.some((room) => room.id === roomId))
    );
  }, []);

  const loadRoomDetail = useCallback(async (roomId) => {
    if (!roomId) {
      setRoomDetail(null);
      return;
    }
    setRoomDetailLoading(true);
    setRoomsError("");
    try {
      const detail = await fetchRoomDetail(roomId);
      setRoomDetail(detail);
    } catch (error) {
      setRoomsError(parseErrorMessage(error));
    } finally {
      setRoomDetailLoading(false);
    }
  }, []);

  const loadRooms = useCallback(
    async (refreshDetail = false) => {
      setRoomsLoading(true);
      setRoomsError("");
      try {
        const data = await fetchRoomDashboard();
        setRoomHierarchy({
          companies: data?.companies ?? [],
          summary: data?.summary ?? { ...defaultRoomSummary },
        });

        if (refreshDetail) {
          if (roomExistsInHierarchy(selectedRoomId, data)) {
            await loadRoomDetail(selectedRoomId);
          } else {
            setSelectedRoomId(null);
            setRoomDetail(null);
          }
        }
      } catch (error) {
        setRoomsError(parseErrorMessage(error));
        showToast(parseErrorMessage(error), "error");
      } finally {
        setRoomsLoading(false);
      }
    },
    [loadRoomDetail, roomExistsInHierarchy, selectedRoomId, showToast]
  );

  const refreshAfterMutation = useCallback(
    async (ticketId, refreshRoomDetail = true) => {
      await Promise.all([
        loadTickets(),
        ticketId ? loadTicket(ticketId) : Promise.resolve(),
        loadRooms(refreshRoomDetail),
      ]);
    },
    [loadRooms, loadTicket, loadTickets]
  );

  const fetchUnreadCount = useCallback(async () => {
     try {
        const response = await apiClient.get('/api/notifications/summary/');
        setUnreadNotifications(response.data?.unread_count || 0);
     } catch (e) {
        console.error("Failed to fetch notifications", e);
     }
  }, []);

  const initialize = useCallback(async () => {
    setLoading(true);
    setInitializeError("");
    try {
      const [meta, insightsData] = await Promise.all([
        fetchMaintenanceMetadata(),
        fetchTicketInsights(),
      ]);
      const normalizedPermissionMap = {
        ...defaultPermissionMap,
        ...(meta.permissionMap ?? {}),
      };
      const normalizedMeta = {
        ...defaultMetadata,
        ...meta,
        slaStates: meta.slaStates ?? meta.sla_states ?? [],
        skills: meta.skills ?? meta.required_skills ?? [],
        tags: meta.tags ?? [],
        permissionMap: normalizedPermissionMap,
        canClaimTickets: meta.canClaimTickets ?? normalizedPermissionMap.canClaimTickets,
      };
      setMetadata(normalizedMeta);
      setInsights({
        unassigned: { total: 0, overdue: 0, dueSoon: 0, withoutDeadline: 0, percentOverdue: 0 },
        averages: { claimHours: null },
        ...insightsData,
      });
      await Promise.all([loadTickets(false), loadRooms(), fetchUnreadCount()]);
    } catch (error) {
      setInitializeError(parseErrorMessage(error));
      showToast(parseErrorMessage(error), "error");
    } finally {
      setLoading(false);
    }
  }, [loadRooms, loadTickets, showToast]);

  useEffect(() => {
    initialize();
  }, [initialize]);

  useEffect(() => {
    if (selectedTicketId) {
      loadTicket(selectedTicketId);
    } else {
      setSelectedTicket(null);
    }
  }, [selectedTicketId, loadTicket]);

  useEffect(() => {
    if (!tickets.length) {
      if (selectedTicketId) {
        setSelectedTicketId(null);
      }
      return;
    }

    const hasSelectedTicket = tickets.some((ticket) => ticket.id === selectedTicketId);

    if (!hasSelectedTicket) {
      if (isMobile) {
        if (selectedTicketId !== null) {
          setSelectedTicketId(null);
        }
      } else {
        setSelectedTicketId(tickets[0].id);
      }
    }
  }, [tickets, selectedTicketId, isMobile]);

  useEffect(() => {
    loadCalendar(calendarFilters);
  }, [calendarFilters, loadCalendar]);

  useEffect(() => {
    if (!isMobile) {
      setIsDetailSheetOpen(false);
      return;
    }
    if (selectedTicketId) {
      setIsDetailSheetOpen(true);
    }
  }, [isMobile, selectedTicketId]);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };

  const toggleFilter = (field, value) => {
    setFilters((prev) => ({
      ...prev,
      [field]: prev[field] === value ? "" : value,
    }));
  };

  const handleApplyQuickFilter = (nextFilters) => {
    setFilters((prev) => ({ ...prev, ...nextFilters }));
    setActiveTab("tickets");
  };

  const handleResetFilters = () => {
    setFilters(defaultFilters);
  };

  const handleSavePreset = (name) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    const newPreset = { id: String(Date.now()), name: trimmed, filters };
    setFilterPresets((prev) => {
      const existingNames = prev.filter((preset) => preset.name !== trimmed);
      return [...existingNames, newPreset];
    });
    showToast(`Preset "${trimmed}" salvato`, "success");
  };

  const handleApplyPreset = (presetId) => {
    const preset = filterPresets.find((entry) => entry.id === presetId);
    if (!preset) return;
    setFilters({ ...defaultFilters, ...preset.filters });
    setActiveTab("tickets");
    showToast(`Preset "${preset.name}" applicato`);
  };

  const handleDeletePreset = (presetId) => {
    setFilterPresets((prev) => prev.filter((entry) => entry.id !== presetId));
  };

  const handleSelectTicketFromOverview = (ticketId) => {
    if (!ticketId) return;
    setSelectedTicketId(ticketId);
    setActiveTab("tickets");
    if (isMobile) {
      setIsDetailSheetOpen(true);
    }
  };

  const handleTicketUpdate = async (payload) => {
    if (!selectedTicketId) return;
    await updateTicket(selectedTicketId, payload);
    await refreshAfterMutation(selectedTicketId, true);
  };

  const handleAddComment = async (payload) => {
    if (!selectedTicketId) return;
    await addComment(selectedTicketId, payload);
    await Promise.all([loadTickets(), loadTicket(selectedTicketId)]);
  };

  const performClaim = useCallback(
    async (ticketId) => {
      if (!ticketId) return;
      setTicketsError("");
      try {
        await claimTicket(ticketId);
        await refreshAfterMutation(ticketId, true);
      } catch (error) {
        setTicketsError(parseErrorMessage(error));
        throw error;
      }
    },
    [refreshAfterMutation]
  );

  const performRelease = useCallback(
    async (ticketId) => {
      if (!ticketId) return;
      setTicketsError("");
      try {
        await releaseTicket(ticketId);
        await refreshAfterMutation(ticketId, true);
      } catch (error) {
        setTicketsError(parseErrorMessage(error));
        throw error;
      }
    },
    [refreshAfterMutation]
  );

  const handleClaimTicket = async () => {
    if (!selectedTicketId) return;
    await performClaim(selectedTicketId);
  };

  const handleReleaseTicket = async () => {
    if (!selectedTicketId) return;
    await performRelease(selectedTicketId);
  };

  const handleExtendTicketDeadline = async (payload) => {
    if (!selectedTicketId) return;
    await extendDeadline(selectedTicketId, payload);
    await refreshAfterMutation(selectedTicketId, true);
  };

  const handleToggleUnassignedAlerts = async (enabled) => {
    setPreferenceSaving(true);
    try {
      const response = await updateUnassignedAlertsPreference(enabled);
      setMetadata((prev) => ({ ...prev, receivesUnassignedAlerts: response.receivesUnassignedAlerts }));
    } finally {
      setPreferenceSaving(false);
    }
  };

  const handleCreateTicket = async (payload) => {
    setCreating(true);
    try {
      const created = await createTicket(payload);
      await Promise.all([loadTickets(), loadRooms(true)]);
      setSelectedTicketId(created.id);
    } finally {
      setCreating(false);
    }
  };

  const handleSelectTicketsFromRoom = (ids) => {
    if (!ids.length) return;
    setActiveTab("tickets");
    setSelectedTicketId(ids[0]);
    if (isMobile) {
      setIsDetailSheetOpen(true);
    }
  };

  const handleSelectRoom = async (roomId) => {
    setSelectedRoomId(roomId);
    await loadRoomDetail(roomId);
    if (isMobile) {
      setIsRoomSheetOpen(true);
    }
  };

  const handleCalendarFilterChange = (nextFilters) => {
    setCalendarFilters(nextFilters);
  };

  const handleCalendarEventSelect = (event) => {
    if (!event?.id) return;
    setSelectedTicketId(event.id);
    setActiveTab("tickets");
    if (isMobile) {
      setIsDetailSheetOpen(true);
    }
  };

  const closeDetailSheet = () => {
    setIsDetailSheetOpen(false);
  };

  if (loading) {
    return (
      <div className={isMobile ? "maintenance-mobile-noir" : "maintenance-app"}>
        {!isMobile && (
          <header className="maintenance-app__header">
            <SkeletonPlaceholder lines={1} width="40%" />
            <SkeletonPlaceholder lines={2} />
          </header>
        )}
        <div className={isMobile ? "noir-content" : "maintenance-layout"}>
          <div className={isMobile ? "" : "maintenance-layout__content"}>
            <SkeletonPlaceholder lines={4} />
            <SkeletonPlaceholder lines={6} />
          </div>
        </div>
      </div>
    );
  }

  if (isMobile) {
    const stats = {
      open: tickets.filter(t => t.status === 'open').length,
      overdue: tickets.filter(t => t.due_date && moment(t.due_date).isBefore(moment())).length,
      unassigned: tickets.filter(t => !t.assigned_to).length,
      roomsCritical: roomHierarchy?.summary?.roomsCritical || 0,
    };

    const filteredTickets = tickets.filter((ticket) => {
      if (filters.status && ticket.status !== filters.status) return false;
      if (filters.assignment === "unassigned" && ticket.assigned_to) return false;
      if (filters.due === "overdue") {
        if (!ticket.due_date || moment(ticket.due_date).isSameOrAfter(moment())) return false;
      }
      if (filters.search) {
        const query = filters.search.toLowerCase();
        return ticket.title.toLowerCase().includes(query) || (ticket.room?.name || "").toLowerCase().includes(query);
      }
      return true;
    });

    return (
      <div className="maintenance-mobile-noir">
        <div className="razer-ambient-glow"></div>

        <header className="noir-status-bar">
          <span className="clock">{moment().format("HH:mm")}</span>
          <a href="/hub/" className="back-to-hub">
             <i className="fa-solid fa-house" /> Hub
          </a>
        </header>

        <main className="noir-content">
          {activeTab === 'home' && (
            <MaintenanceMissionControl
              stats={stats}
              onSelectTab={setActiveTab}
              onApplyQuickFilter={handleApplyQuickFilter}
            />
          )}

          {activeTab === 'tickets' && (
            <div className="noir-ticket-list">
              <div className="noir-section-title">I Tuoi Ticket</div>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', overflowX: 'auto', paddingBottom: '0.5rem' }}>
                <input
                   className="noir-search"
                   placeholder="Cerca ticket o stanza..."
                   value={filters.search}
                   onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                   style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '0.6rem 1rem', color: '#fff', fontSize: '0.85rem', flex: 1, minWidth: '180px' }}
                />
                <button
                  className={`noir-btn ${filters.status === 'open' ? 'primary' : 'secondary'}`}
                  onClick={() => toggleFilter('status', 'open')}
                  style={{ whiteSpace: 'nowrap', borderRadius: '12px', padding: '0 1rem' }}
                >Aperti</button>
              </div>

              {filteredTickets.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--nuvia-text-muted)' }}>Nessun ticket trovato.</div>
              ) : (
                filteredTickets.map(ticket => (
                  <MobileTicketCard
                    key={ticket.id}
                    ticket={ticket}
                    onSelect={(id) => { setSelectedTicketId(id); setIsDetailSheetOpen(true); }}
                    onClaim={performClaim}
                    onResolve={() => updateTicket(ticket.id, { status: "resolved" }).then(() => { showToast("Ticket risolto!", "success"); loadTickets(); })}
                    canClaim={metadata.canClaimTickets}
                    currentUserId={currentUserId}
                  />
                ))
              )}
            </div>
          )}

          {activeTab === 'rooms' && (
             <RoomDashboard
                hierarchy={roomHierarchy}
                summary={roomHierarchy.summary}
                selectedRoomId={selectedRoomId}
                roomDetail={roomDetail}
                isRoomDetailLoading={roomDetailLoading}
                onSelectRoom={handleSelectRoom}
                onSelectTickets={handleSelectTicketsFromRoom}
                isLoading={roomsLoading}
                error={roomsError}
             />
          )}

          {activeTab === 'new' && (
             <TicketForm metadata={metadata} onSubmit={handleCreateTicket} isSubmitting={creating} />
          )}
        </main>

        <nav className="noir-bottom-nav">
          <button className={`nav-item ${activeTab === 'home' ? 'active' : ''}`} onClick={() => setActiveTab('home')}>
            <i className="fa-solid fa-house" />
            <span>Home</span>
          </button>
          <button className="nav-item" onClick={() => window.location.assign('/notifications/')}>
            <div style={{ position: 'relative' }}>
               <i className="fa-solid fa-bell" />
               {unreadNotifications > 0 && (
                 <span style={{ position: 'absolute', top: '-5px', right: '-8px', background: 'var(--nuvia-danger)', color: '#fff', fontSize: '0.6rem', borderRadius: '50%', width: '16px', height: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: '800', border: '2px solid var(--nuvia-bg)' }}>
                   {unreadNotifications > 9 ? '9+' : unreadNotifications}
                 </span>
               )}
            </div>
            <span>Alert</span>
          </button>
          <button className={`nav-item ${activeTab === 'tickets' ? 'active' : ''}`} onClick={() => setActiveTab('tickets')}>
            <i className="fa-solid fa-clipboard-list" />
            <span>Ticket</span>
          </button>
          <button className={`nav-item ${activeTab === 'rooms' ? 'active' : ''}`} onClick={() => setActiveTab('rooms')}>
            <i className="fa-solid fa-bed" />
            <span>Camere</span>
          </button>
          <button className={`nav-item ${activeTab === 'new' ? 'active' : ''}`} onClick={() => setActiveTab('new')}>
            <i className="fa-solid fa-plus" />
            <span>Nuovo</span>
          </button>
        </nav>

        {isDetailSheetOpen && selectedTicket && (
          <MobileTicketDetailNoir
            ticket={selectedTicket}
            onClose={() => setIsDetailSheetOpen(false)}
            onUpdate={handleTicketUpdate}
            onAddComment={handleAddComment}
            onClaim={handleClaimTicket}
            onRelease={handleReleaseTicket}
            canClaim={metadata.canClaimTickets}
            currentUserId={currentUserId}
            metadata={metadata}
          />
        )}

        {isRoomSheetOpen && roomDetail && (
          <MobileRoomDetailSheet
            detail={roomDetail}
            onClose={() => setIsRoomSheetOpen(false)}
            onSelectTickets={(ids) => {
               setIsRoomSheetOpen(false);
               handleSelectTicketsFromRoom(ids);
            }}
          />
        )}

        <MaintenanceToast message={toast.message} tone={toast.tone} onClose={() => setToast({ message: "", tone: "info" })} />
      </div>
    );
  }

  return (
    <div className="maintenance-app">
      <header className="maintenance-app__header">
        <div className="maintenance-app__title">Manutenzione</div>
        <p className="text-muted">Gestisci ticket, scadenze e stato delle camere con un'unica interfaccia reattiva.</p>
        <div className="maintenance-tabs">
          <button
            type="button"
            className={`maintenance-tab ${activeTab === "tickets" ? "maintenance-tab--active" : ""}`}
            onClick={() => handleTabChange("tickets")}
          >
            Ticket
          </button>
          <button
            type="button"
            className={`maintenance-tab ${activeTab === "calendar" ? "maintenance-tab--active" : ""}`}
            onClick={() => handleTabChange("calendar")}
          >
            Calendario
          </button>
          <button
            type="button"
            className={`maintenance-tab ${activeTab === "rooms" ? "maintenance-tab--active" : ""}`}
            onClick={() => handleTabChange("rooms")}
          >
            Camere
          </button>
          <button
            type="button"
            className={`maintenance-tab ${activeTab === "new" ? "maintenance-tab--active" : ""}`}
            onClick={() => handleTabChange("new")}
          >
            Nuovo ticket
          </button>
        </div>
      </header>

      {initializeError && (
        <div className="maintenance-alert maintenance-alert--error" role="alert">
          <i className="fa-solid fa-triangle-exclamation" aria-hidden="true" /> {initializeError}
        </div>
      )}

      {overviewError && !initializeError && (
        <div className="maintenance-alert maintenance-alert--warning" role="status">
          <i className="fa-solid fa-circle-info" aria-hidden="true" /> {overviewError}
        </div>
      )}

      {activeTab === "tickets" && (
        <div className="maintenance-layout">
          <MaintenanceOverview
            tickets={tickets}
            onApplyQuickFilter={handleApplyQuickFilter}
            onSelectTab={handleTabChange}
            onSelectTicket={handleSelectTicketFromOverview}
            activeQuickFilters={{ status: filters.status, due: filters.due, ack: filters.ack, assignment: filters.assignment }}
            insights={insights}
            insightsLoading={insightsLoading}
            ticketsLoading={ticketsLoading}
            canClaim={metadata.canClaimTickets}
            receivesUnassignedAlerts={metadata.receivesUnassignedAlerts}
            onToggleAlerts={handleToggleUnassignedAlerts}
            preferenceSaving={preferenceSaving}
            error={ticketsError}
          />
          <div className={`maintenance-layout__content ${isMobile ? "maintenance-layout__content--mobile" : ""}`}>
            <TicketList
              tickets={tickets}
              selectedId={selectedTicketId}
              onSelect={(id) => {
                setSelectedTicketId(id);
                if (isMobile) {
                  setIsDetailSheetOpen(true);
                }
              }}
              filters={filters}
              onFilterChange={setFilters}
              onResetFilters={handleResetFilters}
              presets={filterPresets}
              onSavePreset={handleSavePreset}
              onApplyPreset={handleApplyPreset}
              onDeletePreset={handleDeletePreset}
              metadata={metadata}
              isLoading={ticketsLoading}
              error={ticketsError}
              canQuickClaim={metadata.canClaimTickets}
              canManageAssignments={metadata.permissionMap?.canAssignTickets}
              onQuickClaim={performClaim}
              onQuickRelease={performRelease}
              currentUserId={currentUserId}
              isCompact={isMobile}
            />
            {!isMobile && (
              <TicketDetail
                ticket={selectedTicket}
                metadata={metadata}
                canEditDeadline={canEditDeadline}
                onUpdate={handleTicketUpdate}
                onAddComment={handleAddComment}
                onClaim={handleClaimTicket}
                onRelease={handleReleaseTicket}
                canClaim={metadata.canClaimTickets}
                currentUserId={currentUserId}
                onExtendDeadline={handleExtendTicketDeadline}
              />
            )}
          </div>
          {isMobile && (
            <div className={`maintenance-sheet ${isDetailSheetOpen ? "maintenance-sheet--open" : ""}`}>
              <button type="button" className="maintenance-sheet__backdrop" onClick={closeDetailSheet} aria-hidden="true" />
              <div
                className="maintenance-sheet__content"
                role="dialog"
                aria-modal="true"
                aria-label="Dettaglio ticket"
              >
                <div className="maintenance-sheet__handle" aria-hidden="true" />
                <button type="button" className="maintenance-sheet__close" onClick={closeDetailSheet} aria-label="Chiudi dettaglio ticket">
                  <span className="visually-hidden">Chiudi dettaglio ticket</span>
                  <i className="fa-solid fa-xmark" aria-hidden="true" />
                </button>
                <TicketDetail
                  ticket={selectedTicket}
                  metadata={metadata}
                  canEditDeadline={canEditDeadline}
                  onUpdate={handleTicketUpdate}
                  onAddComment={handleAddComment}
                  onClaim={handleClaimTicket}
                  onRelease={handleReleaseTicket}
                  canClaim={metadata.canClaimTickets}
                  currentUserId={currentUserId}
                  onExtendDeadline={handleExtendTicketDeadline}
                  isCompact
                  onClose={closeDetailSheet}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === "rooms" && (
        <div className="ticket-detail">
          <RoomDashboard
            hierarchy={roomHierarchy}
            summary={roomHierarchy.summary}
            selectedRoomId={selectedRoomId}
            roomDetail={roomDetail}
            isRoomDetailLoading={roomDetailLoading}
            onSelectRoom={handleSelectRoom}
            onSelectTickets={handleSelectTicketsFromRoom}
            isLoading={roomsLoading}
            error={roomsError}
          />
        </div>
      )}

      {activeTab === "calendar" && (
        <MaintenanceCalendar
          events={calendarEvents}
          metadata={calendarMetadata}
          filters={calendarFilters}
          onFilterChange={handleCalendarFilterChange}
          onSelectEvent={handleCalendarEventSelect}
          isLoading={calendarLoading}
          error={calendarError}
          onRetry={() => loadCalendar(calendarFilters)}
        />
      )}

      {activeTab === "new" && !isMobile && (
        <TicketForm metadata={metadata} onSubmit={handleCreateTicket} isSubmitting={creating} />
      )}

      {isMobile && activeTab === "new" && (
        <div className="maintenance-form-sheet">
          <button
            type="button"
            className="maintenance-form-sheet__backdrop"
            onClick={() => handleTabChange("tickets")}
            aria-hidden="true"
          />
          <div className="maintenance-form-sheet__content" role="dialog" aria-modal="true" aria-label="Nuovo ticket">
            <div className="maintenance-form-sheet__header">
              <h3>Nuovo ticket</h3>
              <button
                type="button"
                className="maintenance-form-sheet__close"
                onClick={() => handleTabChange("tickets")}
                aria-label="Chiudi"
              >
                <i className="fa-solid fa-xmark" aria-hidden="true" />
              </button>
            </div>
            <TicketForm metadata={metadata} onSubmit={handleCreateTicket} isSubmitting={creating} />
          </div>
        </div>
      )}

      {isMobile && (
        <button
          type="button"
          className="maintenance-mobile-fab"
          onClick={() => handleTabChange("new")}
          aria-label="Nuovo ticket"
        >
          <i className="fa-solid fa-plus" aria-hidden="true" />
        </button>
      )}

      <nav className="maintenance-mobile-nav" aria-label="Navigazione manutenzione">
        <button
          type="button"
          className={`maintenance-mobile-nav__item ${activeTab === "tickets" ? "maintenance-mobile-nav__item--active" : ""}`}
          onClick={() => handleTabChange("tickets")}
          aria-current={activeTab === "tickets" ? "page" : undefined}
        >
          <i className="fa-solid fa-clipboard-list" aria-hidden="true" />
          <span>Ticket</span>
        </button>
        <button
          type="button"
          className={`maintenance-mobile-nav__item ${activeTab === "calendar" ? "maintenance-mobile-nav__item--active" : ""}`}
          onClick={() => handleTabChange("calendar")}
          aria-current={activeTab === "calendar" ? "page" : undefined}
        >
          <i className="fa-regular fa-calendar" aria-hidden="true" />
          <span>Calendario</span>
        </button>
        <button
          type="button"
          className={`maintenance-mobile-nav__item ${activeTab === "rooms" ? "maintenance-mobile-nav__item--active" : ""}`}
          onClick={() => handleTabChange("rooms")}
          aria-current={activeTab === "rooms" ? "page" : undefined}
        >
          <i className="fa-solid fa-bed" aria-hidden="true" />
          <span>Camere</span>
        </button>
        <button
          type="button"
          className={`maintenance-mobile-nav__item ${activeTab === "new" ? "maintenance-mobile-nav__item--active" : ""}`}
          onClick={() => handleTabChange("new")}
          aria-current={activeTab === "new" ? "page" : undefined}
        >
          <i className="fa-solid fa-plus" aria-hidden="true" />
          <span>Nuovo</span>
        </button>
      </nav>

      <PwaStatusToast
        offlineReady={offlineReady}
        needsRefresh={needsRefresh}
        error={pwaError}
        onRefresh={refreshApp}
        onDismiss={dismissNotification}
      />
      <MaintenanceToast message={toast.message} tone={toast.tone} onClose={() => setToast({ message: "", tone: "info" })} />
    </div>
  );
}
