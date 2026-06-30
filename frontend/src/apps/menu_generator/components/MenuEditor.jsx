import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
    getMenu,
    updateMenu,
    getLayouts,
    addPiattoToMenu,
    removePiattoFromMenu,
    reorderPiattiInMenu,
    getMenuDocumentJobStatus,
    startMenuDocumentJob,
    getMenuInsights,
} from '../api';
import {
    DndContext,
    closestCenter,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
    DragOverlay,
    defaultDropAnimationSideEffects,
} from '@dnd-kit/core';
import { arrayMove, sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import PiattoLibrary from './PiattoLibrary';
import MenuDropzone from './MenuDropzone';
import MenuVersionHistory from './MenuVersionHistory';
import MenuAuditLog from './MenuAuditLog';
import MenuInsights from './MenuInsights';
import MenuPreview from './MenuPreview';
import { getPiatti } from '../api';
import { toast, ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import { t } from '../i18n';

const parseApiError = (error, fallback) => {
    if (error?.response?.data?.detail) return String(error.response.data.detail);
    if (error?.response?.data?.error) return String(error.response.data.error);
    if (Array.isArray(error?.response?.data?.non_field_errors)) return error.response.data.non_field_errors.join(' · ');
    if (typeof error?.message === 'string' && error.message.trim()) return error.message;
    return fallback;
};

const MenuEditor = () => {
    const { menuId } = useParams();
    const [menu, setMenu] = useState(null);
    const [layouts, setLayouts] = useState([]);
    const [selectedLayout, setSelectedLayout] = useState('');
    const [menuSections, setMenuSections] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshIndex, setRefreshIndex] = useState(0);
    const [docJob, setDocJob] = useState(null);
    const [jobPoller, setJobPoller] = useState(null);
    const [isGenerating, setIsGenerating] = useState(null);
    const [insights, setInsights] = useState(null);
    const [insightsLoading, setInsightsLoading] = useState(false);
    const [activeId, setActiveId] = useState(null);
    const [activePiatto, setActivePiatto] = useState(null);
    const [showTypographyControls, setShowTypographyControls] = useState(false);
    const [previewTypography, setPreviewTypography] = useState({
        dishNameSize: 12,
        dishDescriptionSize: 10.5,
        sectionTitleSize: 16,
        secondaryTextColor: '#4b5563',
    });

    const [saveState, setSaveState] = useState('idle'); // idle|dirty|saving|saved|error
    const [lastSavedAt, setLastSavedAt] = useState(null);

    const hasHydratedRef = useRef(false);
    const suppressDirtyRef = useRef(false);
    const autosaveTimerRef = useRef(null);

    const userPermissions = menu?.user_permissions || {};
    const canEditMenu = userPermissions.can_edit;
    const canPublishMenu = userPermissions.can_publish;
    const selectedLayoutData = layouts.find((layout) => layout.id === selectedLayout);

    const createSectionId = (category) => `menu-section-${category}`;

    const buildSectionsFromPiatti = useCallback((piatti = []) => {
        const grouped = new Map();
        const order = [];
        piatti.forEach((piatto) => {
            const category = piatto.categoria_display || 'Altro';
            if (!grouped.has(category)) {
                grouped.set(category, []);
                order.push(category);
            }
            grouped.get(category).push(piatto);
        });
        return order.map((category) => ({
            id: createSectionId(category),
            title: category,
            piatti: grouped.get(category),
        }));
    }, []);

    const flattenSections = (sections) => sections.flatMap((section) => section.piatti);

    const fetchInsights = useCallback(async (referenceDate) => {
        setInsightsLoading(true);
        try {
            const params = referenceDate ? { reference_date: referenceDate } : {};
            const { data } = await getMenuInsights(menuId, params);
            setInsights(data);
        } catch (err) {
            console.error('Insights error', err);
        } finally {
            setInsightsLoading(false);
        }
    }, [menuId]);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                setError(null);
                const [menuRes, layoutsRes] = await Promise.all([
                    getMenu(menuId),
                    getLayouts(),
                ]);

                const menuData = menuRes.data;
                setMenu(menuData);
                const savedTypography = menuData?.metadata?.preview_typography || {};
                setPreviewTypography((prev) => ({ ...prev, ...savedTypography }));
                setLayouts(layoutsRes.data);
                suppressDirtyRef.current = true;
                setSelectedLayout(menuData.layout ? Number(menuData.layout) : '');

                const menuPiatti = menuData.piatti_details || [];
                setMenuSections(buildSectionsFromPiatti(menuPiatti));
                setSaveState('idle');
                await fetchInsights(menuData.data_evento);
                hasHydratedRef.current = true;
                suppressDirtyRef.current = false;
            } catch (err) {
                setError(parseApiError(err, 'Impossibile caricare i dati del menu.'));
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [menuId, refreshIndex, buildSectionsFromPiatti, fetchInsights]);

    useEffect(() => () => {
        if (jobPoller) clearInterval(jobPoller);
        if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
    }, [jobPoller]);

    useEffect(() => {
        if (!hasHydratedRef.current || suppressDirtyRef.current || !canEditMenu) return;
        setSaveState((prev) => (prev === 'saving' ? prev : 'dirty'));
    }, [menuSections, selectedLayout, previewTypography, canEditMenu]);

    const persistMenuChanges = useCallback(async ({ notify = false } = {}) => {
        if (!canEditMenu || !menu) return;
        setSaveState('saving');
        try {
            const piattoIds = flattenSections(menuSections).map((p) => p.id);
            await updateMenu(menuId, {
                ...menu,
                piatti: piattoIds,
                layout: selectedLayout || null,
                metadata: {
                    ...(menu.metadata || {}),
                    preview_typography: previewTypography,
                },
            });
            setSaveState('saved');
            setLastSavedAt(new Date());
            if (notify) toast.success('Menu salvato');
        } catch (err) {
            setSaveState('error');
            toast.error(parseApiError(err, 'Salvataggio fallito'));
        }
    }, [canEditMenu, menu, menuId, menuSections, selectedLayout, previewTypography]);

    useEffect(() => {
        if (saveState !== 'dirty') return;
        if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
        autosaveTimerRef.current = setTimeout(() => {
            persistMenuChanges();
        }, 1300);
        return () => {
            if (autosaveTimerRef.current) clearTimeout(autosaveTimerRef.current);
        };
    }, [saveState, persistMenuChanges]);

    const sensors = useSensors(
        useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
    );

    const handleRemovePiatto = async (piattoIdToRemove) => {
        if (!canEditMenu) {
            toast.error('Non hai i permessi per modificare il menu.');
            return;
        }

        const previousSections = [...menuSections];
        const piattoToRemove = flattenSections(menuSections).find((p) => p.id === piattoIdToRemove);

        setMenuSections((prev) => prev
            .map((section) => ({
                ...section,
                piatti: section.piatti.filter((piatto) => piatto.id !== piattoIdToRemove),
            }))
            .filter((section) => section.piatti.length > 0));

        try {
            await removePiattoFromMenu(menuId, piattoIdToRemove);
            fetchInsights(menu?.data_evento);
            toast.info(`${piattoToRemove?.nome || 'Piatto'} rimosso`);
        } catch (err) {
            toast.error(parseApiError(err, 'Errore durante la rimozione'));
            setMenuSections(previousSections);
        }
    };

    const handleDragStart = (event) => {
        const { active } = event;
        setActiveId(active.id);
        if (active.data.current?.piatto) {
            setActivePiatto(active.data.current.piatto);
        }
    };

    const handleDragEnd = async (event) => {
        const { active, over } = event;
        setActiveId(null);
        setActivePiatto(null);
        if (!over) return;

        if (!canEditMenu) {
            toast.error('Permesso negato');
            return;
        }

        const activeType = active.data.current?.type;
        const overType = over.data.current?.type;

        // Case 1: Library -> Menu
        if (activeType === 'piatto' && !active.id.toString().startsWith('menu-piatto-')) {
            const piattoAggiunto = active.data.current.piatto;
            if (flattenSections(menuSections).find((p) => p.id === piattoAggiunto.id)) {
                toast.warn('Piatto già presente');
                return;
            }

            const previousSections = [...menuSections];
            setMenuSections((prev) => {
                const category = piattoAggiunto.categoria_display || 'Altro';
                const sectionIndex = prev.findIndex((section) => section.title === category);
                if (sectionIndex === -1) {
                    return [...prev, { id: createSectionId(category), title: category, piatti: [piattoAggiunto] }];
                }
                const next = [...prev];
                next[sectionIndex] = { ...next[sectionIndex], piatti: [...next[sectionIndex].piatti, piattoAggiunto] };
                return next;
            });

            try {
                await addPiattoToMenu(menuId, piattoAggiunto.id);
                fetchInsights(menu?.data_evento);
                toast.success('Piatto aggiunto');
            } catch (err) {
                toast.error(parseApiError(err, 'Errore durante l\'aggiunta'));
                setMenuSections(previousSections);
            }
            return;
        }

        // Case 2: Section Reordering
        if (activeType === 'section' && overType === 'section') {
            const oldIndex = menuSections.findIndex((section) => section.id === active.id);
            const newIndex = menuSections.findIndex((section) => section.id === over.id);
            if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
                const previousSections = [...menuSections];
                const nextSections = arrayMove(menuSections, oldIndex, newIndex);
                setMenuSections(nextSections);

                try {
                    await reorderPiattiInMenu(menuId, flattenSections(nextSections).map((p) => p.id));
                } catch (err) {
                    toast.error(parseApiError(err, 'Errore riordino sezioni'));
                    setMenuSections(previousSections);
                }
            }
            return;
        }

        // Case 3: Internal / Cross-section Dish Reordering
        if (active.id.toString().startsWith('menu-piatto-') && over.id.toString().startsWith('menu-piatto-')) {
            const activeIdNum = Number(active.id.toString().replace('menu-piatto-', ''));
            const overIdNum = Number(over.id.toString().replace('menu-piatto-', ''));

            const activeSIdx = menuSections.findIndex((s) => s.piatti.some((p) => p.id === activeIdNum));
            const overSIdx = menuSections.findIndex((s) => s.piatti.some((p) => p.id === overIdNum));
            if (activeSIdx === -1 || overSIdx === -1) return;

            const previousSections = [...menuSections];
            const nextSections = [...menuSections];

            const activeSection = { ...nextSections[activeSIdx], piatti: [...nextSections[activeSIdx].piatti] };
            const overSection = activeSIdx === overSIdx
                ? activeSection
                : { ...nextSections[overSIdx], piatti: [...nextSections[overSIdx].piatti] };

            const oldIdx = activeSection.piatti.findIndex((p) => p.id === activeIdNum);
            const newIdx = overSection.piatti.findIndex((p) => p.id === overIdNum);
            if (oldIdx === -1 || newIdx === -1) return;

            if (activeSIdx === overSIdx) {
                if (oldIdx === newIdx) return;
                activeSection.piatti = arrayMove(activeSection.piatti, oldIdx, newIdx);
                nextSections[activeSIdx] = activeSection;
            } else {
                const [movingDish] = activeSection.piatti.splice(oldIdx, 1);
                overSection.piatti.splice(newIdx, 0, movingDish);
                nextSections[activeSIdx] = activeSection;
                nextSections[overSIdx] = overSection;
            }

            const cleanedSections = nextSections.filter((section) => section.piatti.length > 0);
            setMenuSections(cleanedSections);

            try {
                await reorderPiattiInMenu(menuId, flattenSections(cleanedSections).map((p) => p.id));
            } catch (err) {
                toast.error(parseApiError(err, 'Errore riordino piatti'));
                setMenuSections(previousSections);
            }
        }
    };

    const handleSaveChanges = async () => {
        await persistMenuChanges({ notify: true });
    };

    const handleAutofill = async () => {
        if (!canEditMenu) return;
        setLoading(true);
        try {
            // Logica semplice di autofill: prendi piatti stagionali consigliati non ancora nel menu
            const season = insights?.stagionalita?.stagione_corrente || 'annuale';
            const { data: allPiatti } = await getPiatti({ detailed: true, stagionalita: season });

            const currentIds = new Set(flattenSections(menuSections).map(p => p.id));
            const availablePiatti = allPiatti.filter(p => !currentIds.has(p.id));

            if (availablePiatti.length === 0) {
                toast.info("Nessun nuovo piatto suggerito per questa stagione.");
                return;
            }

            // Aggiungi un piatto per categoria mancante
            const missingCats = insights?.categorie?.mancanti || [];
            const dishesToAdd = [];

            missingCats.forEach(cat => {
                const dish = availablePiatti.find(p => p.categoria === cat);
                if (dish) dishesToAdd.push(dish);
            });

            if (dishesToAdd.length === 0) {
                toast.info("Nessun piatto trovato per le categorie mancanti.");
                return;
            }

            const previousSections = [...menuSections];
            setMenuSections(prev => {
                let next = [...prev];
                dishesToAdd.forEach(dish => {
                    const category = dish.categoria_display || 'Altro';
                    const sectionIndex = next.findIndex(s => s.title === category);
                    if (sectionIndex === -1) {
                        next.push({ id: createSectionId(category), title: category, piatti: [dish] });
                    } else {
                        next[sectionIndex] = { ...next[sectionIndex], piatti: [...next[sectionIndex].piatti, dish] };
                    }
                });
                return next;
            });

            // Persistenza nel backend per ogni piatto aggiunto
            await Promise.all(dishesToAdd.map(dish => addPiattoToMenu(menuId, dish.id)));
            fetchInsights(menu?.data_evento);
            toast.success(`Autofill completato: aggiunti ${dishesToAdd.length} piatti.`);
        } catch (err) {
            toast.error("Errore durante l'autofill");
        } finally {
            setLoading(false);
        }
    };

    const startPollingJob = (jobId) => {
        if (jobPoller) clearInterval(jobPoller);
        const poller = setInterval(async () => {
            try {
                const { data } = await getMenuDocumentJobStatus(jobId);
                setDocJob(data);
                if (data.status === 'success') {
                    clearInterval(poller);
                    toast.success(t('downloadReady'));
                    if (data.download_url) window.open(data.download_url, '_blank');
                } else if (data.status === 'failed') {
                    clearInterval(poller);
                    toast.error(t('downloadError'));
                }
            } catch (err) {
                clearInterval(poller);
            }
        }, 2000);
        setJobPoller(poller);
    };

    const handleGenerateDocument = async (format) => {
        if (!canPublishMenu) return;
        setIsGenerating(format);
        try {
            const { data } = await startMenuDocumentJob(menuId, { format, type: 'menu', include_cavalieri: false });
            setDocJob(data);
            toast.info(t('documentStarting'));
            startPollingJob(data.id);
        } catch (err) {
            toast.error(parseApiError(err, 'Errore nell\'avvio')); 
        } finally {
            setIsGenerating(null);
        }
    };

    const handleGenerateCavaliere = async (format) => {
        if (!canPublishMenu) return;
        setIsGenerating('cavaliere');
        try {
            const { data } = await startMenuDocumentJob(menuId, { format, type: 'cavaliere', include_cavalieri: true });
            setDocJob(data);
            toast.info("Generazione cavalieri avviata...");
            startPollingJob(data.id);
        } catch (err) {
            toast.error("Errore nell'avvio dei cavalieri");
        } finally {
            setIsGenerating(null);
        }
    };

    if (loading) return <div className="text-center p-5 animate-pulse text-muted-soft">Inizializzazione Studio...</div>;
    if (error) return <div className="alert alert-danger m-4">{error}</div>;

    return (
        <DndContext
            sensors={sensors}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
            collisionDetection={closestCenter}
        >
            <ToastContainer position="top-right" autoClose={3000} theme="dark" />

            <div className="menu-studio-shell p-0 vh-100 d-flex flex-column overflow-hidden">
                {/* Studio Toolbar */}
                <div className="studio-toolbar px-4">
                    <div className="d-flex align-items-center gap-3">
                        <Link to="/menu" className="btn btn-nuvia-ghost p-2 rounded-circle" style={{ width: '40px', height: '40px', display: 'grid', placeItems: 'center' }}>
                            <i className="fas fa-arrow-left"></i>
                        </Link>
                        <div>
                            <span className="tiny-badge bg-nuvia-primary mb-1">Menu Studio v2.0</span>
                            <h1 className="h5 mb-0 fw-bold text-white">{menu.nome}</h1>
                        </div>
                        <div className="ms-2">
                             <span className={`save-state-pill save-state-pill--${saveState}`}>{
                                saveState === 'saving' ? 'Salvataggio...' :
                                saveState === 'saved' ? 'Salvato' :
                                saveState === 'dirty' ? 'Modifiche' :
                                'Pronto'
                            }</span>
                        </div>
                    </div>

                    <div className="ms-auto d-flex align-items-center gap-2">
                        <button
                            type="button"
                            className="btn btn-warning fw-bold smallest py-2 px-3"
                            onClick={() => setShowTypographyControls(true)}
                            title="Apri i controlli font e colore per buffet/menu in full screen"
                        >
                            <i className="fas fa-font me-2"></i>
                            APRI EDITOR TESTI BUFFET (FULL SCREEN)
                        </button>
                        <div className="dropdown">
                            <button className="btn btn-nuvia-ghost dropdown-toggle smallest py-2 px-3" type="button" data-bs-toggle="dropdown" disabled={isGenerating !== null || !canPublishMenu}>
                                <i className="fas fa-file-export me-2"></i> ESPORTA
                            </button>
                            <ul className="dropdown-menu dropdown-menu-dark shadow-lg border-0 smallest">
                                <li><button className="dropdown-item py-2" onClick={() => handleGenerateDocument('pdf')}>Scarica PDF Stampa</button></li>
                                <li><button className="dropdown-item py-2" onClick={() => handleGenerateDocument('docx')}>Scarica Word Editabile</button></li>
                                <li className="dropdown-divider opacity-10"></li>
                                <li><button className="dropdown-item py-2" onClick={() => handleGenerateCavaliere('pdf')}>Cavalieri Tavolo (PDF)</button></li>
                            </ul>
                        </div>

                        <select className="form-select noir-select py-2 smallest" value={selectedLayout} onChange={(e) => setSelectedLayout(e.target.value ? Number(e.target.value) : '')} style={{ width: '160px' }}>
                            <option value="">Stile Automatico</option>
                            {layouts.map((l) => <option key={l.id} value={l.id}>{l.nome_layout}</option>)}
                        </select>

                        <button className="btn btn-nuvia-ghost p-2 px-3 smallest" onClick={handleAutofill} disabled={loading || !canEditMenu} title="Autocompila">
                            <i className="fas fa-magic me-2"></i> AUTOFILL
                        </button>

                        <button className="btn btn-nuvia-primary px-4 fw-bold" onClick={handleSaveChanges} disabled={saveState === 'saving' || !canEditMenu}>
                            {saveState === 'saving' ? 'SALVATAGGIO...' : 'SALVA ORA'}
                        </button>
                    </div>
                </div>

                <div className="studio-container flex-grow-1">
                    {/* Left Panel: Library & Audit */}
                    <div className="studio-sidebar border-end" style={{ width: '340px' }}>
                        <div className="sidebar-tabs">
                            <div className="sidebar-tab active">Libreria Piatti</div>
                        </div>
                        <div className="sidebar-content p-3 d-flex flex-column gap-3">
                            <PiattoLibrary excludeIds={flattenSections(menuSections).map((p) => p.id)} />
                            <MenuAuditLog menuId={menuId} />
                        </div>
                    </div>

                    {/* Center Workspace: Dropzone */}
                    <div className="studio-content bg-black bg-opacity-50">
                        <div className="p-4 h-100 overflow-auto">
                            <div className="mx-auto" style={{ maxWidth: '900px' }}>
                                <MenuDropzone sections={menuSections} onRemove={handleRemovePiatto} columns={selectedLayoutData?.struttura_blocchi?.columns || 1} />
                            </div>
                        </div>
                    </div>

                    {/* Right Panel: Insights & Preview */}
                    <div className="studio-sidebar border-start" style={{ width: '380px' }}>
                        <div className="sidebar-tabs">
                            <div className="sidebar-tab active">Revisione & Anteprima</div>
                        </div>
                        <div className="sidebar-content p-3 d-flex flex-column gap-3">
                            <MenuInsights insights={insights} loading={insightsLoading} onRefresh={() => fetchInsights(menu?.data_evento)} />

                            <div className="glass-card menu-preview-card overflow-hidden" style={{ height: '350px', flexShrink: 0 }}>
                                <div className="card-header border-bottom border-white border-opacity-10 py-2 d-flex justify-content-between align-items-center">
                                    <span className="smallest fw-bold uppercase">Anteprima Live</span>
                                    <div className="d-flex align-items-center gap-2">
                                        <button type="button" className="btn btn-sm btn-nuvia-ghost py-0 px-2 smallest" onClick={() => setShowTypographyControls((prev) => !prev)}>
                                            <i className="fas fa-font me-1"></i>{showTypographyControls ? 'Chiudi editor buffet' : 'Apri editor buffet'}
                                        </button>
                                        <Link to={selectedLayout ? `/layout-editor/${selectedLayout}` : '/layouts'} className="smallest text-nuvia-accent text-decoration-none">Apri Designer &rarr;</Link>
                                    </div>
                                </div>
                                {showTypographyControls && (
                                    <div className="px-3 py-2 border-bottom border-white border-opacity-10 bg-black bg-opacity-25">
                                        <div className="d-grid gap-2">
                                            <div className="smallest text-warning fw-bold">EDITOR TESTI BUFFET / MENU</div>
                                            <label className="smallest text-white opacity-75">Titolo sezione ({previewTypography.sectionTitleSize}pt)</label>
                                            <input type="range" min="12" max="26" step="0.5" value={previewTypography.sectionTitleSize} onChange={(e) => setPreviewTypography((prev) => ({ ...prev, sectionTitleSize: parseFloat(e.target.value) }))} />
                                            <label className="smallest text-white opacity-75">Nome piatto ({previewTypography.dishNameSize}pt)</label>
                                            <input type="range" min="10" max="20" step="0.5" value={previewTypography.dishNameSize} onChange={(e) => setPreviewTypography((prev) => ({ ...prev, dishNameSize: parseFloat(e.target.value) }))} />
                                            <label className="smallest text-white opacity-75">Descrizione ({previewTypography.dishDescriptionSize}pt)</label>
                                            <input type="range" min="8" max="16" step="0.5" value={previewTypography.dishDescriptionSize} onChange={(e) => setPreviewTypography((prev) => ({ ...prev, dishDescriptionSize: parseFloat(e.target.value) }))} />
                                            <label className="smallest text-white opacity-75">Colore testo secondario</label>
                                            <input type="color" value={previewTypography.secondaryTextColor} onChange={(e) => setPreviewTypography((prev) => ({ ...prev, secondaryTextColor: e.target.value }))} style={{ width: '42px', height: '24px' }} />
                                        </div>
                                    </div>
                                )}
                                <div className="card-body p-0">
                                    <MenuPreview
                                        layoutProps={{
                                            font_principale: selectedLayoutData?.font_principale,
                                            colore_font: selectedLayoutData?.colore_font,
                                            struttura_blocchi: selectedLayoutData?.struttura_blocchi,
                                            metadata: selectedLayoutData?.metadata,
                                        }}
                                        logoUrl={selectedLayoutData?.logo}
                                        backgroundImageUrl={selectedLayoutData?.background_image}
                                        piatti={flattenSections(menuSections)}
                                        menuName={menu.nome}
                                        sections={menuSections}
                                        menuData={menu}
                                        typography={previewTypography}
                                    />
                                </div>
                            </div>

                            <MenuVersionHistory menuId={menuId} onRestored={() => setRefreshIndex((p) => p + 1)} />
                        </div>
                    </div>
                </div>
            </div>
            {showTypographyControls && (
                <div
                    className="position-fixed top-0 start-0 w-100 h-100 d-flex align-items-center justify-content-center"
                    style={{ background: 'rgba(2, 6, 23, 0.92)', zIndex: 2000 }}
                >
                    <div className="glass-card p-4 w-100 h-100 overflow-auto" style={{ maxWidth: '100vw', borderRadius: 0 }}>
                        <div className="d-flex justify-content-between align-items-center mb-4">
                            <h2 className="h5 text-warning mb-0 fw-bold">EDITOR TESTI BUFFET / MENU · FULL SCREEN</h2>
                            <button type="button" className="btn btn-danger fw-bold" onClick={() => setShowTypographyControls(false)}>
                                CHIUDI
                            </button>
                        </div>
                        <div className="row g-4">
                            <div className="col-lg-4">
                                <div className="d-grid gap-3">
                                    <label className="small text-white">Titolo sezione ({previewTypography.sectionTitleSize}pt)</label>
                                    <input type="range" min="12" max="26" step="0.5" value={previewTypography.sectionTitleSize} onChange={(e) => setPreviewTypography((prev) => ({ ...prev, sectionTitleSize: parseFloat(e.target.value) }))} />
                                    <label className="small text-white">Nome piatto ({previewTypography.dishNameSize}pt)</label>
                                    <input type="range" min="10" max="20" step="0.5" value={previewTypography.dishNameSize} onChange={(e) => setPreviewTypography((prev) => ({ ...prev, dishNameSize: parseFloat(e.target.value) }))} />
                                    <label className="small text-white">Descrizione ({previewTypography.dishDescriptionSize}pt)</label>
                                    <input type="range" min="8" max="16" step="0.5" value={previewTypography.dishDescriptionSize} onChange={(e) => setPreviewTypography((prev) => ({ ...prev, dishDescriptionSize: parseFloat(e.target.value) }))} />
                                    <label className="small text-white">Colore testo secondario</label>
                                    <input type="color" value={previewTypography.secondaryTextColor} onChange={(e) => setPreviewTypography((prev) => ({ ...prev, secondaryTextColor: e.target.value }))} style={{ width: '60px', height: '36px' }} />
                                </div>
                            </div>
                            <div className="col-lg-8">
                                <div className="bg-black bg-opacity-50 p-3 rounded-3">
                                    <MenuPreview
                                        layoutProps={{
                                            font_principale: selectedLayoutData?.font_principale,
                                            colore_font: selectedLayoutData?.colore_font,
                                            struttura_blocchi: selectedLayoutData?.struttura_blocchi,
                                            metadata: selectedLayoutData?.metadata,
                                        }}
                                        logoUrl={selectedLayoutData?.logo}
                                        backgroundImageUrl={selectedLayoutData?.background_image}
                                        piatti={flattenSections(menuSections)}
                                        menuName={menu.nome}
                                        sections={menuSections}
                                        menuData={menu}
                                        typography={previewTypography}
                                    />
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <DragOverlay dropAnimation={{
                sideEffects: defaultDropAnimationSideEffects({
                    styles: { active: { opacity: '0.5' } },
                }),
            }}>
                {activePiatto ? (
                    <div className="list-group-item bg-nuvia-primary border-nuvia shadow-glow p-2 rounded-3 text-white" style={{ width: '250px' }}>
                        <div className="fw-bold smaller">{activePiatto.nome}</div>
                        <div className="smallest opacity-75">{activePiatto.categoria_display}</div>
                    </div>
                ) : null}
            </DragOverlay>
        </DndContext>
    );
};

export default MenuEditor;
