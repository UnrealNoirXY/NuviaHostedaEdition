import React, { useState, useCallback } from 'react';
import LayoutForm from './LayoutForm';
import LayoutList from './LayoutList';
import { usePermissions } from '../permissions';

const LayoutDashboard = () => {
    const { permissions } = usePermissions();
    const canEditLayouts = permissions?.aggregate?.can_edit_layouts || permissions?.is_superuser;
    const [isFormOpen, setIsFormOpen] = useState(false);
    const [editingLayout, setEditingLayout] = useState(null);
    const [refreshTrigger, setRefreshTrigger] = useState(0);

    const handleOpenForm = (layout = null) => {
        setEditingLayout(layout);
        setIsFormOpen(true);
    };

    const handleCloseForm = () => {
        setIsFormOpen(false);
        setEditingLayout(null);
    };

    const handleSuccess = useCallback(() => {
        handleCloseForm();
        setRefreshTrigger(prev => prev + 1); // Ricarica la lista
    }, []);

    return (
        <div className="glass-card p-4 border-white border-opacity-5">
            <div className="d-flex justify-content-between align-items-center mb-5 flex-wrap gap-4">
                <div>
                    <div className="d-flex align-items-center gap-2 mb-2">
                        <div className="p-2 rounded bg-nuvia-primary bg-opacity-10 text-nuvia-primary">
                            <i className="fas fa-palette"></i>
                        </div>
                        <span className="smallest fw-bold text-nuvia-accent uppercase ls-1">Design System</span>
                    </div>
                    <h2 className="h3 mb-0 fw-bold text-white ls-tight">STILI & LAYOUT</h2>
                    <p className="text-muted-soft smallest uppercase fw-bold ls-1 mt-1">Personalizza l'identità visiva dei tuoi menu cartacei</p>
                </div>

                <div className="d-flex gap-3 align-items-center flex-wrap">
                    <button className="btn btn-nuvia-primary px-4 py-2 smallest fw-bold" onClick={() => handleOpenForm()} disabled={!canEditLayouts}>
                        <i className="fas fa-plus me-2"></i> NUOVO LAYOUT
                    </button>
                    {!canEditLayouts && (
                        <div className="badge-soft border border-warning border-opacity-20 text-warning px-3 py-2 smallest fw-bold">
                            <i className="fas fa-lock me-2"></i> MODALITÀ SOLA LETTURA
                        </div>
                    )}
                </div>
            </div>

            <div className="mb-5 p-4 rounded-4 bg-white bg-opacity-5 border border-white border-opacity-5">
                <div className="row align-items-center">
                    <div className="col-md-8">
                        <h5 className="text-white fw-bold mb-2 smaller">Libreria Stili</h5>
                        <p className="text-muted-soft smallest uppercase ls-1 mb-0">Seleziona un layout esistente per modificarlo nel Designer o creane uno da zero.</p>
                    </div>
                </div>
            </div>

            <LayoutList
                onEdit={handleOpenForm}
                refreshTrigger={refreshTrigger}
            />

            {isFormOpen && (
                <LayoutForm
                    layout={editingLayout}
                    onClose={handleCloseForm}
                    onSuccess={handleSuccess}
                />
            )}
        </div>
    );
};

export default LayoutDashboard;
