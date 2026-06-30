import apiClient from "../apiClient";

export async function fetchTickets(params = {}) {
  const response = await apiClient.get("/api/maintenance/tickets/", { params });
  return response.data;
}

export async function fetchTicket(ticketId) {
  const response = await apiClient.get(`/api/maintenance/tickets/${ticketId}/`);
  return response.data;
}

export async function fetchRoomDashboard() {
  const response = await apiClient.get("/api/maintenance/tickets/room-dashboard/");
  return response.data;
}

export async function fetchRoomDetail(roomId) {
  const response = await apiClient.get(`/api/maintenance/tickets/rooms/${roomId}/detail/`);
  return response.data;
}

export async function createTicket(payload) {
  const formData = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    if (Array.isArray(value)) {
      value.forEach((entry) => {
        if (entry !== undefined && entry !== null && entry !== "") {
          formData.append(key, entry);
        }
      });
      return;
    }
    formData.append(key, value);
  });
  const response = await apiClient.post("/api/maintenance/tickets/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function updateTicket(ticketId, payload) {
  const formData = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      formData.append(key, value);
    }
  });
  const response = await apiClient.patch(`/api/maintenance/tickets/${ticketId}/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function addComment(ticketId, payload) {
  const formData = new FormData();
  Object.entries(payload).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      formData.append(key, value);
    }
  });
  const response = await apiClient.post(`/api/maintenance/tickets/${ticketId}/comments/`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function extendDeadline(ticketId, payload) {
  const response = await apiClient.post(`/api/maintenance/tickets/${ticketId}/extend-deadline/`, payload);
  return response.data;
}

export async function fetchMaintenanceMetadata() {
  const response = await apiClient.get("/api/maintenance/tickets/metadata/");
  return response.data;
}

export async function fetchCalendar(params = {}) {
  const response = await apiClient.get("/api/maintenance/tickets/calendar/", { params });
  return response.data;
}

export async function claimTicket(ticketId) {
  const response = await apiClient.post(`/api/maintenance/tickets/${ticketId}/claim/`);
  return response.data;
}

export async function releaseTicket(ticketId) {
  const response = await apiClient.post(`/api/maintenance/tickets/${ticketId}/release/`);
  return response.data;
}

export async function updateUnassignedAlertsPreference(enabled) {
  const response = await apiClient.post("/api/maintenance/tickets/preferences/unassigned-alerts/", { enabled });
  return response.data;
}

export async function fetchTicketInsights() {
  const response = await apiClient.get("/api/maintenance/tickets/insights/");
  return response.data;
}
