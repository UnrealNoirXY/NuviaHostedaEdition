import React, { useState, useEffect, useCallback } from 'react';
import { getDashboardData } from './api/bookingsApi';
import ArrivalsChart from './components/ArrivalsChart';
import AddBookingModal from './components/AddBookingModal';
import BookingsTable from './components/BookingsTable'; // Importa la nuova tabella
import TopNav from './components/TopNav';

const KpiCard = ({ title, value, colorClass }) => (
    <div className="card kpi-card">
        <div className="card-body">
            <div className={`kpi-number ${colorClass}`}>{value}</div>
            <div className="kpi-label">{title}</div>
        </div>
    </div>
);

const RecentActivityTable = ({ bookings }) => (
    <div className="card h-100">
        <div className="card-header"><h5 className="card-title mb-0">Check-in Recenti</h5></div>
        <div className="card-body">
            <table className="table table-hover">
                <thead>
                    <tr><th>Cliente</th><th>Resort</th><th>Status</th></tr>
                </thead>
                <tbody>
                    {bookings && bookings.length > 0 ? (
                        bookings.map(booking => (
                            <tr key={booking.id}>
                                <td>{booking.guest_name}</td>
                                <td>{booking.resort.name}</td>
                                <td><span className="badge bg-success">{booking.status_display}</span></td>
                            </tr>
                        ))
                    ) : (
                        <tr><td colSpan="3" className="text-center text-muted">Nessuna attività recente.</td></tr>
                    )}
                </tbody>
            </table>
        </div>
    </div>
);

const BookingsDashboard = () => {
    const [dashboardData, setDashboardData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [refreshKey, setRefreshKey] = useState(0); // Stato per forzare il re-render

    const fetchData = useCallback(async () => {
        try {
            setLoading(true);
            const response = await getDashboardData();
            setDashboardData(response.data);
            setError(null);
        } catch (err) {
            setError('Impossibile caricare i dati del cruscotto.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchData();
    }, [fetchData, refreshKey]);

    const handleBookingAdded = () => {
        // Quando una prenotazione viene aggiunta, forziamo l'aggiornamento
        setRefreshKey(oldKey => oldKey + 1);
    };

    if (loading) {
        return (
            <>
                <TopNav />
                <div className="container p-4 text-center"><h3>Caricamento in corso...</h3></div>
            </>
        );
    }
    if (error) {
        return (
            <>
                <TopNav />
                <div className="container p-4 alert alert-danger">{error}</div>
            </>
        );
    }
    if (!dashboardData) return null;

    const { kpis, arrivals_chart, recent_activity } = dashboardData;

    return (
        <>
            <TopNav />
            <AddBookingModal
                show={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onBookingAdded={handleBookingAdded}
            />
            <div className="container-fluid p-4">
                <div className="dashboard-header d-flex justify-content-between align-items-center mb-4">
                    <div className="container">
                        <div className="row align-items-center">
                             <div className="col-md-8">
                                <h2>Cruscotto Check-in</h2>
                                <p className="text-muted mb-0">Gestione e monitoraggio delle prenotazioni e dei check-in.</p>
                            </div>
                            <div className="col-md-4 text-end">
                                <button className="btn btn-primary" onClick={() => setIsModalOpen(true)}>
                                    <i className="fas fa-plus me-2"></i>
                                    Aggiungi Prenotazione
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
                <div className="container">
                    <div className="row g-4 mb-4">
                        <div className="col-md-4"><KpiCard title="Arrivi Previsti Oggi" value={kpis.arrivals_today} colorClass="text-primary" /></div>
                        <div className="col-md-4"><KpiCard title="Check-in Completati Oggi" value={kpis.completed_checkins_today} colorClass="text-success" /></div>
                        <div className="col-md-4"><KpiCard title="In Attesa di Check-in Oggi" value={kpis.pending_checkins_today} colorClass="text-warning" /></div>
                    </div>
                    <div className="row g-4 mb-4">
                        <div className="col-lg-7">
                            <div className="card h-100"><div className="card-body"><ArrivalsChart labels={arrivals_chart.labels} data={arrivals_chart.data} /></div></div>
                        </div>
                        <div className="col-lg-5">
                            <RecentActivityTable bookings={recent_activity} />
                        </div>
                    </div>
                    <div className="row g-4">
                        <div className="col-12">
                            <BookingsTable key={refreshKey} />
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default BookingsDashboard;
