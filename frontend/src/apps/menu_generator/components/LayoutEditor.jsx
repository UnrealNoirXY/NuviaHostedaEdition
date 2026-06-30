import React, { useMemo, useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getLayout, updateLayout } from '../api';
import { toast, ToastContainer } from 'react-toastify';
import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useDroppable, useSensor, useSensors, DragOverlay } from '@dnd-kit/core';
import { arrayMove, sortableKeyboardCoordinates, SortableContext, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { usePermissions } from '../permissions';
import LayoutPreview from './LayoutPreview';

const BLOCK_DEFINITIONS = {
    logo: { label: 'Logo' },
    info: { label: 'Info evento' },
    sections: { label: 'Sezioni menu' },
    legend: { label: 'Legenda allergeni' },
};

const DEFAULT_ORDER = ['logo', 'info', 'sections', 'legend'];

const normalizeOrder = (order = [], available) => {
    const filtered = order.filter((blockId) => available.includes(blockId));
    const missing = available.filter((blockId) => !filtered.includes(blockId));
    return [...filtered, ...missing];
};

const buildLayoutBlocks = (data = {}) => {
    const raw = data.struttura_blocchi || {};
    const columns = raw.columns === 2 ? 2 : 1;
    const available = Object.keys(BLOCK_DEFINITIONS);
    const rawBlocks = raw.blocks || {};

    const blocks = available.reduce((acc, blockId) => {
        acc[blockId] = {
            id: blockId,
            label: BLOCK_DEFINITIONS[blockId].label,
            enabled: rawBlocks[blockId]?.enabled ?? true,
        };
        return acc;
    }, {});

    const order = {
        1: normalizeOrder(raw.order?.[1] || raw.order?.['1'] || DEFAULT_ORDER, available),
        2: normalizeOrder(raw.order?.[2] || raw.order?.['2'] || [], available),
    };

    if (columns === 1) {
        order[1] = normalizeOrder([...order[1], ...order[2]], available);
        order[2] = [];
    }

    return {
        columns,
        blocks,
        order,
        metadata: data.metadata || {}
    };
};

const BLOCK_ICONS = {
    logo: 'fa-image',
    info: 'fa-info-circle',
    sections: 'fa-utensils',
    legend: 'fa-exclamation-triangle',
};

const SortableBlockItem = ({ blockId, label, enabled }) => {
    const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
        id: blockId,
    });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.6 : 1,
        cursor: 'grab',
    };

    return (
        <div ref={setNodeRef} style={style} className={`list-group-item d-flex justify-content-between align-items-center ${!enabled ? 'opacity-50' : ''}`}>
            <div className="d-flex align-items-center">
                <i className={`fas ${BLOCK_ICONS[blockId]} me-3 text-nuvia-primary`} style={{ width: '20px' }}></i>
                <div>
                    <strong className="d-block">{label}</strong>
                    {!enabled && <span className="badge bg-secondary" style={{ fontSize: '0.6rem' }}>DISABILITATO</span>}
                </div>
            </div>
            <div className="d-flex align-items-center gap-3">
                <span {...attributes} {...listeners} className="p-2" style={{ cursor: 'grab' }}>
                    <i className="fas fa-grip-vertical text-muted"></i>
                </span>
            </div>
        </div>
    );
};

const ColumnContainer = ({ columnId, title, children }) => {
    const { setNodeRef, isOver } = useDroppable({ id: `column-${columnId}` });
    const style = {
        border: '1px dashed #ced4da',
        borderRadius: '0.5rem',
        padding: '0.75rem',
        background: isOver ? '#f8f9fa' : 'transparent',
    };

    return (
        <div ref={setNodeRef} style={style}>
            <h6 className="mb-2">{title}</h6>
            {children}
        </div>
    );
};

