import React, { useMemo, useState, useEffect } from 'react';
import { Rnd } from 'react-rnd';

const LayoutPreview = ({ layoutProps, logoUrl, backgroundImageUrl, blockLayout, positions = {}, onPositionChange, isEditable = false }) => {
    const [zoom, setZoom] = useState(0.45);
    const [guides, setGuides] = useState({ x: null, y: null });
    const [contextMenu, setContextMenu] = useState(null);

    const handleContextMenu = (e) => {
        if (!isEditable) return;
        e.preventDefault();

        // Calcola coordinate relative al canvas A4
        const canvas = e.currentTarget.querySelector('.a4-page-simulation');
        if (!canvas) return;

        const rect = canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / zoom;
        const y = (e.clientY - rect.top) / zoom;

        setContextMenu({
            visible: true,
            x: e.clientX,
            y: e.clientY,
            canvasX: x,
            canvasY: y
        });
    };

    const closeContextMenu = () => setContextMenu(null);

    const addElement = (type) => {
        if (!contextMenu) return;

        const newBlockId = `${type}_${Date.now()}`;
        const defaultWidth = type === 'image' ? 200 : 300;

        onPositionChange(newBlockId, {
            x: contextMenu.canvasX - (defaultWidth / 2),
            y: contextMenu.canvasY - 50,
            width: defaultWidth,
            height: type === 'image' ? 150 : 100,
            type: type
        });

        closeContextMenu();
    };

    const presetClass = blockLayout.metadata?.preset || '';
    const backgroundImage = backgroundImageUrl || '';
    const borderStyle = blockLayout.metadata?.border_style || '';

    const previewContainerStyle = {
        fontFamily: layoutProps.font_principale || 'serif',
        color: layoutProps.colore_font || '#1a1a1a',
        transform: `scale(${zoom})`,
        transformOrigin: 'top center',
        transition: 'transform 0.2s ease-out',
        margin: '20px auto',
    };

    const renderBlockContent = (blockId) => {
        switch (blockId) {
            case 'logo':
                return (
                    <div className="text-center">
                        {logoUrl ? (
                            <img src={logoUrl} alt="Logo" style={{ maxWidth: '120px' }} />
                        ) : (
                            <div className="border rounded p-2 text-muted smallest">Logo non impostato</div>
                        )}
                    </div>
                );
            case 'info':
                return (
                    <div className="header-block" key="info" style={{ border: 'none', marginBottom: 0, paddingBottom: 0 }}>
                        <h1>Nome del Menu</h1>
                        <div className="info-subtitle">
                            15 Settembre 2025 &bull; Cena
                        </div>
                    </div>
                );
            case 'sections':
                return (
                    <div>
                        <div className="category-section">
                            <h2 className="category-title">Antipasti</h2>
                            <div className="dish-item">
                                <div className="dish-header">
                                    <span className="dish-price">12 €</span>
                                    <span className="dish-name">Insalata di Mare</span>
                                </div>
                                <div className="dish-description">
                                    Polpo, seppie e gamberetti con emulsione al limone.
                                </div>
                            </div>
                        </div>
                        <div className="category-section">
                            <h2 className="category-title">Primi</h2>
                            <div className="dish-item">
                                <div className="dish-header">
                                    <span className="dish-price">18 €</span>
                                    <span className="dish-name">Risotto agli Agrumi</span>
                                </div>
                            </div>
                        </div>
                    </div>
                );
            case 'legend':
                return (
                    <div className="legend-block" style={{ marginTop: 0, paddingTop: 0, border: 'none' }}>
                        <div className="legend-title">Legenda Allergeni</div>
                        <ul className="legend-list">
                            <li><strong>Glutine</strong>: presente in base pizza e pasta.</li>
                            <li><strong>Crostacei</strong>: presente nei piatti di mare.</li>
                        </ul>
                    </div>
                );
            default:
                return null;
        }
    };

    const allBlockIds = ['logo', 'info', 'sections', 'legend'];

    return (
        <div className="h-100 d-flex flex-column w-100 position-relative">
            {/* Workbench Controls Overlay */}
            <div className="preview-controls mb-0 shadow-sm" style={{
                position: 'absolute',
                top: '20px',
                right: '20px',
                zIndex: 1000,
                borderRadius: '999px',
                width: 'auto',
                background: 'rgba(15, 23, 42, 0.9)',
                padding: '8px 24px'
            }}>
                <label className="smallest uppercase ls-1 text-muted-soft me-3 fw-bold">Zoom Tavola</label>
                <input
                    type="range"
                    min="0.25"
                    max="1.1"
                    step="0.05"
                    value={zoom}
                    onChange={(e) => setZoom(parseFloat(e.target.value))}
                    className="zoom-slider"
                    style={{ width: '120px' }}
                />
                <span className="smallest text-white ms-3 fw-bold">{Math.round(zoom * 100)}%</span>
            </div>

            <div className="flex-grow-1 overflow-auto p-5" style={{
                background: '#000',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'flex-start'
            }}>
                <div style={previewContainerStyle}>
                    <div
                        className={`a4-page-simulation ${presetClass}`}
                        style={{
                            backgroundImage: backgroundImage ? `url(${backgroundImage})` : 'none',
                            border: borderStyle || undefined,
                            position: 'relative',
                            overflow: 'hidden'
                        }}
                        onContextMenu={handleContextMenu}
                        onClick={closeContextMenu}
                    >
                        {[...allBlockIds.filter(id => blockLayout.blocks[id]?.enabled), ...Object.keys(positions).filter(id => !allBlockIds.includes(id))].map(blockId => {
                            const pos = positions[blockId] || { x: 50, y: 50 + (allBlockIds.indexOf(blockId) * 150), width: 600 };
                            return (
                                <Rnd
                                    key={blockId}
                                    size={{ width: pos.width || 'auto', height: pos.height || 'auto' }}
                                    position={{ x: pos.x, y: pos.y }}
                                    dragGrid={[10, 10]}
                                    resizeGrid={[10, 10]}
                                    onDrag={(e, d) => {
                                        if (isEditable) {
                                            const parent = document.querySelector('.a4-page-simulation');
                                            if (parent) {
                                                const pw = parent.offsetWidth;
                                                const ph = parent.offsetHeight;
                                                const w = e.target.offsetWidth;
                                                const h = e.target.offsetHeight;

                                                let gx = null, gy = null;
                                                // Calcola allineamento con i bordi e il centro
                                                if (Math.abs(d.x - pw/2 + w/2) < 10) gx = pw/2; // Centro verticale
                                                if (Math.abs(d.y - ph/2 + h/2) < 10) gy = ph/2; // Centro orizzontale
                                                if (Math.abs(d.x) < 10) gx = 0; // Bordo sinistro
                                                if (Math.abs(d.x + w - pw) < 10) gx = pw; // Bordo destro

                                                setGuides({ x: gx, y: gy });
                                            }
                                        }
                                    }}
                                    onDragStop={(e, d) => {
                                        setGuides({ x: null, y: null });
                                        if (isEditable) {
                                            // Snapping manuale su stop
                                            const parent = document.querySelector('.a4-page-simulation');
                                            let finalX = d.x;
                                            let finalY = d.y;
                                            if (parent) {
                                                const pw = parent.offsetWidth;
                                                const w = e.target.offsetWidth;
                                                if (Math.abs(d.x - pw/2 + w/2) < 10) finalX = pw/2 - w/2;
                                            }
                                            onPositionChange(blockId, { ...pos, x: finalX, y: finalY });
                                        }
                                    }}
                                    onResize={(e, direction, ref, delta, position) => {
                                        if (isEditable) {
                                            setGuides({ x: position.x, y: position.y });
                                        }
                                    }}
                                    onResizeStop={(e, direction, ref, delta, position) => {
                                        setGuides({ x: null, y: null });
                                        if (isEditable) onPositionChange(blockId, {
                                            x: position.x,
                                            y: position.y,
                                            width: ref.offsetWidth,
                                            height: ref.offsetHeight,
                                        });
                                    }}
                                    disableDragging={!isEditable}
                                    enableResizing={isEditable}
                                    bounds="parent"
                                    style={{
                                        border: isEditable ? '1px solid rgba(56, 189, 248, 0.3)' : 'none',
                                        padding: '5px',
                                        backgroundColor: isEditable ? 'rgba(56, 189, 248, 0.02)' : 'transparent',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        zIndex: 10,
                                        transition: 'background-color 0.2s',
                                    }}
                                    className="rnd-block-hover"
                                >
                                    {isEditable && (
                                        <div className="position-absolute top-0 start-0 translate-middle-y smallest bg-nuvia-accent text-dark px-2 fw-bold rounded-1 opacity-0 block-label-tag" style={{ fontSize: '0.6rem', pointerEvents: 'none', zIndex: 100 }}>
                                            {blockId.startsWith('text') ? 'TESTO LIBERO' : blockId.startsWith('image') ? 'IMMAGINE' : blockId.toUpperCase()}
                                        </div>
                                    )}
                                    {blockId.startsWith('text') ? (
                                        <div style={{ padding: '10px', fontSize: '1.2rem' }}>Inserisci testo qui...</div>
                                    ) : blockId.startsWith('image') ? (
                                        <div style={{ width: '100%', height: '100%', border: '2px dashed rgba(255,255,255,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                            <i className="fas fa-image text-muted" style={{ fontSize: '2rem' }}></i>
                                        </div>
                                    ) : (
                                        renderBlockContent(blockId)
                                    )}
                                </Rnd>
                            );
                        })}
                        {isEditable && guides.x !== null && (
                            <div style={{
                                position: 'absolute',
                                left: guides.x,
                                top: 0,
                                bottom: 0,
                                width: '1px',
                                borderLeft: '1px dashed #38bdf8',
                                zIndex: 100,
                                pointerEvents: 'none'
                            }} />
                        )}
                        {isEditable && (
                            <>
                                <div style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '1px', borderLeft: '1px solid rgba(56, 189, 248, 0.2)', zIndex: 5, pointerEvents: 'none' }} />
                                <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '1px', borderTop: '1px solid rgba(56, 189, 248, 0.2)', zIndex: 5, pointerEvents: 'none' }} />
                            </>
                        )}
                        {isEditable && guides.y !== null && (
                            <div style={{
                                position: 'absolute',
                                top: guides.y,
                                left: 0,
                                right: 0,
                                height: '1px',
                                borderTop: '1px dashed #38bdf8',
                                zIndex: 100,
                                pointerEvents: 'none'
                            }} />
                        )}
                    </div>
                </div>
            </div>

            {/* Context Menu UI */}
            {contextMenu && (
                <div
                    className="glass-card shadow-glow border-nuvia"
                    style={{
                        position: 'fixed',
                        top: contextMenu.y,
                        left: contextMenu.x,
                        zIndex: 2000,
                        width: '220px',
                        padding: '8px',
                        borderRadius: '12px'
                    }}
                >
                    <div className="smallest fw-bold text-nuvia-accent uppercase ls-1 mb-2 px-2">Aggiungi Elemento</div>
                    <button className="btn btn-nuvia-ghost w-100 text-start smallest fw-bold py-2 px-3 border-0 mb-1" onClick={() => addElement('image')}>
                        <i className="fas fa-image me-2"></i> IMMAGINE
                    </button>
                    <button className="btn btn-nuvia-ghost w-100 text-start smallest fw-bold py-2 px-3 border-0 mb-1" onClick={() => addElement('text')}>
                        <i className="fas fa-font me-2"></i> TESTO LIBERO
                    </button>
                    <div className="border-top border-white border-opacity-10 my-1"></div>
                    <button className="btn btn-link text-danger w-100 text-start smallest fw-bold py-2 px-3 text-decoration-none" onClick={closeContextMenu}>
                        ANNULLA
                    </button>
                </div>
            )}
        </div>
    );
};

export default LayoutPreview;
