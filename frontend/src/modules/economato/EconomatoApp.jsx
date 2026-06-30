import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
    changeEconomatoStatus,
    createEconomatoRequest,
    fetchCostCenters,
    fetchEconomatoItems,
    fetchEconomatoOverview,
    fetchEconomatoRequests,
    fetchEconomatoTimeline,
} from '../../api/economatoApi';
import TopNav from '../../components/TopNav';
import './economato.css';

const STATUS_METADATA = {
    draft: { label: 'Bozza', color: 'secondary' },
    pending: { label: 'In Approvazione', color: 'warning' },
    approved: { label: 'Approvata', color: 'success' },
    fulfilled: { label: 'Completata', color: 'primary' },
    rejected: { label: 'Rifiutata', color: 'danger' },
    cancelled: { label: 'Annullata', color: 'dark' },
};

const PRIORITY_BADGES = {
    low: 'bg-secondary',
    medium: 'bg-info',
    high: 'bg-warning text-dark',
    critical: 'bg-danger',
};

const TABS = [
    { id: 'overview', label: 'Panoramica' },
    { id: 'requests', label: 'Richieste' },
    { id: 'catalogue', label: 'Catalogo' },
];

const DEFAULT_ITEM = {
    item: '',
    description: '',
    quantity: 1,
    unit_of_measure: '',
    unit_cost: '',
    supplier: '',
};

const formatCurrency = (value) => {
    const number = Number(value || 0);
    return number.toLocaleString('it-IT', {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 2,
    });
};

