import apiClient from '../apiClient';

export function fetchEconomatoOverview(params = {}) {
    return apiClient.get('/economato/api/overview/', { params });
}

export function fetchEconomatoRequests(params = {}) {
    return apiClient.get('/economato/api/requests/', { params });
}

export function createEconomatoRequest(payload) {
    return apiClient.post('/economato/api/requests/', payload);
}

export function updateEconomatoRequest(id, payload) {
    return apiClient.put(`/economato/api/requests/${id}/`, payload);
}

export function changeEconomatoStatus(id, payload) {
    return apiClient.post(`/economato/api/requests/${id}/change_status/`, payload);
}

export function fetchEconomatoItems(params = {}) {
    return apiClient.get('/economato/api/items/', { params });
}

export function fetchEconomatoTimeline(requestId, params = {}) {
    return apiClient.get(`/economato/api/requests/${requestId}/timeline/`, { params });
}

export function fetchCostCenters(params = {}) {
    return apiClient.get('/economato/api/cost-centers/', { params });
}

export function fetchCategories(params = {}) {
    return apiClient.get('/economato/api/categories/', { params });
}
