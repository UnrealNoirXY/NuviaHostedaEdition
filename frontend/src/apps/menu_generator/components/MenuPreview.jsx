import React, { useMemo, useState } from 'react';
import { Rnd } from 'react-rnd';

const MenuPreview = ({ layoutProps, logoUrl, backgroundImageUrl, piatti, menuName, sections, menuData, typography }) => {
    const { font_principale, colore_font, struttura_blocchi, metadata } = layoutProps || {};
    const [zoom, setZoom] = useState(0.65);

    const presetClass = metadata?.preset || '';
    const backgroundImage = backgroundImageUrl || metadata?.background_image_url || '';
    const borderStyle = metadata?.border_style || '';
    const positions = metadata?.positions || {};

    const previewContainerStyle = {
        fontFamily: font_principale || 'serif',
        color: colore_font || '#1a1a1a',
        transform: `scale(${zoom})`,
        transformOrigin: 'top center',
        transition: 'transform 0.2s ease-out',
        margin: '20px auto',
    };

    const previewSections = useMemo(() => {
        if (sections && sections.length > 0) {
            return sections.map((section) => ({
                title: section.title,
                piatti: section.piatti || [],
            }));
        }

        if (!piatti || piatti.length === 0) return [];
        const grouped = new Map();
        piatti.forEach((piatto) => {
            const category = piatto.categoria_display || 'Altro';
            if (!grouped.has(category)) {
                grouped.set(category, []);
            }
            grouped.get(category).push(piatto);
        });
        return Array.from(grouped.entries()).map(([title, items]) => ({
            title,
            piatti: items,
        }));
    }, [piatti, sections]);

    const renderBlockContent = (blockId) => {
        switch (blockId) {
            case 'logo':
                return logoUrl ? (
                    <div className="text-center mb-0">
                        <img src={logoUrl} alt="Logo" style={{ maxWidth: '120px' }} />
                    </div>
                ) : null;
            case 'info':
                return (
                    <div className="header-block" key="info" style={{ border: 'none', marginBottom: 0, paddingBottom: 0 }}>
                        <h1>{menuName || 'Il Nostro Menu'}</h1>
                        {menuData && (
                            <div className="info-subtitle">
                                {menuData.data_evento && <span>{new Date(menuData.data_evento).toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric' })} &bull; </span>}
                                {menuData.turno && <span className="text-capitalize">{menuData.turno}</span>}
                            </div>
                        )}
                        {menuData?.ospiti_target && (
                            <div style={{ marginTop: '5px', fontSize: '10pt', opacity: 0.8 }}>{menuData.ospiti_target}</div>
                        )}
                    </div>
                );
            case 'sections':
                return (
                    <div>
                        {previewSections.map((section) => (
                            <div key={section.title} className="category-section">
                                <h2 className="category-title" style={{ fontSize: `${typography?.sectionTitleSize || 16}pt` }}>{section.title}</h2>
                                {section.piatti.map((piatto) => (
                                    <div key={piatto.id} className="dish-item">
                                        <div className="dish-header">
                                            <span className="dish-price">
                                                {piatto.prezzo ? `${piatto.prezzo} €` : ''}
                                            </span>
                                            <span className="dish-name" style={{ fontSize: `${typography?.dishNameSize || 12}pt` }}>
                                                {piatto.nome}
                                            </span>
                                        </div>
                                        {piatto.descrizione && (
                                            <div className="dish-description" style={{ fontSize: `${typography?.dishDescriptionSize || 10.5}pt`, color: typography?.secondaryTextColor || undefined }}>
                                                {piatto.descrizione}
                                            </div>
                                        )}
                                        {(piatto.allergeni_details?.length > 0 || piatto.allergen_summary) && (
                                            <div className="dish-allergens">
                                                <strong>Allergeni:</strong> {piatto.allergeni_details?.map(a => a.nome).join(', ')}
                                                {piatto.allergen_summary && (piatto.allergeni_details?.length > 0 ? `, ${piatto.allergen_summary}` : piatto.allergen_summary)}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ))}
                    </div>
                );
            case 'legend':
                const allAllergeni = new Map();
                piatti?.forEach(p => {
                    p.allergeni_details?.forEach(a => allAllergeni.set(a.id, a));
                });
                if (allAllergeni.size === 0) return null;
                return (
                    <div className="legend-block" style={{ marginTop: 0, paddingTop: 0, border: 'none' }}>
                        <div className="legend-title">Legenda Allergeni</div>
                        <ul className="legend-list">
                            {Array.from(allAllergeni.values()).map(a => (
                                <li key={a.id}>
                                    <strong>{a.nome}</strong>{a.descrizione ? `: ${a.descrizione}` : ''}
                                </li>
                            ))}
                        </ul>
                    </div>
                )
            default:
                return null;
        }
    };

    const allBlockIds = ['logo', 'info', 'sections', 'legend'];

    return (
        <>
        <div className="preview-controls">
            <div className="d-flex align-items-center gap-2 me-auto">
                <span className="tiny-badge">A4 WYSIWYG Mode</span>
                <span className="small text-white opacity-50">Precisione PDF: Alta</span>
            </div>
            <label className="small text-white opacity-50">Zoom</label>
            <input
                type="range"
                min="0.3"
                max="1.2"
                step="0.05"
                value={zoom}
                onChange={(e) => setZoom(parseFloat(e.target.value))}
                className="zoom-slider"
            />
            <span className="small text-white opacity-75">{Math.round(zoom * 100)}%</span>
            <button className="btn btn-sm btn-nuvia-ghost py-0" onClick={() => setZoom(0.65)}>Reset</button>
        </div>
        <div style={previewContainerStyle} className="menu-preview-document">
            <div
                className={`a4-page-simulation ${presetClass}`}
                style={{
                    backgroundImage: backgroundImage ? `url(${backgroundImage})` : 'none',
                    border: borderStyle || undefined,
                    position: 'relative',
                    overflow: 'hidden'
                }}
            >
                {!menuData?.is_published && <div className="watermark">BOZZA</div>}

                {allBlockIds.filter(id => struttura_blocchi?.blocks?.[id]?.enabled !== false).map(blockId => {
                    const pos = positions[blockId] || { x: 50, y: 50 + (allBlockIds.indexOf(blockId) * 150), width: 600 };
                    return (
                        <Rnd
                            key={blockId}
                            size={{ width: pos.width || 'auto', height: pos.height || 'auto' }}
                            position={{ x: pos.x, y: pos.y }}
                            disableDragging={true}
                            enableResizing={false}
                            style={{
                                display: 'flex',
                                flexDirection: 'column',
                                zIndex: 10
                            }}
                        >
                            {renderBlockContent(blockId)}
                        </Rnd>
                    );
                })}

                {previewSections.length === 0 && (
                    <p style={{ fontStyle: 'italic', textAlign: 'center', marginTop: '2rem', color: '#999', position: 'absolute', top: '50%', width: '100%' }}>
                        Il menu è in fase di composizione.
                    </p>
                )}
            </div>
        </div>
        </>
    );
};

export default MenuPreview;
