import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { HashRouter as Router, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import './styles/preview.css';
import PiattoForm from './components/PiattoForm';
import PiattoList from './components/PiattoList';
import MenuDashboard from './components/MenuDashboard';
import MenuEditor from './components/MenuEditor';
import MenuWizard from './components/MenuWizard';
import ExecutiveDashboard from './components/ExecutiveDashboard';
import LayoutDashboard from './components/LayoutDashboard';
import LayoutEditor from './components/LayoutEditor';
import CatalogDashboard from './components/CatalogDashboard';
import { PermissionsProvider, usePermissions } from './permissions';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles/theme.css';

const useStudioBodyClass = () => {
    React.useEffect(() => {
        document.body.classList.add('menu-studio-body');
        return () => document.body.classList.remove('menu-studio-body');
    }, []);
};

const AppContent = () => {
    useStudioBodyClass();
    const location = useLocation();
    const { permissions, loading } = usePermissions();
    const [refreshTrigger, setRefreshTrigger] = useState(0);
    const [editingPiatto, setEditingPiatto] = useState(null);

    const handleSuccess = () => {
        setRefreshTrigger(prev => prev + 1);
        setEditingPiatto(null);
    };

    const handleEdit = (piatto) => {
        setEditingPiatto(piatto);
    };

    const clearEditing = () => {
        setEditingPiatto(null);
    };

    // Determine active tab from the route
    const getActiveTab = (pathname) => {
        if (pathname.startsWith('/executive')) return 'executive';
        if (pathname.startsWith('/wizard')) return 'wizard';
        if (pathname.startsWith('/menu')) return 'menu';
        if (pathname.startsWith('/layouts')) return 'layouts';
        if (pathname.startsWith('/cataloghi')) return 'cataloghi';
        return 'piatti';
    };

    const activeTab = getActiveTab(location.pathname);
    const hasMemberships = permissions?.is_superuser
        || permissions?.is_owner
        || (permissions?.structures || []).length > 0;

    const showExecutive = permissions?.is_superuser || permissions?.is_owner;

    return (
        <div className="menu-studio-shell">
            <nav className="studio-nav glass-card">
                {showExecutive && (
                    <Link className={activeTab === 'executive' ? 'active' : ''} to="/executive">
                        DASHBOARD
                    </Link>
                )}
                <Link className={activeTab === 'wizard' ? 'active' : ''} to="/wizard">
                    NUOVO MENU
                </Link>
                <Link className={activeTab === 'menu' ? 'active' : ''} to="/menu">
                    STORICO
                </Link>
                <Link className={activeTab === 'piatti' ? 'active' : ''} to="/piatti">
                    SICUREZZA
                </Link>
                <Link className={activeTab === 'layouts' ? 'active' : ''} to="/layouts">
                    STILI
                </Link>
                <Link className={activeTab === 'cataloghi' ? 'active' : ''} to="/cataloghi">
                    ALIMENTI
                </Link>
                <span className="ms-auto small text-muted-soft">
                    {loading ? 'Permessi in caricamento...' : 'Permessi caricati'}
                </span>
            </nav>

            {!loading && !hasMemberships ? (
                <div className="alert alert-warning mt-3">
                    Non hai strutture attive associate al tuo profilo. Contatta l'amministratore per abilitare
                    l'accesso al Menu Creation Studio.
                </div>
            ) : (
            <Routes>
                <Route path="/" element={<Navigate to={showExecutive ? "/executive" : "/wizard"} replace />} />
                <Route path="/executive" element={<ExecutiveDashboard />} />
                <Route path="/piatti" element={
                    <div className="menu-studio-grid">
                        <div className="p-0 mb-3">
                            <PiattoForm
                                onSuccess={handleSuccess}
                                editingPiatto={editingPiatto}
                                clearEditing={clearEditing}
                            />
                        </div>
                        <PiattoList
                            refreshTrigger={refreshTrigger}
                            onEdit={handleEdit}
                        />
                    </div>
                } />
                <Route path="/layouts" element={<LayoutDashboard />} />
                <Route path="/menu" element={<MenuDashboard />} />
                <Route path="/wizard" element={<MenuWizard />} />
                <Route path="/menu-editor/:menuId" element={<MenuEditor />} />
                <Route path="/layout-editor/:layoutId" element={<LayoutEditor />} />
                <Route path="/cataloghi" element={<CatalogDashboard />} />
            </Routes>
            )}
        </div>
    );
};


const MenuGeneratorStudio = () => {
    return (
        <Router>
            <PermissionsProvider>
                <AppContent />
            </PermissionsProvider>
        </Router>
    );
};


const container = document.getElementById('menu-generator-studio-root');
if (container) {
    const root = createRoot(container);
    root.render(
        <React.StrictMode>
            <MenuGeneratorStudio />
        </React.StrictMode>
    );
}