const LayoutEditor = () => {
    const { layoutId } = useParams();
    const { permissions } = usePermissions();
    const [layoutData, setLayoutData] = useState(null);
    const canEditLayouts = (permissions?.aggregate?.can_edit_layouts || permissions?.is_superuser) && !layoutData?.is_preset;

    const [activeTab, setActiveTab] = useState('design'); // design | structure | metadata

    const [formData, setFormData] = useState({
        nome_layout: '',
        font_principale: 'Helvetica',
        colore_font: '#000000',
    });
    const [blockLayout, setBlockLayout] = useState(buildLayoutBlocks());
    const [freePositions, setFreePositions] = useState({});
    const [logoFile, setLogoFile] = useState(null);
    const [logoPreview, setLogoPreview] = useState(null);
    const [backgroundFile, setBackgroundFile] = useState(null);
    const [backgroundPreview, setBackgroundPreview] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [isSaving, setIsSaving] = useState(false);
    const sensors = useSensors(
        useSensor(PointerSensor),
        useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
    );

    useEffect(() => {
        const fetchLayout = async () => {
            try {
                setLoading(true);
                const response = await getLayout(layoutId);
                const data = response.data;
                setLayoutData(data);
                setFormData({
                    nome_layout: data.nome_layout || '',
                    font_principale: data.font_principale || 'Helvetica',
                    colore_font: data.colore_font || '#000000',
                });
                setBlockLayout(buildLayoutBlocks(data));
                setFreePositions(data.metadata?.positions || {});
                if (data.logo) {
                    setLogoPreview(data.logo);
                }
                if (data.background_image) {
                    setBackgroundPreview(data.background_image);
                }
            } catch (err) {
                setError('Impossibile caricare il layout.');
            } finally {
                setLoading(false);
            }
        };
        fetchLayout();
    }, [layoutId]);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleBlockToggle = (blockId) => {
        setBlockLayout((prev) => ({
            ...prev,
            blocks: {
                ...prev.blocks,
                [blockId]: {
                    ...prev.blocks[blockId],
                    enabled: !prev.blocks[blockId]?.enabled,
                },
            },
        }));
    };

    const handleColumnChange = (e) => {
        const nextColumns = Number(e.target.value);
        setBlockLayout((prev) => {
            if (nextColumns === prev.columns) return prev;
            if (nextColumns === 1) {
                return {
                    ...prev,
                    columns: 1,
                    order: {
                        1: normalizeOrder([...prev.order[1], ...prev.order[2]], Object.keys(BLOCK_DEFINITIONS)),
                        2: [],
                    },
                };
            }
            const available = Object.keys(BLOCK_DEFINITIONS);
            return {
                ...prev,
                columns: 2,
                order: {
                    1: normalizeOrder(prev.order[1], available),
                    2: normalizeOrder(prev.order[2], available),
                },
            };
        });
    };

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setLogoFile(file);
            setLogoPreview(URL.createObjectURL(file));
        }
    };

    const handleBackgroundFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setBackgroundFile(file);
            setBackgroundPreview(URL.createObjectURL(file));
        }
    };

    const findColumnForBlock = (blockId, order) => {
        if (blockId === 'column-1') return '1';
        if (blockId === 'column-2') return '2';
        return Object.keys(order).find((columnId) => order[columnId].includes(blockId));
    };

    const handleDragEnd = (event) => {
        const { active, over } = event;
        if (!over) return;

        setBlockLayout((prev) => {
            const activeColumn = findColumnForBlock(active.id, prev.order);
            const overColumn = findColumnForBlock(over.id, prev.order);
            if (!activeColumn || !overColumn) return prev;

            if (activeColumn === overColumn) {
                const columnItems = prev.order[activeColumn];
                const oldIndex = columnItems.indexOf(active.id);
                const newIndex = columnItems.indexOf(over.id);
                if (oldIndex === -1) return prev;
                if (newIndex === -1) {
                    return {
                        ...prev,
                        order: {
                            ...prev.order,
                            [activeColumn]: [
                                ...columnItems.filter((id) => id !== active.id),
                                active.id,
                            ],
                        },
                    };
                }
                return {
                    ...prev,
                    order: {
                        ...prev.order,
                        [activeColumn]: arrayMove(columnItems, oldIndex, newIndex),
                    },
                };
            }

            const nextActiveItems = [...prev.order[activeColumn]];
            const nextOverItems = [...prev.order[overColumn]];
            const activeIndex = nextActiveItems.indexOf(active.id);
            if (activeIndex === -1) return prev;
            nextActiveItems.splice(activeIndex, 1);
            const overIndex = nextOverItems.indexOf(over.id);
            const insertIndex = overIndex === -1 ? nextOverItems.length : overIndex;
            nextOverItems.splice(insertIndex, 0, active.id);

            return {
                ...prev,
                order: {
                    ...prev.order,
                    [activeColumn]: nextActiveItems,
                    [overColumn]: nextOverItems,
                },
            };
        });
    };

    const handlePositionUpdate = (blockId, pos) => {
        setFreePositions(prev => ({
            ...prev,
            [blockId]: pos
        }));
    };

    const handleSaveChanges = async () => {
        if (!canEditLayouts) {
            toast.error('Non hai i permessi per modificare il layout.');
            return;
        }
        setIsSaving(true);

        const dataToSend = new FormData();
        dataToSend.append('nome_layout', formData.nome_layout);
        dataToSend.append('font_principale', formData.font_principale);
        dataToSend.append('colore_font', formData.colore_font);

        const metadata = {
            ...blockLayout.metadata,
            preset: blockLayout.metadata?.preset,
            border_style: blockLayout.metadata?.border_style,
            positions: freePositions,
            is_free_mode: true
        };

        dataToSend.append('metadata', JSON.stringify(metadata));

        dataToSend.append('struttura_blocchi', JSON.stringify({
            columns: blockLayout.columns,
            order: blockLayout.order,
            blocks: Object.keys(blockLayout.blocks).reduce((acc, blockId) => {
                acc[blockId] = { enabled: blockLayout.blocks[blockId].enabled };
                return acc;
            }, {}),
        }));
        if (logoFile) {
            dataToSend.append('logo', logoFile);
        }
        if (backgroundFile) {
            dataToSend.append('background_image', backgroundFile);
        }

        try {
            await updateLayout(layoutId, dataToSend);
            toast.success('Layout salvato con successo!');
        } catch (err) {
            toast.error('Errore durante il salvataggio del layout.');
        } finally {
            setIsSaving(false);
        }
    };

    const blockLists = useMemo(() => ({
        1: blockLayout.order[1].map((blockId) => blockLayout.blocks[blockId]),
        2: blockLayout.order[2].map((blockId) => blockLayout.blocks[blockId]),
    }), [blockLayout]);

    if (loading) return <div>Caricamento...</div>;
    if (error) return <div className="alert alert-danger">{error}</div>;

    return (
        <div className="menu-studio-shell p-0 vh-100 d-flex flex-column overflow-hidden">
            <ToastContainer position="top-right" autoClose={3000} theme="dark" />

            {/* Topbar del Designer */}
            <div className="studio-toolbar px-4">
                <div className="d-flex align-items-center gap-3">
                    <Link to="/layouts" className="btn btn-nuvia-ghost p-2 rounded-circle" style={{ width: '40px', height: '40px', display: 'grid', placeItems: 'center' }}>
                        <i className="fas fa-arrow-left"></i>
                    </Link>
                    <div>
                        <span className="tiny-badge bg-nuvia-primary mb-1">Noir Studio v2.0</span>
                        <h1 className="h5 mb-0 fw-bold text-white">{formData.nome_layout || 'Nuovo Layout'}</h1>
                    </div>
                </div>

                <div className="ms-auto d-flex align-items-center gap-3">
                    {layoutData?.is_preset && (
                        <span className="badge-soft smallest px-3 text-warning">
                            <i className="fas fa-lock me-1"></i> Preset Sola Lettura
                        </span>
                    )}
                    <button className="btn btn-nuvia-primary px-4 fw-bold" onClick={handleSaveChanges} disabled={isSaving || !canEditLayouts}>
                        {isSaving ? 'Sincronizzazione...' : 'PUBBLICA DESIGN'}
                    </button>
                </div>
            </div>

            <div className="studio-container flex-grow-1">
                {/* Sidebar delle Proprietà */}
                <div className="studio-sidebar">
                    <div className="sidebar-tabs">
                        <div className={`sidebar-tab ${activeTab === 'design' ? 'active' : ''}`} onClick={() => setActiveTab('design')}>
                            <i className="fas fa-palette me-2"></i> Stile
                        </div>
                        <div className={`sidebar-tab ${activeTab === 'structure' ? 'active' : ''}`} onClick={() => setActiveTab('structure')}>
                            <i className="fas fa-layer-group me-2"></i> Blocchi
                        </div>
                        <div className={`sidebar-tab ${activeTab === 'metadata' ? 'active' : ''}`} onClick={() => setActiveTab('metadata')}>
                            <i className="fas fa-cog me-2"></i> Info
                        </div>
                    </div>

                    <div className="sidebar-content">
                        {activeTab === 'design' && (
                            <div className="animate-in">
                                <div className="prop-group">
                                    <div className="prop-group-title">Tipografia & Colori</div>
                                    <div className="prop-row">
                                        <label className="small-label">Font Principale</label>
                                        <input
                                            type="text"
                                            className="form-control noir-input mt-2"
                                            value={formData.font_principale}
                                            onChange={handleInputChange}
                                            name="font_principale"
                                            placeholder="Es. Playfair Display"
                                            list="font-options"
                                            disabled={!canEditLayouts}
                                        />
                                        <datalist id="font-options">
                                            <option value="Poppins, sans-serif" />
                                            <option value="Playfair Display, serif" />
                                            <option value="Montserrat, sans-serif" />
                                            <option value="Inter, sans-serif" />
                                            <option value="Georgia, serif" />
                                        </datalist>
                                    </div>
                                    <div className="prop-row">
                                        <label className="small-label">Colore Testo</label>
                                        <div className="d-flex align-items-center mt-2 gap-3">
                                            <input
                                                type="color"
                                                className="form-control-color border-0 bg-transparent"
                                                value={formData.colore_font}
                                                onChange={handleInputChange}
                                                name="colore_font"
                                                style={{ width: '40px', height: '40px', padding: 0, cursor: 'pointer' }}
                                                disabled={!canEditLayouts}
                                            />
                                            <code className="text-muted-soft">{formData.colore_font}</code>
                                        </div>
                                    </div>
                                </div>

                                <div className="prop-group">
                                    <div className="prop-group-title">Background & Logo</div>
                                    <div className="prop-row">
                                        <label className="small-label">Logo Aziendale</label>
                                        <div className="mt-2 p-3 border border-dashed border-white border-opacity-10 rounded-3 text-center">
                                            {logoPreview ? (
                                                <div className="position-relative d-inline-block">
                                                    <img src={logoPreview} alt="Logo" style={{ maxWidth: '100%', maxHeight: '80px' }} />
                                                    <label htmlFor="logo-upload" className="btn btn-sm btn-dark position-absolute top-50 start-50 translate-middle opacity-0 hover-opacity-100 transition-all">Cambia</label>
                                                </div>
                                            ) : (
                                                <div className="smallest text-muted-soft py-2">Trascina o seleziona un logo</div>
                                            )}
                                            <input id="logo-upload" type="file" className="d-none" onChange={handleFileChange} accept="image/*" disabled={!canEditLayouts} />
                                            <button className="btn btn-nuvia-ghost smallest w-100 mt-2" onClick={() => document.getElementById('logo-upload').click()} disabled={!canEditLayouts}>Carica Immagine</button>
                                        </div>
                                    </div>
                                    <div className="prop-row mt-4">
                                        <label className="small-label">Texture di Sfondo</label>
                                        <div className="mt-2">
                                            {backgroundPreview && (
                                                <div className="mb-2 rounded-3 overflow-hidden border border-white border-opacity-10">
                                                    <img src={backgroundPreview} alt="Sfondo" style={{ width: '100%', height: '100px', objectFit: 'cover' }} />
                                                </div>
                                            )}
                                            <input id="bg-upload" type="file" className="d-none" onChange={handleBackgroundFileChange} accept="image/*" disabled={!canEditLayouts} />
                                            <button className="btn btn-nuvia-ghost smallest w-100" onClick={() => document.getElementById('bg-upload').click()} disabled={!canEditLayouts}>Sostituisci Sfondo</button>
                                        </div>
                                    </div>
                                </div>

                                <div className="prop-group">
                                    <div className="prop-group-title">Effetti & Bordi</div>
                                    <div className="prop-row">
                                        <label className="small-label">Stile Predefinito</label>
                                        <select
                                            className="form-select noir-select mt-2"
                                            value={blockLayout.metadata?.preset || ''}
                                            onChange={(e) => setBlockLayout(prev => ({
                                                ...prev,
                                                metadata: { ...prev.metadata, preset: e.target.value }
                                            }))}
                                            disabled={!canEditLayouts}
                                        >
                                            <option value="">Nessuno (Custom)</option>
                                            <option value="preset-gala">Gala Noir</option>
                                            <option value="preset-bistro">Bistro Vintage</option>
                                            <option value="preset-modern">Modern Slate</option>
                                        </select>
                                    </div>
                                    <div className="prop-row mt-3">
                                        <label className="small-label">Bordo Documento (CSS)</label>
                                        <input
                                            type="text"
                                            className="form-control noir-input mt-2"
                                            placeholder="10px double #gold"
                                            value={blockLayout.metadata?.border_style || ''}
                                            onChange={(e) => setBlockLayout(prev => ({
                                                ...prev,
                                                metadata: { ...prev.metadata, border_style: e.target.value }
                                            }))}
                                            disabled={!canEditLayouts}
                                        />
                                    </div>
                                </div>
                            </div>
                        )}

                        {activeTab === 'structure' && (
                            <div className="animate-in">
                                <div className="prop-group">
                                    <div className="prop-group-title">Organizzazione Flusso</div>
                                    <div className="prop-row">
                                        <label className="small-label">Colonne di Stampa</label>
                                        <div className="d-flex gap-2 mt-2">
                                            <button
                                                className={`btn flex-grow-1 smallest ${blockLayout.columns === 1 ? 'btn-nuvia-primary' : 'btn-nuvia-ghost'}`}
                                                onClick={() => handleColumnChange({ target: { value: 1 } })}
                                                disabled={!canEditLayouts}
                                            >1 Colonna</button>
                                            <button
                                                className={`btn flex-grow-1 smallest ${blockLayout.columns === 2 ? 'btn-nuvia-primary' : 'btn-nuvia-ghost'}`}
                                                onClick={() => handleColumnChange({ target: { value: 2 } })}
                                                disabled={!canEditLayouts}
                                            >2 Colonne</button>
                                        </div>
                                    </div>
                                </div>

                                <div className="prop-group">
                                    <div className="prop-group-title">Gerarchia Blocchi</div>
                                    <DndContext sensors={sensors} onDragEnd={handleDragEnd} collisionDetection={closestCenter}>
                                        <div className="d-flex flex-column gap-3">
                                            <ColumnContainer columnId={1} title="Zona A (Principale)">
                                                <SortableContext items={blockLayout.order[1]} strategy={verticalListSortingStrategy}>
                                                    <div className="list-group list-group-noir">
                                                        {blockLists[1].map((block) => (
                                                            <SortableBlockItem key={block.id} blockId={block.id} label={block.label} enabled={block.enabled} />
                                                        ))}
                                                    </div>
                                                </SortableContext>
                                            </ColumnContainer>
                                            {blockLayout.columns === 2 && (
                                                <ColumnContainer columnId={2} title="Zona B (Secondaria)">
                                                    <SortableContext items={blockLayout.order[2]} strategy={verticalListSortingStrategy}>
                                                        <div className="list-group list-group-noir">
                                                            {blockLists[2].map((block) => (
                                                                <SortableBlockItem key={block.id} blockId={block.id} label={block.label} enabled={block.enabled} />
                                                            ))}
                                                        </div>
                                                    </SortableContext>
                                                </ColumnContainer>
                                            )}
                                        </div>
                                    </DndContext>
                                </div>

                                <div className="prop-group">
                                    <div className="prop-group-title">Visibilità Componenti</div>
                                    {Object.values(blockLayout.blocks).map((block) => (
                                        <div key={block.id} className="d-flex justify-content-between align-items-center mb-2 p-2 bg-white bg-opacity-5 rounded-3">
                                            <span className="smaller fw-bold">{block.label}</span>
                                            <div className="form-check form-switch m-0">
                                                <input className="form-check-input" type="checkbox" checked={block.enabled} onChange={() => handleBlockToggle(block.id)} disabled={!canEditLayouts} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {activeTab === 'metadata' && (
                            <div className="animate-in">
                                <div className="prop-group">
                                    <div className="prop-group-title">Informazioni Generali</div>
                                    <div className="prop-row">
                                        <label className="small-label">Identificativo Layout</label>
                                        <input
                                            type="text"
                                            className="form-control noir-input mt-2"
                                            value={formData.nome_layout}
                                            onChange={handleInputChange}
                                            name="nome_layout"
                                            disabled={!canEditLayouts}
                                        />
                                    </div>
                                    <div className="prop-row mt-4">
                                        <label className="small-label">Ultima Modifica</label>
                                        <p className="text-muted-soft smallest mt-1">
                                            {layoutData?.data_modifica ? new Date(layoutData.data_modifica).toLocaleString() : 'N/A'}
                                        </p>
                                    </div>
                                    <div className="prop-row">
                                        <label className="small-label">Versione Documento</label>
                                        <p className="text-white fw-bold mb-0">v{layoutData?.versione || 1}.0</p>
                                    </div>
                                </div>

                                {!canEditLayouts && (
                                    <div className="alert alert-soft-warning p-3 smallest">
                                        <i className="fas fa-exclamation-triangle me-2"></i>
                                        I layout di sistema (Preset) non possono essere modificati direttamente.
                                        Duplica questo layout per apportare cambiamenti.
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Area di Lavoro (Canvas) */}
                <div className="studio-content">
                    <div className="studio-canvas-area">
                        <LayoutPreview
                            layoutProps={formData}
                            logoUrl={logoPreview}
                            backgroundImageUrl={backgroundPreview}
                            blockLayout={blockLayout}
                            positions={freePositions}
                            onPositionChange={handlePositionUpdate}
                            isEditable={canEditLayouts}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LayoutEditor;