const ScopeSelector = ({ overview, filters, onChange }) => {
    if (!overview) return null;
    const companyOptions = overview.available_companies || [];
    const resortOptions = overview.available_resorts || [];
    const allowCompanySelection = overview.scope?.is_global || companyOptions.length > 1;
    const allowResortSelection = resortOptions.length > 1;

    return (
        <div className="row g-3 align-items-end mt-3">
            {allowCompanySelection && (
                <div className="col-md-4">
                    <label className="form-label text-white-50">Società</label>
                    <select
                        className="form-select"
                        value={filters.company || ''}
                        onChange={(event) => onChange({ company: event.target.value || undefined, resort: undefined })}
                    >
                        <option value="">Tutte</option>
                        {companyOptions.map((company) => (
                            <option key={company.id} value={company.id}>
                                {company.name}
                            </option>
                        ))}
                    </select>
                </div>
            )}
            {allowResortSelection && (
                <div className="col-md-4">
                    <label className="form-label text-white-50">Resort</label>
                    <select
                        className="form-select"
                        value={filters.resort || ''}
                        onChange={(event) => onChange({ resort: event.target.value || undefined })}
                    >
                        <option value="">Tutti</option>
                        {resortOptions
                            .filter((resort) => {
                                if (!filters.company) return true;
                                return String(resort.company_id) === String(filters.company);
                            })
                            .map((resort) => (
                                <option key={resort.id} value={resort.id}>
                                    {resort.name}
                                </option>
                            ))}
                    </select>
                </div>
            )}
            {!allowCompanySelection && !allowResortSelection && (
                <div className="col-md-6">
                    <div className="alert alert-light shadow-sm mb-0">
                        <div className="fw-semibold mb-1">Visibilità assegnata</div>
                        <p className="mb-0 small">
                            Stai visualizzando i dati per <strong>{overview.scope?.current_resort_id ? 'il tuo resort' : 'la tua società'}</strong>.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
};

const StatCard = ({ label, value, accent }) => (
    <div className="card economato-stats-card h-100 border-0">
        <div className="card-body">
            <span className="badge rounded-pill bg-opacity-25 text-uppercase mb-2" style={{ backgroundColor: accent }}>
                {label}
            </span>
            <h3 className="fw-bold">{value}</h3>
        </div>
    </div>
);

const LowStockList = ({ items }) => {
    if (!items?.length) {
        return (
            <div className="card h-100">
                <div className="card-body d-flex align-items-center justify-content-center text-muted">
                    Nessun articolo sotto scorta minima.
                </div>
            </div>
        );
    }

    return (
        <div className="card h-100">
            <div className="card-header border-0 bg-transparent">
                <h5 className="card-title mb-0">Articoli critici</h5>
            </div>
            <div className="card-body economato-low-stock">
                <div className="list-group list-group-flush">
                    {items.map((stock) => (
                        <div key={stock.id} className="list-group-item px-0 d-flex justify-content-between align-items-center">
                            <div>
                                <div className="fw-semibold">{stock.item_name}</div>
                                <div className="text-muted small">{stock.resort_name || 'Multi-resort'}</div>
                            </div>
                            <span className="badge bg-danger-subtle text-danger">Disponibili: {stock.available_quantity}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

const RequestsBoard = ({ grouped, onSelect, activeId }) => (
    <div className="row g-3 row-cols-1 row-cols-md-2 row-cols-xl-4">
        {grouped.map((column) => (
            <div key={column.id} className="col">
                <div className="economato-board-column h-100" role="group" aria-label={column.label}>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                        <h6 className="text-muted mb-0">{column.label}</h6>
                        <span className={`badge bg-${column.color || 'secondary'} bg-opacity-25 text-dark`}>
                            {column.requests.length}
                        </span>
                    </div>
                    {column.requests.length === 0 ? (
                        <div className="text-muted small fst-italic">Nessuna richiesta</div>
                    ) : (
                        column.requests.map((request) => (
                            <div
                                key={request.id}
                                className={`economato-board-card ${activeId === request.id ? 'border-primary shadow-sm' : ''}`}
                                onClick={() => onSelect(request)}
                            >
                                <div className="d-flex justify-content-between align-items-center mb-2">
                                    <div className="fw-semibold">#{request.id}</div>
                                    <span className={`badge ${PRIORITY_BADGES[request.priority] || 'bg-secondary'}`}>
                                        {request.priority?.toUpperCase()}
                                    </span>
                                </div>
                                <div className="text-muted small mb-2">
                                    {request.resort_name}
                                </div>
                                <div className="d-flex justify-content-between small">
                                    <span>{request.items?.length || 0} articoli</span>
                                    <span className="fw-semibold">{formatCurrency(request.total_estimated_cost)}</span>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>
        ))}
    </div>
);

const TimelineView = ({ timeline }) => (
    <div className="timeline">
        {timeline.length === 0 ? (
            <p className="text-muted">Nessun evento registrato.</p>
        ) : (
            <ul className="list-unstyled">
                {timeline.map((event) => (
                    <li key={event.id} className="mb-4">
                        <div className="fw-semibold">{event.verb}</div>
                        <div className="text-muted small">{new Date(event.created_at).toLocaleString('it-IT')}</div>
                        {event.created_by_name && (
                            <div className="small">Operatore: {event.created_by_name}</div>
                        )}
                        {event.payload && Object.keys(event.payload).length > 0 && (
                            <pre className="bg-light rounded mt-2 p-2 small text-muted">
                                {JSON.stringify(event.payload, null, 2)}
                            </pre>
                        )}
                    </li>
                ))}
            </ul>
        )}
    </div>
);

const RequestComposer = ({
    open,
    onClose,
    onSubmit,
    isSubmitting,
    defaultValues,
    costCenters,
    items,
}) => {
    const [formState, setFormState] = useState(() => ({
        company: defaultValues.company,
        resort: defaultValues.resort,
        priority: 'medium',
        cost_center: '',
        needed_by: '',
        notes: '',
        items: [{ ...DEFAULT_ITEM }],
    }));
    const [error, setError] = useState(null);

    useEffect(() => {
        if (open) {
            setFormState((prev) => ({
                ...prev,
                company: defaultValues.company,
                resort: defaultValues.resort,
            }));
            setError(null);
        }
    }, [open, defaultValues.company, defaultValues.resort]);

    const updateLine = (index, payload) => {
        setFormState((prev) => ({
            ...prev,
            items: prev.items.map((line, lineIndex) => (lineIndex === index ? { ...line, ...payload } : line)),
        }));
    };

    const handleAddLine = () => {
        setFormState((prev) => ({
            ...prev,
            items: [...prev.items, { ...DEFAULT_ITEM }],
        }));
    };

    const handleRemoveLine = (index) => {
        setFormState((prev) => ({
            ...prev,
            items: prev.items.filter((_, lineIndex) => lineIndex !== index),
        }));
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        if (formState.items.length === 0) {
            setError('Inserire almeno una riga nella richiesta.');
            return;
        }
        setError(null);
        const payload = {
            company: formState.company,
            resort: formState.resort,
            cost_center: formState.cost_center || null,
            priority: formState.priority,
            needed_by: formState.needed_by || null,
            notes: formState.notes,
            items: formState.items
                .filter((line) => line.description || line.item)
                .map((line) => {
                    const itemName = items.find((it) => String(it.id) === String(line.item))?.name ?? '';
                    const hasItem = line.item !== undefined && line.item !== null && String(line.item).trim() !== '';
                    const hasSupplier =
                        line.supplier !== undefined && line.supplier !== null && String(line.supplier).trim() !== '';
                    return {
                        item: hasItem ? Number(line.item) : null,
                        description: line.description || itemName,
                        quantity: Number(line.quantity) || 0,
                        unit_of_measure: line.unit_of_measure,
                        unit_cost: line.unit_cost ? Number(line.unit_cost) : 0,
                        supplier: hasSupplier ? Number(line.supplier) : null,
                    };
                }),
        };
        if (payload.items.length === 0) {
            setError('Completa almeno una riga con descrizione o articolo.');
            return;
        }
        onSubmit(payload, () => {
            setFormState({
                company: defaultValues.company,
                resort: defaultValues.resort,
                priority: 'medium',
                cost_center: '',
                needed_by: '',
                notes: '',
                items: [{ ...DEFAULT_ITEM }],
            });
        });
    };

    if (!open) return null;

    return (
        <>
            <div className="economato-modal-backdrop" onClick={onClose} />
            <div className="economato-modal">
                <form onSubmit={handleSubmit} className="d-flex flex-column h-100">
                    <div className="economato-modal-header d-flex justify-content-between align-items-center">
                        <div>
                            <h5 className="mb-1">Nuova richiesta economato</h5>
                            <p className="mb-0 text-muted small">
                                Pianifica gli approvvigionamenti multi-canale con workflow approvativo.
                            </p>
                        </div>
                        <button type="button" className="btn-close" onClick={onClose} aria-label="Chiudi" />
                    </div>
                    <div className="economato-modal-body">
                        {error && <div className="alert alert-danger">{error}</div>}
                        <div className="row g-3">
                            <div className="col-md-6">
                                <label className="form-label">Priorità</label>
                                <select
                                    className="form-select"
                                    value={formState.priority}
                                    onChange={(event) => setFormState((prev) => ({ ...prev, priority: event.target.value }))}
                                >
                                    <option value="low">Bassa</option>
                                    <option value="medium">Media</option>
                                    <option value="high">Alta</option>
                                    <option value="critical">Critica</option>
                                </select>
                            </div>
                            <div className="col-md-6">
                                <label className="form-label">Data richiesta</label>
                                <input
                                    type="date"
                                    className="form-control"
                                    value={formState.needed_by || ''}
                                    onChange={(event) => setFormState((prev) => ({ ...prev, needed_by: event.target.value }))}
                                />
                            </div>
                            <div className="col-md-6">
                                <label className="form-label">Centro di costo</label>
                                <select
                                    className="form-select"
                                    value={formState.cost_center || ''}
                                    onChange={(event) => setFormState((prev) => ({ ...prev, cost_center: event.target.value }))}
                                >
                                    <option value="">Seleziona…</option>
                                    {costCenters.map((center) => (
                                        <option key={center.id} value={center.id}>
                                            {center.code} · {center.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="col-12">
                                <label className="form-label">Note operative</label>
                                <textarea
                                    className="form-control"
                                    rows={3}
                                    value={formState.notes}
                                    onChange={(event) => setFormState((prev) => ({ ...prev, notes: event.target.value }))}
                                    placeholder="Indicazioni per magazzino, consegna, budget…"
                                />
                            </div>
                        </div>
                        <hr className="my-4" />
                        <div className="d-flex justify-content-between align-items-center mb-3">
                            <h6 className="mb-0">Articoli richiesti</h6>
                            <button type="button" className="btn btn-outline-primary btn-sm" onClick={handleAddLine}>
                                <i className="fas fa-plus me-1" /> Aggiungi riga
                            </button>
                        </div>
                        {formState.items.map((line, index) => (
                            <div key={index} className="border rounded-3 p-3 mb-3">
                                <div className="row g-3 align-items-end">
                                    <div className="col-md-4">
                                        <label className="form-label">Articolo catalogo</label>
                                        <select
                                            className="form-select"
                                            value={line.item || ''}
                                            onChange={(event) => {
                                                const selectedItem = items.find(
                                                    (item) => String(item.id) === event.target.value
                                                );
                                                updateLine(index, {
                                                    item: event.target.value || '',
                                                    description: selectedItem?.name || line.description,
                                                    unit_of_measure: selectedItem?.unit || line.unit_of_measure,
                                                    supplier: selectedItem?.supplier || line.supplier,
                                                });
                                            }}
                                        >
                                            <option value="">Seleziona…</option>
                                            {items.map((item) => (
                                                <option key={item.id} value={item.id}>
                                                    {item.code} · {item.name}
                                                </option>
                                            ))}
                                        </select>
                                    </div>
                                    <div className="col-md-4">
                                        <label className="form-label">Descrizione</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            value={line.description}
                                            onChange={(event) => updateLine(index, { description: event.target.value })}
                                            placeholder="Es. Dispenser sapone camera deluxe"
                                        />
                                    </div>
                                    <div className="col-md-2">
                                        <label className="form-label">Quantità</label>
                                        <input
                                            type="number"
                                            min="0"
                                            step="1"
                                            className="form-control"
                                            value={line.quantity}
                                            onChange={(event) => updateLine(index, { quantity: event.target.value })}
                                        />
                                    </div>
                                    <div className="col-md-2">
                                        <label className="form-label">UM</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            value={line.unit_of_measure}
                                            onChange={(event) => updateLine(index, { unit_of_measure: event.target.value })}
                                            placeholder="pz, box, lt…"
                                        />
                                    </div>
                                    <div className="col-md-3">
                                        <label className="form-label">Prezzo unitario</label>
                                        <input
                                            type="number"
                                            min="0"
                                            step="0.01"
                                            className="form-control"
                                            value={line.unit_cost}
                                            onChange={(event) => updateLine(index, { unit_cost: event.target.value })}
                                        />
                                    </div>
                                    <div className="col-md-3">
                                        <label className="form-label">Fornitore</label>
                                        <input
                                            type="text"
                                            className="form-control"
                                            value={line.supplier}
                                            onChange={(event) => updateLine(index, { supplier: event.target.value })}
                                            placeholder="ID fornitore o descrizione"
                                        />
                                    </div>
                                    <div className="col-md-3 text-end">
                                        {formState.items.length > 1 && (
                                            <button
                                                type="button"
                                                className="btn btn-link text-danger"
                                                onClick={() => handleRemoveLine(index)}
                                            >
                                                Rimuovi
                                            </button>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                    <div className="economato-modal-footer d-flex justify-content-between align-items-center">
                        <span className="text-muted small">
                            Gli articoli verranno instradati automaticamente verso budget, magazzino e approvazione.
                        </span>
                        <div className="d-flex gap-2">
                            <button type="button" className="btn btn-outline-secondary" onClick={onClose}>
                                Annulla
                            </button>
                            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                                {isSubmitting ? (
                                    <span className="spinner-border spinner-border-sm" role="status" aria-hidden="true" />
                                ) : (
                                    <>
                                        <i className="fas fa-paper-plane me-2" /> Invia richiesta
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </>
    );
};

const RequestDrawer = ({ request, onClose, timeline, onStatusChange, canManage, isLoading }) => {
    if (!request) return null;
    const statusInfo = STATUS_METADATA[request.status] || {};

    return (
        <div className="economato-request-drawer" id="economato-request-drawer">
            <div className="economato-drawer-header d-flex justify-content-between align-items-start">
                <div>
                    <div className="text-muted small">Richiesta #{request.id}</div>
                    <h5 className="mb-1">{request.resort_name}</h5>
                    <span className={`badge ${PRIORITY_BADGES[request.priority] || 'bg-secondary'}`}>
                        Priorità {request.priority?.toUpperCase()}
                    </span>
                </div>
                <button type="button" className="btn-close" onClick={onClose} aria-label="Chiudi" />
            </div>
            <div className="economato-drawer-body">
                <div className="mb-4">
                    <div className="fw-semibold">Stato</div>
                    <span className={`badge bg-${statusInfo.color || 'secondary'}`}>{statusInfo.label}</span>
                </div>
                <div className="mb-4">
                    <h6>Articoli richiesti</h6>
                    <ul className="list-group list-group-flush">
                        {request.items?.map((item) => (
                            <li key={item.id} className="list-group-item px-0">
                                <div className="d-flex justify-content-between">
                                    <span>{item.description}</span>
                                    <span className="fw-semibold">
                                        {item.quantity} {item.unit_of_measure} · {formatCurrency(item.unit_cost)}
                                    </span>
                                </div>
                            </li>
                        ))}
                    </ul>
                </div>
                <div className="mb-4">
                    <div className="fw-semibold mb-1">Note</div>
                    <p className="text-muted small">{request.notes || 'Nessuna nota specificata.'}</p>
                </div>
                {canManage && (
                    <div className="mb-4">
                        <label className="form-label">Aggiorna stato</label>
                        <select
                            className="form-select"
                            value={request.status}
                            onChange={(event) => onStatusChange(request.id, event.target.value)}
                        >
                            {Object.entries(STATUS_METADATA).map(([status, metadata]) => (
                                <option key={status} value={status}>
                                    {metadata.label}
                                </option>
                            ))}
                        </select>
                    </div>
                )}
                <div>
                    <h6 className="mb-3">Timeline</h6>
                    {isLoading ? (
                        <div className="text-center py-3">
                            <div className="spinner-border" role="status" aria-hidden="true" />
                        </div>
                    ) : (
                        <TimelineView timeline={timeline} />
                    )}
                </div>
            </div>
        </div>
    );
};

const CatalogTable = ({ items }) => (
    <div className="card border-0 shadow-sm">
        <div className="card-body">
            <div className="table-responsive">
                <table className="table align-middle" aria-describedby="economato-catalogue-description">
                    <caption className="visually-hidden" id="economato-catalogue-description">
                        Catalogo articoli economato con categorie, resort e livelli di scorta.
                    </caption>
                    <thead>
                        <tr>
                            <th>Codice</th>
                            <th>Articolo</th>
                            <th>Categoria</th>
                            <th>Resort</th>
                            <th>Scorta Min.</th>
                            <th>Scorta Ideale</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items.length === 0 ? (
                            <tr>
                                <td colSpan="6" className="text-center text-muted py-4">
                                    Nessun articolo registrato nel perimetro attuale.
                                </td>
                            </tr>
                        ) : (
                            items.map((item) => (
                                <tr key={item.id}>
                                    <td className="fw-semibold">{item.code}</td>
                                    <td>{item.name}</td>
                                    <td>{item.category_display || '—'}</td>
                                    <td>{item.resort_name || 'Multi-resort'}</td>
                                    <td>{item.reorder_point}</td>
                                    <td>{item.optimal_stock}</td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
);

const EconomatoApp = ({ userRole, userRoleLabel, userName }) => {
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState(null);
    const [overview, setOverview] = useState(null);
    const [requests, setRequests] = useState([]);
    const [catalogItems, setCatalogItems] = useState([]);
    const [timeline, setTimeline] = useState([]);
    const [timelineLoading, setTimelineLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('overview');
    const [filters, setFilters] = useState({});
    const [showComposer, setShowComposer] = useState(false);
    const [composerLoading, setComposerLoading] = useState(false);
    const [composerCostCenters, setComposerCostCenters] = useState([]);
    const [composerItems, setComposerItems] = useState([]);
    const [selectedRequest, setSelectedRequest] = useState(null);

    const friendlyName = useMemo(() => {
        if (!userName) {
            return null;
        }
        const segments = userName.trim().split(' ');
        return segments.length ? segments[0] : userName;
    }, [userName]);

    const readableRole = useMemo(() => {
        if (userRoleLabel) {
            return userRoleLabel;
        }
        if (!userRole) {
            return null;
        }
        return userRole.replace(/_/g, ' ');
    }, [userRole, userRoleLabel]);

    const handleOpenGuide = useCallback(() => {
        window.dispatchEvent(
            new CustomEvent('open-in-app-guide', { detail: { guideKey: 'economato', force: true } })
        );
    }, []);

    const fetchData = useCallback(async (params = filters) => {
        setIsLoading(true);
        setError(null);
        try {
            const [overviewResponse, requestsResponse, itemsResponse] = await Promise.all([
                fetchEconomatoOverview(params),
                fetchEconomatoRequests({ ...params, page_size: 60 }),
                fetchEconomatoItems({ ...params, page_size: 120 }),
            ]);
            setOverview(overviewResponse.data);
            const requestPayload = requestsResponse.data;
            setRequests(Array.isArray(requestPayload.results) ? requestPayload.results : requestPayload);
            const catalogPayload = itemsResponse.data;
            setCatalogItems(Array.isArray(catalogPayload.results) ? catalogPayload.results : catalogPayload);
        } catch (err) {
            console.error('Errore nel caricamento economato', err);
            setError('Impossibile caricare i dati dell\'economato.');
        } finally {
            setIsLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        fetchData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleScopeChange = (payload) => {
        const nextFilters = { ...filters, ...payload };
        setFilters(nextFilters);
        fetchData(nextFilters);
    };

    const canManage = overview?.scope?.can_manage && !overview?.scope?.is_read_only;

    const groupedRequests = useMemo(() => {
        const columns = [
            { id: 'draft', label: 'Bozze', color: 'secondary', statuses: ['draft'] },
            { id: 'pending', label: 'In Approvazione', color: 'warning', statuses: ['pending'] },
            { id: 'approved', label: 'Approvate', color: 'success', statuses: ['approved'] },
            { id: 'fulfilled', label: 'Completate / Archivio', color: 'primary', statuses: ['fulfilled', 'cancelled', 'rejected'] },
        ];
        return columns.map((column) => ({
            ...column,
            requests: requests.filter((request) => column.statuses.includes(request.status)),
        }));
    }, [requests]);

    const handleOpenComposer = () => {
        setShowComposer(true);
        if (composerCostCenters.length === 0) {
            fetchCostCenters(filters)
                .then((response) => {
                    const payload = response.data;
                    setComposerCostCenters(Array.isArray(payload.results) ? payload.results : payload);
                })
                .catch((err) => console.error('Errore caricamento cost center', err));
        }
        if (composerItems.length === 0) {
            setComposerItems(catalogItems);
        }
    };

    const handleSubmitRequest = async (payload, resetForm) => {
        setComposerLoading(true);
        try {
            await createEconomatoRequest(payload);
            resetForm();
            setShowComposer(false);
            fetchData(filters);
        } catch (err) {
            console.error('Errore creazione richiesta economato', err);
        } finally {
            setComposerLoading(false);
        }
    };

    const handleSelectRequest = (request) => {
        setSelectedRequest(request);
        setTimelineLoading(true);
        fetchEconomatoTimeline(request.id, filters)
            .then((response) => {
                setTimeline(response.data);
            })
            .catch((err) => {
                console.error('Errore caricamento timeline economato', err);
                setTimeline([]);
            })
            .finally(() => setTimelineLoading(false));
    };

    const handleStatusChange = async (requestId, status) => {
        try {
            const response = await changeEconomatoStatus(requestId, { status });
            const updatedRequest = response.data;
            setRequests((prev) => prev.map((req) => (req.id === updatedRequest.id ? updatedRequest : req)));
            if (selectedRequest && selectedRequest.id === updatedRequest.id) {
                setSelectedRequest(updatedRequest);
            }
        } catch (err) {
            console.error('Errore cambio stato richiesta economato', err);
        }
    };

    if (isLoading) {
        return (
            <>
                <TopNav />
                <div className="d-flex justify-content-center align-items-center" style={{ minHeight: '60vh' }}>
                    <div className="spinner-border" role="status" aria-hidden="true" />
                </div>
            </>
        );
    }

    if (error) {
        return (
            <>
                <TopNav />
                <div className="alert alert-danger">
                    {error}
                    <div>
                        <button className="btn btn-outline-light btn-sm mt-2" onClick={() => fetchData(filters)}>
                            Riprova
                        </button>
                    </div>
                </div>
            </>
        );
    }

    const stats = overview?.stats || {};

    return (
        <>
            <TopNav />
            <div className="economato-app">
            <header className="economato-header" id="economato-hero">
                <div className="economato-header__meta mb-3">
                    <span className="badge bg-light text-primary-emphasis text-uppercase fw-semibold">Magazzino centralizzato</span>
                    {readableRole && (
                        <span className="badge bg-primary-subtle text-primary ms-2">{readableRole}</span>
                    )}
                </div>
                <div className="d-flex flex-column flex-lg-row align-items-lg-center gap-4">
                    <div className="flex-grow-1">
                        <h1 className="economato-header__title mb-2">
                            {friendlyName ? `Ciao ${friendlyName}, ecco la tua control room` : 'Economato intelligente'}
                        </h1>
                        <p className="economato-header__subtitle mb-3">
                            Orchestrazione end-to-end delle richieste di economato con controlli di budget, timeline condivise e visibilità multi-resort.
                        </p>
                        <div className="d-flex flex-wrap gap-2" id="economato-header-actions">
                            <button
                                type="button"
                                className="btn btn-outline-light"
                                onClick={handleOpenGuide}
                                aria-describedby="economato-guide-hint"
                            >
                                <i className="fas fa-circle-question me-2" aria-hidden="true" />
                                Guida rapida
                            </button>
                            {canManage && (
                                <button
                                    id="economato-new-request"
                                    type="button"
                                    className="btn btn-light"
                                    onClick={handleOpenComposer}
                                >
                                    <i className="fas fa-plus me-2" aria-hidden="true" /> Nuova richiesta
                                </button>
                            )}
                        </div>
                        <p id="economato-guide-hint" className="economato-header__hint text-white-50 mt-3 mb-0">
                            La guida illustra i punti chiave per gestire richieste, approvazioni e monitoraggio stock in base al tuo ruolo operativo.
                        </p>
                    </div>
                    <div className="economato-header__summary card shadow-sm border-0">
                        <div className="card-body text-start">
                            <h6 className="text-uppercase text-white-50 small mb-3">Prossime azioni consigliate</h6>
                            <ul className="list-unstyled mb-0 small text-white-75">
                                <li className="d-flex align-items-start gap-2">
                                    <i className="fas fa-check-circle mt-1 text-success" aria-hidden="true" />
                                    <span>Approva le richieste critiche direttamente dalla timeline della card.</span>
                                </li>
                                <li className="d-flex align-items-start gap-2 mt-2">
                                    <i className="fas fa-layer-group mt-1 text-info" aria-hidden="true" />
                                    <span>Controlla gli articoli sotto scorta per anticipare gli ordini ricorrenti.</span>
                                </li>
                                <li className="d-flex align-items-start gap-2 mt-2">
                                    <i className="fas fa-chart-line mt-1 text-warning" aria-hidden="true" />
                                    <span>Confronta budget impegnato e forecast mensile per restare allineato agli obiettivi.</span>
                                </li>
                            </ul>
                        </div>
                    </div>
                </div>
                <div className="economato-scope mt-4" id="economato-scope-selector">
                    <ScopeSelector overview={overview} filters={filters} onChange={handleScopeChange} />
                </div>
            </header>

            <ul className="nav nav-pills economato-tabs mt-4 mb-4 justify-content-start justify-content-md-center" role="tablist">
                {TABS.map((tab) => (
                    <li key={tab.id} className="nav-item">
                        <button
                            type="button"
                            className={`nav-link ${activeTab === tab.id ? 'active' : ''}`}
                            id={`economato-tab-${tab.id}`}
                            role="tab"
                            aria-selected={activeTab === tab.id}
                            aria-controls={`economato-panel-${tab.id}`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            {tab.label}
                        </button>
                    </li>
                ))}
            </ul>

            {activeTab === 'overview' && (
                <section className="row g-4" id="economato-panel-overview" role="tabpanel" aria-labelledby="economato-tab-overview">
                    <div className="col-xl-8">
                        <div className="row g-3 row-cols-1 row-cols-sm-2 row-cols-xl-3" id="economato-kpi-grid">
                            <div className="col">
                                <StatCard label="Articoli catalogo" value={stats.total_items ?? 0} accent="rgba(13, 110, 253, 0.2)" />
                            </div>
                            <div className="col">
                                <StatCard label="Sotto scorta" value={stats.low_stock_items ?? 0} accent="rgba(220, 53, 69, 0.2)" />
                            </div>
                            <div className="col">
                                <StatCard label="Richieste attive" value={stats.active_requests ?? 0} accent="rgba(25, 135, 84, 0.2)" />
                            </div>
                        </div>
                        <div className="row g-3 mt-1" id="economato-highlights">
                            <div className="col-lg-6">
                                <div className="card border-0 shadow-sm h-100">
                                    <div className="card-body">
                                        <h6 className="mb-3">Trend richieste e budget</h6>
                                        <p className="text-muted small">
                                            Bilancia i carichi controllando il volume per stato e il budget impegnato rispetto agli obiettivi mensili.
                                        </p>
                                        <div className="d-flex flex-wrap gap-2 mb-3">
                                            {Object.entries(overview.requests_by_status || {}).map(([status, value]) => (
                                                <span key={status} className={`badge bg-${STATUS_METADATA[status]?.color || 'secondary'}`}>
                                                    {STATUS_METADATA[status]?.label || status}: {value}
                                                </span>
                                            ))}
                                        </div>
                                        <div className="d-flex flex-column flex-sm-row flex-wrap align-items-sm-center justify-content-between gap-2">
                                            <div>
                                                <div className="text-muted small text-uppercase">Budget impegnato mese</div>
                                                <h2 className="fw-bold mb-0">{formatCurrency(stats.monthly_estimated_cost)}</h2>
                                            </div>
                                            <div className="text-muted small">
                                                <i className="fas fa-clock me-1 text-primary" aria-hidden="true" />Aggiorna i filtri per confronti storici.
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div className="col-lg-6">
                                <LowStockList items={overview.low_stock_items} />
                            </div>
                        </div>
                        <div className="card border-0 shadow-sm mt-3">
                            <div className="card-body">
                                <h6 className="mb-3">Suggerimenti operativi</h6>
                                <p className="text-muted small mb-3">
                                    Usa la sezione richieste per collaborare con fornitori e approvatori: ogni aggiornamento genera un evento in timeline così da mantenere tracciabilità completa.
                                </p>
                                <div className="d-flex flex-column flex-md-row gap-3">
                                    <div className="d-flex gap-2 align-items-start">
                                        <i className="fas fa-bolt text-warning mt-1" aria-hidden="true" />
                                        <span className="small">Duplica una richiesta ricorrente dal drawer per velocizzare ordini periodici.</span>
                                    </div>
                                    <div className="d-flex gap-2 align-items-start">
                                        <i className="fas fa-user-shield text-info mt-1" aria-hidden="true" />
                                        <span className="small">Coinvolgi il responsabile tramite nota: riceverà subito la notifica dedicata.</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div className="col-xl-4">
                        <div className="card border-0 shadow-sm h-100">
                            <div className="card-header bg-transparent border-0 d-flex justify-content-between align-items-center">
                                <h5 className="card-title mb-0">Ultime richieste</h5>
                                <span className="badge bg-primary-subtle text-primary">Aggiornato ora</span>
                            </div>
                            <div className="card-body">
                                <div className="list-group list-group-flush" aria-live="polite">
                                    {(overview.recent_requests || []).map((request) => (
                                        <div key={request.id} className="list-group-item px-0">
                                            <div className="d-flex justify-content-between align-items-start">
                                                <span className="fw-semibold">#{request.id}</span>
                                                <span className={`badge bg-${STATUS_METADATA[request.status]?.color || 'secondary'}`}>
                                                    {STATUS_METADATA[request.status]?.label}
                                                </span>
                                            </div>
                                            <div className="text-muted small">{request.resort_name}</div>
                                            <div className="small fw-semibold">{formatCurrency(request.total_estimated_cost)}</div>
                                        </div>
                                    ))}
                                    {(!overview.recent_requests || overview.recent_requests.length === 0) && (
                                        <div className="text-muted small">Nessuna richiesta recente: crea o filtra per visualizzare lo storico.</div>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            )}

            {activeTab === 'requests' && (
                <section
                    id="economato-panel-requests"
                    className="economato-requests"
                    role="tabpanel"
                    aria-labelledby="economato-tab-requests"
                >
                    <div className="d-flex flex-column flex-md-row justify-content-between align-items-md-end gap-3 mb-3">
                        <div>
                            <h2 className="h5 mb-1">Workflow richieste</h2>
                            <p className="text-muted small mb-0">
                                Trascina una card per cambiare stato o aprila per consultare timeline, note operative e storico approvazioni.
                            </p>
                        </div>
                        <button
                            type="button"
                            className="btn btn-outline-primary btn-sm"
                            onClick={handleOpenGuide}
                        >
                            <i className="fas fa-circle-question me-2" aria-hidden="true" />Rivedi tour
                        </button>
                    </div>
                    <div id="economato-requests-board">
                        <RequestsBoard grouped={groupedRequests} onSelect={handleSelectRequest} activeId={selectedRequest?.id} />
                    </div>
                </section>
            )}

            {activeTab === 'catalogue' && (
                <section
                    id="economato-panel-catalogue"
                    role="tabpanel"
                    aria-labelledby="economato-tab-catalogue"
                >
                    <div className="card border-0 shadow-sm mb-3">
                        <div className="card-body d-flex flex-column flex-lg-row justify-content-between gap-3">
                            <div>
                                <h2 className="h5 mb-1">Catalogo economato</h2>
                                <p className="text-muted small mb-0">
                                    Filtra dagli strumenti avanzati della tab panoramica per concentrare l'analisi su società o resort specifici.
                                </p>
                            </div>
                            <button type="button" className="btn btn-outline-secondary btn-sm" onClick={handleOpenGuide}>
                                <i className="fas fa-circle-question me-2" aria-hidden="true" />Apri guida
                            </button>
                        </div>
                    </div>
                    <CatalogTable items={catalogItems} />
                </section>
            )}

            <RequestDrawer
                request={selectedRequest}
                onClose={() => setSelectedRequest(null)}
                timeline={timeline}
                onStatusChange={handleStatusChange}
                canManage={canManage}
                isLoading={timelineLoading}
            />

            <RequestComposer
                open={showComposer}
                onClose={() => setShowComposer(false)}
                onSubmit={handleSubmitRequest}
                isSubmitting={composerLoading}
                defaultValues={{
                    company: filters.company || overview?.scope?.current_company_id || '',
                    resort: filters.resort || overview?.scope?.current_resort_id || '',
                }}
                costCenters={composerCostCenters}
                items={composerItems}
            />
            </div>
        </>
    );
};

export default EconomatoApp;
