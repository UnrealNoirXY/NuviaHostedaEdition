import React, { useEffect, useMemo, useState } from 'react';
import { useDraggable } from '@dnd-kit/core';
import { getAllergeni, getPiatti, clonePiatto } from '../api';

const DraggablePiatto = ({ piatto }) => {
    const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
        id: `piatto-${piatto.id}`,
        data: { type: 'piatto', piatto },
    });

    const style = transform ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
        zIndex: 1000,
    } : undefined;

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...listeners}
            {...attributes}
            className={`btn btn-sm ${isDragging ? 'btn-nuvia-primary shadow-glow' : 'btn-nuvia-ghost'} d-flex align-items-center gap-2`}
            title="Trascina nel menu"
        >
            <i className="bi bi-grip-vertical"></i>
            <span>Aggiungi</span>
        </div>
    );
};

const defaultFilters = {
    categorie: [],
    stagionalita: 'all',
    includeAllergeni: [],
    excludeAllergeni: [],
    includeInactive: false,
};

const PiattoLibrary = ({ excludeIds = [] }) => {
    const [piatti, setPiatti] = useState([]);
    const [allergeni, setAllergeni] = useState([]);
    const [filters, setFilters] = useState(() => {
        const saved = localStorage.getItem('piattoLibraryFilters');
        if (!saved) return defaultFilters;
        try {
            const parsed = JSON.parse(saved);
            const { search, ...rest } = parsed || {};
            return { ...defaultFilters, ...rest };
        } catch (error) {
            return defaultFilters;
        }
    });
    const [searchQuery, setSearchQuery] = useState(() => {
        const saved = localStorage.getItem('piattoLibraryFilters');
        if (!saved) return '';
        try {
            const parsed = JSON.parse(saved);
            return parsed?.search || '';
        } catch (error) {
            return '';
        }
    });
    const [savedFilters, setSavedFilters] = useState(() => {
        const saved = localStorage.getItem('piattoLibrarySavedFilters');
        return saved ? JSON.parse(saved) : [];
    });
    const [selectedPiatto, setSelectedPiatto] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [savingName, setSavingName] = useState('');

    const loadAllergeni = async () => {
        try {
            const res = await getAllergeni();
            setAllergeni(res.data || []);
        } catch (err) {
            console.error('Errore nel recupero degli allergeni', err);
        }
    };

    const fetchPiatti = async () => {
        setLoading(true);
        setError(null);
        try {
            const params = {
                detailed: true,
                categorie: filters.categorie.join(','),
                stagionalita: filters.stagionalita !== 'all' ? filters.stagionalita : undefined,
                allergeni: filters.includeAllergeni.map(a => a.id).join(','),
                exclude_allergeni: filters.excludeAllergeni.map(a => a.id).join(','),
                include_inactive: filters.includeInactive,
            };
            const res = await getPiatti(params);
            setPiatti(res.data || []);
        } catch (err) {
            setError('Errore nel caricamento della libreria piatti.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { loadAllergeni(); }, []);
    useEffect(() => { localStorage.setItem('piattoLibraryFilters', JSON.stringify({ ...filters, search: searchQuery })); }, [filters, searchQuery]);
    useEffect(() => { fetchPiatti(); }, [filters]);

    const filteredPiatti = useMemo(() => {
            const base = piatti.filter((p) => !excludeIds.includes(p.id));
            const normalizedQuery = searchQuery.trim().toLowerCase();
            if (!normalizedQuery) return base;
            return base.filter((piatto) => {
                const ingredienti = piatto.ingredienti_details?.map((ing) => ing.nome).join(' ') || '';
                const haystack = `${piatto.nome || ''} ${piatto.descrizione || ''} ${ingredienti}`.toLowerCase();
                return haystack.includes(normalizedQuery);
            });
        },
        [piatti, excludeIds, searchQuery]
    );

    const categoryOptions = useMemo(() => {
        const map = new Map();
        filteredPiatti.forEach((piatto) => {
            if (!piatto.categoria) return;
            if (!map.has(piatto.categoria)) map.set(piatto.categoria, piatto.categoria_display || piatto.categoria);
        });
        return Array.from(map.entries()).map(([value, label]) => ({ value, label })).sort((a, b) => a.label.localeCompare(b.label));
    }, [filteredPiatti]);

    const toggleCategory = (categoria) => {
        setFilters((prev) => {
            const exists = prev.categorie.includes(categoria);
            const nextCategories = exists ? prev.categorie.filter((c) => c !== categoria) : [...prev.categorie, categoria];
            return { ...prev, categorie: nextCategories };
        });
    };

    const handleClone = async (piatto) => {
        try {
            await clonePiatto(piatto.id, { nome: `${piatto.nome} (copia)` });
            fetchPiatti();
        } catch (err) {
            setError('Impossibile duplicare il piatto.');
        }
    };

    return (
        <div className="d-flex flex-column h-100 overflow-hidden">
            <div className="d-flex justify-content-between align-items-center mb-3">
                <span className="smallest fw-bold text-nuvia-accent uppercase ls-1">Catalogo Piatti</span>
                <div className="position-relative">
                    <i className="fas fa-search position-absolute top-50 start-0 translate-middle-y ms-2 tiny text-muted-soft"></i>
                    <input
                        type="search"
                        className="form-control noir-input py-1 ps-4 smallest"
                        placeholder="Filtra..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{ width: '130px' }}
                    />
                </div>
            </div>

            <div className="mb-3 d-flex flex-wrap gap-1">
                {categoryOptions.slice(0, 6).map((cat) => (
                    <button
                        key={cat.value}
                        className={`btn smallest py-1 px-2 rounded-pill border-white border-opacity-10 ${filters.categorie.includes(cat.value) ? 'btn-nuvia-primary' : 'btn-nuvia-ghost opacity-75'}`}
                        onClick={() => toggleCategory(cat.value)}
                    >
                        {cat.label}
                    </button>
                ))}
            </div>

            <div className="flex-grow-1 overflow-auto studio-piatti-list pe-1">
                {loading ? (
                    <div className="text-center py-5 animate-pulse text-muted-soft smaller">Sincronizzazione...</div>
                ) : filteredPiatti.length > 0 ? (
                    filteredPiatti.map((piatto) => (
                        <div
                            key={piatto.id}
                            className={`piatto-lib-item p-3 mb-2 rounded-3 border transition-all ${selectedPiatto?.id === piatto.id ? 'bg-nuvia-primary bg-opacity-10 border-nuvia-primary' : 'bg-white bg-opacity-5 border-white border-opacity-5 hover-bg-white-5'}`}
                            onClick={() => setSelectedPiatto(piatto)}
                        >
                            <div className="d-flex justify-content-between align-items-center">
                                <div className="flex-grow-1 overflow-hidden me-2">
                                    <div className="fw-bold text-truncate text-white smaller uppercase ls-tight mb-1">{piatto.nome}</div>
                                    <div className="smallest text-muted-soft text-truncate uppercase ls-1">
                                        {piatto.categoria_display}
                                    </div>
                                </div>
                                <DraggablePiatto piatto={piatto} />
                            </div>
                        </div>
                    ))
                ) : (
                    <div className="text-center py-5 text-muted-soft smallest border border-dashed border-white border-opacity-10 rounded-3">Nessun piatto trovato.</div>
                )}
            </div>

            {selectedPiatto && (
                <div className="piatto-preview-pane p-3 mt-3 rounded-4 border border-nuvia-primary border-opacity-20 bg-nuvia-primary bg-opacity-5 animate-in">
                    <div className="d-flex justify-content-between align-items-start mb-2">
                        <h6 className="mb-0 fw-bold text-white smallest uppercase ls-1">{selectedPiatto.nome}</h6>
                        <button className="btn-close btn-close-white smallest" onClick={() => setSelectedPiatto(null)}></button>
                    </div>
                    <p className="smallest text-muted-soft mb-3 line-clamp-2">{selectedPiatto.descrizione || 'Nessuna descrizione.'}</p>
                    <div className="d-flex gap-2">
                        <button className="btn btn-nuvia-ghost btn-sm smallest py-2 flex-grow-1 fw-bold" onClick={() => handleClone(selectedPiatto)}>
                            <i className="fas fa-copy me-1"></i> DUPLICA
                        </button>
                         <button className="btn btn-nuvia-primary btn-sm smallest py-2 flex-grow-1 fw-bold" onClick={() => setSelectedPiatto(null)}>
                            OK
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PiattoLibrary;
