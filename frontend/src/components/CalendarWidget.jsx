import React, { useState, useEffect, useCallback } from 'react';
import { Calendar, momentLocalizer } from 'react-big-calendar';
import moment from 'moment';
import apiClient from '../apiClient'; // Import the new centralized API client
import 'react-big-calendar/lib/css/react-big-calendar.css';
import './CalendarWidget.css';

// Setup the localizer by providing the moment Object
const localizer = momentLocalizer(moment);

const CalendarWidget = () => {
    const [events, setEvents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showModal, setShowModal] = useState(false);
    const [selectedSlot, setSelectedSlot] = useState(null);
    const [eventTitle, setEventTitle] = useState('');
    const [eventType, setEventType] = useState('event');
    const [view, setView] = useState(window.innerWidth < 768 ? 'agenda' : 'month');
    const [invitees, setInvitees] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [isSearching, setIsSearching] = useState(false);

    useEffect(() => {
        const handleResize = () => {
            setView(window.innerWidth < 768 ? 'agenda' : 'month');
        };

        window.addEventListener('resize', handleResize);
        // Set the initial view
        handleResize();

        return () => window.removeEventListener('resize', handleResize);
    }, []);

    const fetchEvents = useCallback(() => {
        setLoading(true);
        apiClient.get('/api/desk/widget-data/calendar/')
            .then(response => {
                const formattedEvents = response.data.map(event => ({
                    ...event,
                    start: new Date(event.start),
                    end: new Date(event.end),
                }));
                setEvents(formattedEvents);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching calendar events:", err);
                setError("Impossibile caricare il calendario.");
                setLoading(false);
            });
    }, []);

    useEffect(() => {
        fetchEvents();
    }, [fetchEvents]);

    const handleSelectSlot = useCallback(({ start, end }) => {
        setSelectedSlot({ start, end });
        setShowModal(true);
    }, []);

    useEffect(() => {
        if (searchTerm.length < 2) {
            setSearchResults([]);
            return;
        }

        setIsSearching(true);
        const debounceTimeout = setTimeout(() => {
            apiClient.get(`/api/desk/search-invitees/?search=${searchTerm}`)
                .then(response => {
                    const existingInviteeIds = invitees.map(inv => inv.id);
                    const filteredResults = response.data.filter(user => !existingInviteeIds.includes(user.id));
                    setSearchResults(filteredResults);
                })
                .catch(err => console.error("Error searching for invitees:", err))
                .finally(() => setIsSearching(false));
        }, 300);

        return () => clearTimeout(debounceTimeout);
    }, [searchTerm, invitees]);

    const handleAddInvitee = (user) => {
        setInvitees([...invitees, user]);
        setSearchTerm('');
        setSearchResults([]);
    };

    const handleRemoveInvitee = (userId) => {
        setInvitees(invitees.filter(invitee => invitee.id !== userId));
    };

    const handleSaveEvent = () => {
        if (eventTitle && selectedSlot) {
            const newEvent = {
                title: eventTitle,
                start: selectedSlot.start.toISOString(),
                end: selectedSlot.end.toISOString(),
                event_type: eventType,
                attendee_ids: invitees.map(invitee => invitee.id),
            };

            apiClient.post('/api/desk/events/', newEvent)
                .then(response => {
                    // Refetch events to get the latest data including the new one
                    fetchEvents();
                    setShowModal(false);
                    setEventTitle('');
                    setEventType('event');
                    setInvitees([]);
                })
                .catch(err => {
                    console.error("Error saving event:", err);
                    setError("Errore durante il salvataggio dell'evento.");
                });
        }
    };

    if (loading) return <div className="widget-loading">Caricamento...</div>;
    if (error) return <div className="widget-error">{error}</div>;

    return (
        <div className="calendar-widget-container">
            <Calendar
                localizer={localizer}
                events={events}
                startAccessor="start"
                endAccessor="end"
                style={{ height: '100%' }}
                onSelectSlot={handleSelectSlot}
                selectable
                view={view}
                onView={setView}
                eventPropGetter={event => {
                    let className = `event-${event.event_type || 'default'}`;
                    if (event.invitation_status === 'pending') {
                        className += ' event-pending';
                    }
                    return { className: className };
                }}
            />
            {showModal && (
                <div className="widget-popup-overlay" onClick={() => setShowModal(false)}>
                    <div className="widget-popup" onClick={(e) => e.stopPropagation()}>
                        <div className="widget-popup-header">
                            <h5 className="widget-popup-title">Aggiungi Evento</h5>
                            <button type="button" className="btn-close" onClick={() => setShowModal(false)}></button>
                        </div>
                        <div className="widget-popup-body">
                            <div className="mb-3">
                                <label className="form-label">Titolo Evento</label>
                                <input
                                    type="text"
                                    className="form-control"
                                    placeholder="Titolo dell'evento"
                                    value={eventTitle}
                                    onChange={e => setEventTitle(e.target.value)}
                                />
                            </div>
                            <div className="mb-3">
                                <label className="form-label">Tipo</label>
                                <select
                                    className="form-control"
                                    value={eventType}
                                    onChange={e => setEventType(e.target.value)}
                                >
                                    <option value="event">Evento</option>
                                    <option value="task">Task</option>
                                    <option value="appointment">Appuntamento</option>
                                </select>
                            </div>
                            <div className="mb-3">
                                <label className="form-label">Invita Colleghi</label>
                                <div className="invitee-list mb-2">
                                    {invitees.map(invitee => (
                                        <div key={invitee.id} className="invitee-badge">
                                            {invitee.username}
                                            <button onClick={() => handleRemoveInvitee(invitee.id)}>&times;</button>
                                        </div>
                                    ))}
                                </div>
                                <div className="invitee-input-wrapper">
                                    <input
                                        type="text"
                                        className="form-control"
                                        placeholder="Cerca per nome o username..."
                                        value={searchTerm}
                                        onChange={e => setSearchTerm(e.target.value)}
                                    />
                                    {isSearching && <div className="spinner-border spinner-border-sm text-secondary"></div>}
                                    {searchResults.length > 0 && (
                                        <ul className="search-results-list">
                                            {searchResults.map(user => (
                                                <li key={user.id} onClick={() => handleAddInvitee(user)}>
                                                    {user.first_name} {user.last_name} ({user.username})
                                                </li>
                                            ))}
                                        </ul>
                                    )}
                                </div>
                            </div>
                        </div>
                        <div className="widget-popup-footer">
                            <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>Annulla</button>
                            <button type="button" className="btn btn-primary" onClick={handleSaveEvent}>Salva</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default CalendarWidget;
