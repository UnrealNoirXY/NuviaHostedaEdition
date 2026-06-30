import React, { useCallback, useMemo } from 'react';
import { Responsive, WidthProvider } from 'react-grid-layout';
import WidgetRenderer from './WidgetRenderer';

const ResponsiveGridLayout = WidthProvider(Responsive);

const GRID_BREAKPOINTS = { lg: 1200, md: 996, sm: 768, xs: 480, xxs: 0 };
const GRID_COLUMNS = { lg: 12, md: 10, sm: 6, xs: 4, xxs: 2 };

const Dashboard = ({
    layouts,
    onLayoutChange,
    availableWidgets,
    isEditable,
    onRemoveWidget,
    focusMode = false,
    compactLayout = false,
    activeTimescale = 'oggi',
    isMobile = false,
}) => {

    const findWidgetName = (widgetId) => {
        const widget = availableWidgets.find(w => w.id === widgetId);
        return widget ? widget.name : 'Widget Sconosciuto';
    };

    // The layout for the largest breakpoint ('lg') is considered the master list of widgets.
    const masterLayout = layouts.lg || [];
    const prioritizedWidgetIds = useMemo(
        () => new Set(masterLayout.slice(0, 3).map((item) => item.i)),
        [masterLayout],
    );

    const margin = useMemo(() => (isMobile ? [6, 12] : [16, 16]), [isMobile]);
    const containerPadding = useMemo(() => (isMobile ? [6, 12] : [16, 16]), [isMobile]);
    const rowHeight = useMemo(() => (isMobile ? 92 : 30), [isMobile]);

    const handleDragStart = useCallback((layout, oldItem, newItem, placeholder, event) => {
        event.stopPropagation();
        document.body.classList.add('is-dragging-widget');
    }, []);

    const handleDragStop = useCallback(() => {
        document.body.classList.remove('is-dragging-widget');
    }, []);

    return (
        <ResponsiveGridLayout
            className={`layout ${focusMode ? 'layout-focus' : ''} ${compactLayout ? 'layout-compact' : ''}`}
            layouts={layouts}
            breakpoints={GRID_BREAKPOINTS}
            cols={GRID_COLUMNS}
            rowHeight={rowHeight}
            margin={margin}
            containerPadding={containerPadding}
            onLayoutChange={(layout, allLayouts) => onLayoutChange(allLayouts)}
            isDraggable={isEditable}
            isResizable={isEditable}
            draggableHandle={isEditable ? '.widget-drag-handle' : undefined}
            draggableCancel={'.react-resizable-handle, .widget-action, .widget-content-interactive, .no-drag, input, textarea, select, button, a'}
            preventCollision={!isEditable}
            compactType={compactLayout ? 'vertical' : null}
            isBounded
            measureBeforeMount={isMobile}
            useCSSTransforms={!isMobile}
            onDragStart={handleDragStart}
            onDragStop={handleDragStop}
            onResizeStart={handleDragStart}
            onResizeStop={handleDragStop}
            resizeHandles={['se']}
            style={{ width: '100%' }}
        >
            {masterLayout.map(item => (
                <div
                    key={item.i}
                    data-grid={item}
                    className={`card shadow-sm ${isEditable ? 'widget-editable' : ''} ${focusMode && prioritizedWidgetIds.has(item.i) ? 'widget-focus-highlight' : ''}`}
                    data-timescale={activeTimescale}
                >
                    <div className="card-header">
                        <div className="widget-header">
                            <h6 className="card-title mb-0 widget-title">{findWidgetName(item.i)}</h6>
                            {isEditable && (
                                <div className="widget-actions">
                                    <button
                                        type="button"
                                        className="widget-drag-handle"
                                        aria-label="Trascina per spostare il widget"
                                        title="Trascina per spostare il widget"
                                    >
                                        <i className="fas fa-grip-vertical" aria-hidden="true"></i>
                                    </button>
                                    <button
                                        type="button"
                                        className="btn btn-sm btn-outline-danger widget-action"
                                        onClick={(event) => {
                                            event.stopPropagation();
                                            onRemoveWidget(item.i);
                                        }}
                                        title="Rimuovi Widget"
                                    >
                                        <i className="fas fa-times" aria-hidden="true"></i>
                                        <span className="visually-hidden">Rimuovi widget</span>
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                    <div className="card-body widget-content">
                        <WidgetRenderer widgetId={item.i} />
                    </div>
                </div>
            ))}
        </ResponsiveGridLayout>
    );
};

export default Dashboard;
