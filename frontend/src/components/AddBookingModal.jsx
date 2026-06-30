import React, { useState, useEffect } from 'react';
import { createBooking } from '../api/bookingsApi';
import { getFormOptions } from '../api/bookingsApi';

const AddBookingModal = ({ show, onClose, onBookingAdded }) => {
    const initialBookingData = {
        guest_name: '',
        guest_email: '',
        check_in_date: '',
        check_out_date: '',
        resort: '',
        room_details: '',
        booking_engine_id: '',
    };
    const [bookingData, setBookingData] = useState(initialBookingData);
    const [formOptions, setFormOptions] = useState({ companies: [], resorts: [] });
    const [filteredResorts, setFilteredResorts] = useState([]);
    const [selectedCompany, setSelectedCompany] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState(null);

    useEffect(() => {
        // Carica le opzioni solo quando il modale diventa visibile
        if (show) {
            getFormOptions()
                .then(response => {
                    setFormOptions(response.data);
                    setFilteredResorts(response.data.resorts); // Inizialmente mostra tutti i resort
                })
                .catch(err => {
                    console.error("Errore nel caricare le opzioni del form:", err);
                    setError("Impossibile caricare le opzioni per il form.");
                });
        }
    }, [show]);

    const handleCompanyChange = (e) => {
        const companyId = e.target.value;
        setSelectedCompany(companyId);
        if (companyId) {
            // Filtra i resort in base alla società selezionata
            const resortsOfCompany = formOptions.resorts.filter(
                resort => resort.company === parseInt(companyId)
            );
            setFilteredResorts(resortsOfCompany);
        } else {
            setFilteredResorts(formOptions.resorts);
        }
        // Resetta la selezione del resort
        setBookingData(prevData => ({ ...prevData, resort: '' }));
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setBookingData(prevData => ({ ...prevData, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSaving(true);
        setError(null);
        try {
            const response = await createBooking(bookingData);
            onBookingAdded(response.data);
            handleClose();
        } catch (err) {
            setError('Errore durante il salvataggio. Controlla i campi e riprova.');
            console.error(err);
        } finally {
            setIsSaving(false);
        }
    };

    const handleClose = () => {
        // Resetta lo stato prima di chiudere
        setBookingData(initialBookingData);
        setSelectedCompany('');
        setError(null);
        onClose();
    };

    if (!show) return null;

    return (
        <div className="modal" tabIndex="-1" style={{ display: 'block', backgroundColor: 'rgba(0,0,0,0.5)' }}>
            <div className="modal-dialog modal-dialog-centered">
                <div className="modal-content">
                    <div className="modal-header">
                        <h5 className="modal-title">Aggiungi Nuova Prenotazione</h5>
                        <button type="button" className="btn-close" onClick={handleClose}></button>
                    </div>
                    <div className="modal-body">
                        {error && <div className="alert alert-danger">{error}</div>}
                        <form id="add-booking-form" onSubmit={handleSubmit}>
                            <div className="mb-3">
                                <label htmlFor="company" className="form-label">Società</label>
                                <select className="form-select" id="company" name="company" value={selectedCompany} onChange={handleCompanyChange}>
                                    <option value="">Seleziona una società...</option>
                                    {formOptions.companies.map(company => <option key={company.id} value={company.id}>{company.name}</option>)}
                                </select>
                            </div>
                             <div className="mb-3">
                                <label htmlFor="resort" className="form-label">Resort</label>
                                <select className="form-select" id="resort" name="resort" value={bookingData.resort} onChange={handleChange} required>
                                    <option value="">Seleziona un resort...</option>
                                    {filteredResorts.map(resort => <option key={resort.id} value={resort.id}>{resort.name}</option>)}
                                </select>
                            </div>
                            <hr/>
                            <div className="mb-3">
                                <label htmlFor="guest_name" className="form-label">Nome Cliente</label>
                                <input type="text" className="form-control" id="guest_name" name="guest_name" value={bookingData.guest_name} onChange={handleChange} required />
                            </div>
                             <div className="mb-3">
                                <label htmlFor="guest_email" className="form-label">Email Cliente</label>
                                <input type="email" className="form-control" id="guest_email" name="guest_email" value={bookingData.guest_email} onChange={handleChange} required />
                            </div>
                            <div className="row">
                                <div className="col-md-6 mb-3">
                                    <label htmlFor="check_in_date" className="form-label">Data Check-in</label>
                                    <input type="date" className="form-control" id="check_in_date" name="check_in_date" value={bookingData.check_in_date} onChange={handleChange} required />
                                </div>
                                <div className="col-md-6 mb-3">
                                    <label htmlFor="check_out_date" className="form-label">Data Check-out</label>
                                    <input type="date" className="form-control" id="check_out_date" name="check_out_date" value={bookingData.check_out_date} onChange={handleChange} required />
                                </div>
                            </div>
                            <div className="mb-3">
                                <label htmlFor="booking_engine_id" className="form-label">ID Booking Esterno (Opzionale)</label>
                                <input type="text" className="form-control" id="booking_engine_id" name="booking_engine_id" value={bookingData.booking_engine_id} onChange={handleChange} />
                            </div>
                        </form>
                    </div>
                    <div className="modal-footer">
                        <button type="button" className="btn btn-secondary" onClick={handleClose}>Annulla</button>
                        <button type="submit" form="add-booking-form" className="btn btn-primary" disabled={isSaving}>
                            {isSaving ? 'Salvataggio...' : 'Salva Prenotazione'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AddBookingModal;