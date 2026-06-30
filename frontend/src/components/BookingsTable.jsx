import React, { useState, useEffect, useCallback } from 'react';
import { getBookings, deleteBooking } from '../api/bookingsApi';
import moment from 'moment';

const BookingsTable = () => {
    const [bookings, setBookings] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');

    // Per ora, la paginazione è simulata. In un'app reale, si userebbero parametri nell'API.
    const [currentPage, setCurrentPage] = useState(1);
    const bookingsPerPage = 10;

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            // L'API restituisce tutti i booking, il filtro è client-side per semplicità
            const response = await getBookings();
            setBookings(response.data);
            setError(null);
        } catch (err) {
            setError('Impossibile caricare la lista delle prenotazioni.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const handleDelete = async (bookingId) => {
        if (window.confirm('Sei sicuro di voler eliminare questa prenotazione? L\'azione è irreversibile.')) {
            try {
                await deleteBooking(bookingId);
                // Ricarica i dati per riflettere la cancellazione
                fetchData();
            } catch (err) {
                alert('Errore durante l\'eliminazione della prenotazione.');
                console.error(err);
            }
        }
    };

    const filteredBookings = bookings.filter(booking =>
        booking.guest_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        booking.guest_email.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const indexOfLastBooking = currentPage * bookingsPerPage;
    const indexOfFirstBooking = indexOfLastBooking - bookingsPerPage;
    const currentBookings = filteredBookings.slice(indexOfFirstBooking, indexOfLastBooking);

    if (loading) return <p>Caricamento prenotazioni...</p>;
    if (error) return <div className="alert alert-danger">{error}</div>;

    return (
        <div className="card">
            <div className="card-header d-flex justify-content-between align-items-center">
                <h5 className="mb-0">Tutte le Prenotazioni</h5>
                <input
                    type="text"
                    className="form-control w-25"
                    placeholder="Cerca per nome o email..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                />
            </div>
            <div className="card-body">
                <table className="table table-striped">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Cliente</th>
                            <th>Date Soggiorno</th>
                            <th>Resort</th>
                            <th>Status</th>
                            <th>Azioni</th>
                        </tr>
                    </thead>
                    <tbody>
                        {currentBookings.length > 0 ? currentBookings.map(booking => (
                            <tr key={booking.id}>
                                <td>{booking.booking_engine_id || `MAN-${booking.id}`}</td>
                                <td>{booking.guest_name}</td>
                                <td>{moment(booking.check_in_date).format('DD/MM/YY')} - {moment(booking.check_out_date).format('DD/MM/YY')}</td>
                                <td>{booking.resort.name}</td>
                                <td><span className="badge bg-info">{booking.status_display}</span></td>
                                <td>
                                    <button className="btn btn-sm btn-outline-danger" onClick={() => handleDelete(booking.id)}>
                                        <i className="fas fa-trash"></i>
                                    </button>
                                    {/* Futuri pulsanti per 'Dettagli' o 'Modifica' */}
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="6" className="text-center text-muted">Nessuna prenotazione trovata.</td>
                            </tr>
                        )}
                    </tbody>
                </table>
                {/* Qui andrebbe una paginazione più complessa */}
            </div>
        </div>
    );
};

export default BookingsTable;