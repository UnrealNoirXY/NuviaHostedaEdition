import React, { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import MenuList from './MenuList';
import MenuForm from './MenuForm';
import { usePermissions } from '../permissions';

const MenuDashboard = () => {
    const { permissions } = usePermissions();
    const canEditMenus = permissions?.aggregate?.can_edit_menus || permissions?.is_superuser;

    const [isFormOpen, setIsFormOpen] = useState(false);
    const [editingMenu, setEditingMenu] = useState(null);
    const [refreshTrigger, setRefreshTrigger] = useState(0);

    const handleOpenForm = (menu = null) => {
        setEditingMenu(menu);
        setIsFormOpen(true);
    };

    const handleCloseForm = () => {
        setIsFormOpen(false);
        setEditingMenu(null);
    };

    const handleSuccess = useCallback(() => {
        handleCloseForm();
        setRefreshTrigger(prev => prev + 1); // Trigger a refresh of the list
    }, []);

    return (
        <div className="glass-card p-4 border-white border-opacity-5">
            <div className="d-flex justify-content-between align-items-center mb-5 flex-wrap gap-4">
                <div>
                    <div className="d-flex align-items-center gap-2 mb-2">
                        <div className="p-2 rounded bg-nuvia-primary bg-opacity-10 text-nuvia-primary">
                            <i className="fas fa-scroll"></i>
                        </div>
                        <span className="smallest fw-bold text-nuvia-accent uppercase ls-1">Archivio Servizio</span>
                    </div>
                    <h2 className="h3 mb-0 fw-bold text-white ls-tight">REGISTRO MENU</h2>
                    <p className="text-muted-soft smallest uppercase fw-bold ls-1 mt-1">Gestisci la programmazione e i piatti del giorno</p>
                </div>

                <div className="d-flex gap-3 align-items-center flex-wrap">
                    <Link className={`btn btn-nuvia-ghost px-4 py-2 smallest fw-bold border-white border-opacity-10 ${!canEditMenus ? 'disabled' : ''}`} to={canEditMenus ? '/wizard' : '#'}>
                        <i className="fas fa-magic me-2"></i> WIZARD GUIDATO
                    </Link>
                    <button className="btn btn-nuvia-primary px-4 py-2 smallest fw-bold" onClick={() => handleOpenForm()} disabled={!canEditMenus}>
                        <i className="fas fa-plus me-2"></i> NUOVO MENU
                    </button>
                    {!canEditMenus && (
                        <div className="badge-soft border border-warning border-opacity-20 text-warning px-3 py-2 smallest fw-bold">
                            <i className="fas fa-lock me-2"></i> MODALITÀ SOLA LETTURA
                        </div>
                    )}
                </div>
            </div>

            <MenuList
                onEdit={handleOpenForm}
                refreshTrigger={refreshTrigger}
            />

            {isFormOpen && (
                <MenuForm
                    menu={editingMenu}
                    onClose={handleCloseForm}
                    onSuccess={handleSuccess}
                />
            )}
        </div>
    );
};

export default MenuDashboard;
