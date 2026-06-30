import axios from 'axios';
import Cookies from 'js-cookie';

// Setup an Axios instance with CSRF token
const apiClient = axios.create({
    baseURL: '/api/menu-generator',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': Cookies.get('csrftoken'),
    },
});

// --- Piatto Endpoints ---
export const getPiatti = (params = {}) => apiClient.get('/piatti/', { params });
export const getPiatto = (id) => apiClient.get(`/piatti/${id}/`);
export const createPiatto = (piattoData) => apiClient.post('/piatti/', piattoData);
export const updatePiatto = (id, piattoData) => apiClient.put(`/piatti/${id}/`, piattoData);
export const deletePiatto = (id) => apiClient.delete(`/piatti/${id}/`);
export const clonePiatto = (id, payload = {}) => apiClient.post(`/piatti/${id}/clone/`, payload);

// --- Ingrediente Endpoints ---
export const getIngredienti = (params = {}) => apiClient.get('/ingredienti/', { params });
export const getIngrediente = (id) => apiClient.get(`/ingredienti/${id}/`);
export const createIngrediente = (ingredienteData) => apiClient.post('/ingredienti/', ingredienteData);
export const updateIngrediente = (id, ingredienteData) => apiClient.put(`/ingredienti/${id}/`, ingredienteData);
export const deleteIngrediente = (id) => apiClient.delete(`/ingredienti/${id}/`);

// --- Allergene Endpoints ---
export const getAllergeni = (params = {}) => apiClient.get('/allergeni/', { params });
export const createAllergene = (payload) => apiClient.post('/allergeni/', payload);
export const updateAllergene = (id, payload) => apiClient.put(`/allergeni/${id}/`, payload);
export const deleteAllergene = (id) => apiClient.delete(`/allergeni/${id}/`);

// --- Alimenti Base Endpoints ---
export const getAlimentiBase = (params = {}) => apiClient.get('/alimenti-base/', { params });
export const createAlimentoBase = (payload) => apiClient.post('/alimenti-base/', payload);
export const updateAlimentoBase = (id, payload) => apiClient.put(`/alimenti-base/${id}/`, payload);
export const deleteAlimentoBase = (id) => apiClient.delete(`/alimenti-base/${id}/`);

// --- Menu Endpoints ---
export const getMenus = (params = {}) => apiClient.get('/menu/', { params });
export const getMenu = (id) => apiClient.get(`/menu/${id}/`);
export const createMenu = (menuData) => apiClient.post('/menu/', menuData);
export const updateMenu = (id, menuData) => apiClient.put(`/menu/${id}/`, menuData);
export const deleteMenu = (id) => apiClient.delete(`/menu/${id}/`);
export const addPiattoToMenu = (menuId, piattoId) => apiClient.post(`/menu/${menuId}/add_piatto/`, { piatto_id: piattoId });
export const removePiattoFromMenu = (menuId, piattoId) => apiClient.post(`/menu/${menuId}/remove_piatto/`, { piatto_id: piattoId });
export const reorderPiattiInMenu = (menuId, order) => apiClient.post(`/menu/${menuId}/reorder_piatti/`, { order });
export const validateMenuDraft = (payload) => apiClient.post('/menu/validate/', payload);
export const getMenuVersions = (menuId) => apiClient.get(`/menu/${menuId}/versions/`);
export const getMenuVersionDiff = (menuId, versionId) => apiClient.get(`/menu/${menuId}/versions/${versionId}/diff/`);
export const restoreMenuVersion = (menuId, versionId) => apiClient.post(`/menu/${menuId}/versions/${versionId}/restore/`);
export const createMenuSnapshot = (menuId) => apiClient.post(`/menu/${menuId}/versions/snapshot/`);
export const startMenuDocumentJob = (menuId, payload) => apiClient.post(`/menu/${menuId}/generate-documents/`, payload);
export const getMenuDocumentJobStatus = (jobId) => apiClient.get(`/menu/document-jobs/${jobId}/`);
export const getMenuInsights = (menuId, params = {}) => apiClient.get(`/menu/${menuId}/insights/`, { params });
export const getMenuAuditTrail = (menuId, params = {}) => apiClient.get(`/menu/${menuId}/audit/`, { params });
export const getMenuDocumentHealth = () => apiClient.get('/menu/document-health/');

// --- Permissions ---
export const getPermissions = () => apiClient.get('/permissions/');
export const getExecutiveDashboard = (params = {}) => apiClient.get('/executive-dashboard/', { params });

// --- Layout Endpoints ---
export const getLayouts = (params = {}) => apiClient.get('/layouts/', { params });
export const getLayout = (id) => apiClient.get(`/layouts/${id}/`);
export const createLayout = (layoutData) => {
    // Similar logic for FormData on create if logo can be added initially
    return apiClient.post('/layouts/', layoutData);
};

export const updateLayout = (id, layoutData) => {
    const isFormData = layoutData instanceof FormData;

    return apiClient.patch(`/layouts/${id}/`, layoutData, {
        headers: {
            'Content-Type': isFormData ? 'multipart/form-data' : 'application/json',
        },
    });
};

export const deleteLayout = (id) => apiClient.delete(`/layouts/${id}/`);

// --- Cavaliere Template Endpoints ---
export const getCavalieri = (params = {}) => apiClient.get('/cavalieri/', { params });
export const createCavaliere = (payload) => apiClient.post('/cavalieri/', payload);
export const updateCavaliere = (id, payload) => apiClient.put(`/cavalieri/${id}/`, payload);
export const deleteCavaliere = (id) => apiClient.delete(`/cavalieri/${id}/`);

export default apiClient;
