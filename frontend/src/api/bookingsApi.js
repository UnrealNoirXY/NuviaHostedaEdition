import apiClient from '../apiClient';

/**
 * Fetches the aggregated data for the main dashboard view.
 */
export const getDashboardData = () => {
    return apiClient.get('/api/bookings/dashboard/');
};

/**
 * Fetches a paginated list of all bookings.
 * @param {object} params - Optional query parameters for filtering and pagination.
 */
export const getBookings = (params) => {
    return apiClient.get('/api/bookings/bookings/', { params });
};

/**
 * Fetches the details for a single booking.
 * @param {number} id - The ID of the booking.
 */
export const getBookingDetails = (id) => {
    return apiClient.get(`/api/bookings/bookings/${id}/`);
};

/**
 * Creates a new booking.
 * @param {object} bookingData - The data for the new booking.
 */
export const createBooking = (bookingData) => {
    return apiClient.post('/api/bookings/bookings/', bookingData);
};

/**
 * Updates an existing booking.
 * @param {number} id - The ID of the booking to update.
 * @param {object} bookingData - The updated data.
 */
export const updateBooking = (id, bookingData) => {
    return apiClient.put(`/api/bookings/bookings/${id}/`, bookingData);
};

/**
 * Deletes a booking.
 * @param {number} id - The ID of the booking to delete.
 */
export const deleteBooking = (id) => {
    return apiClient.delete(`/api/bookings/bookings/${id}/`);
};

/**
 * Fetches the options for the forms, like companies and resorts.
 */
export const getFormOptions = () => {
    return apiClient.get('/api/bookings/form-options/');
};