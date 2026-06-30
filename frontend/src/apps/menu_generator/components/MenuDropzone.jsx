import React from 'react';
import { useDroppable } from '@dnd-kit/core';
import {
    SortableContext,
    useSortable,
    verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const SortablePiattoItem = ({ piatto, onRemove }) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging
    } = useSortable({
        id: `menu-piatto-${piatto.id}`,
        data: { type: 'piatto', piatto }
    });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        cursor: 'grab',
        zIndex: isDragging ? 1000 : 1,
        opacity: isDragging ? 0.5 : 1,
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            className={`list-group-item d-flex justify-content-between align-items-center ${isDragging ? 'shadow-lg border-nuvia' : ''}`}
        >
            <div className="d-flex align-items-center gap-2">
                 <i className="fas fa-grip-lines text-muted-soft smaller"></i>
                 <div>
                    <span className="d-block fw-bold" style={{ fontSize: '0.9rem' }}>{piatto.nome}</span>
                    <small className="text-muted-soft smaller">{piatto.categoria_display}</small>
                 </div>
            </div>
            <button className="btn btn-sm btn-link text-danger p-0 ms-2" onClick={(e) => { e.stopPropagation(); onRemove(piatto.id); }}>
                <i className="bi bi-trash"></i>
            </button>
        </div>
    );
};


const SortableSection = ({ section, children }) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging,
    } = useSortable({
        id: section.id,
        data: { type: 'section', sectionId: section.id }
    });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.7 : 1,
    };

    return (
        <div ref={setNodeRef} style={style} className="menu-section-container mb-4">
            <div className="d-flex justify-content-between align-items-center mb-2 px-2">
                <div className="d-flex align-items-center gap-2">
                    <span
                        className="btn-grab p-1"
                        {...attributes}
                        {...listeners}
                    >
                        <i className="fas fa-grip-vertical text-muted-soft" aria-hidden="true"></i>
                    </span>
                    <h6 className="mb-0 text-uppercase letter-spacing-1 fw-bold smaller">{section.title}</h6>
                </div>
                <span className="badge bg-dark border border-white border-opacity-10 text-muted-soft smallest">
                    {section.piatti.length}
                </span>
            </div>
            {children}
        </div>
    );
};

const MenuDropzone = ({ sections, onRemove, columns = 1 }) => {
    const { setNodeRef, isOver } = useDroppable({
        id: 'menu-dropzone',
        data: { accept: ['piatto'] }
    });

    const hasPiatti = sections.some((section) => section.piatti.length > 0);

    return (
        <div className={`d-flex flex-column h-100 ${isOver ? 'shadow-glow-nuvia rounded-4' : ''}`}>
            <div className="d-flex justify-content-between align-items-center mb-4">
                <div className="d-flex align-items-center gap-2">
                    <div className="p-2 rounded bg-nuvia-accent bg-opacity-10 text-nuvia-accent">
                        <i className="fas fa-layer-group"></i>
                    </div>
                    <span className="smallest fw-bold text-white uppercase ls-1">Architettura del Menu</span>
                </div>
                <div className="d-flex gap-2">
                    <span className="tiny-badge bg-white bg-opacity-10 text-white border-white border-opacity-10">COLONNE: {columns}</span>
                    <span className="tiny-badge bg-nuvia-primary bg-opacity-10 text-nuvia-primary border-nuvia-primary border-opacity-20">PIATTI: {sections.reduce((acc, s) => acc + s.piatti.length, 0)}</span>
                </div>
            </div>

            <div
                ref={setNodeRef}
                className={`studio-dropzone-body flex-grow-1 p-1 transition-all rounded-4 ${isOver ? 'bg-nuvia-primary bg-opacity-5' : ''}`}
                style={{ overflowY: 'auto' }}
            >
                <SortableContext items={sections.map((section) => section.id)} strategy={verticalListSortingStrategy}>
                    {sections.map((section) => (
                        <SortableSection key={section.id} section={section}>
                            <SortableContext items={section.piatti.map((piatto) => `menu-piatto-${piatto.id}`)} strategy={verticalListSortingStrategy}>
                                <div className="list-group list-group-noir">
                                    {section.piatti.map((piatto) => (
                                        <SortablePiattoItem
                                            key={piatto.id}
                                            piatto={piatto}
                                            onRemove={onRemove}
                                        />
                                    ))}
                                    {section.piatti.length === 0 && (
                                        <div className="p-4 text-center text-muted-soft smallest border border-dashed border-white border-opacity-10 rounded-4 bg-white bg-opacity-5 uppercase ls-1 fw-bold">
                                            Sezione Libera
                                        </div>
                                    )}
                                </div>
                            </SortableContext>
                        </SortableSection>
                    ))}
                </SortableContext>

                {!hasPiatti && (
                    <div className="text-center text-muted-soft p-5 border border-dashed border-white border-opacity-10 rounded-5 mt-5 bg-white bg-opacity-5 animate-pulse">
                        <i className="fas fa-hand-pointer d-block h2 opacity-25 mb-4"></i>
                        <h6 className="text-white fw-bold mb-2">Composizione Vuota</h6>
                        <p className="smallest uppercase ls-1 mb-0">Trascina i piatti dalla libreria a sinistra<br/>per popolare le sezioni del menu.</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default MenuDropzone;
