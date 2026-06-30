import React, { useState, useEffect } from 'react';
import { getExecutiveDashboard } from '../api';
import { usePermissions } from '../permissions';
import { Link } from 'react-router-dom';

const ExecutiveDashboard = () => {
    const { permissions } = usePermissions();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedCompany, setSelectedCompany] = useState('');

    const isSuperUser = permissions?.is_superuser;
    const isOwner = permissions?.is_owner;

    useEffect(() => {
        const fetchData = async () => {
            if (!(isSuperUser || isOwner)) return;
            setLoading(true);
            try {
                const params = selectedCompany ? { company: selectedCompany } : {};
                const res = await getExecutiveDashboard(params);
                setData(res.data);
            } catch (err) {
                setError('Impossibile caricare i dati della dashboard.');
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [isSuperUser, isOwner, selectedCompany]);

    if (!(isSuperUser || isOwner)) {
        return <div className="alert alert-warning m-4">Accesso riservato a Proprietari e Super Admin.</div>;
    }

    if (loading) return <div className="text-center p-5 animate-pulse text-muted-soft">Caricamento Dashboard Executive...</div>;
    if (error) return <div className="alert alert-danger m-4">{error}</div>;

    return (
        <div className="menu-studio-shell px-4 animate-in">
            <div className="d-flex justify-content-between align-items-center mb-5 flex-wrap gap-4">
                <div>
                    <div className="d-flex align-items-center gap-2 mb-2">
                        <div className="p-2 rounded bg-nuvia-primary bg-opacity-10 text-nuvia-primary">
                            <i className="fas fa-chart-line"></i>
                        </div>
                        <span className="smallest fw-bold text-nuvia-accent uppercase ls-1">Operational Cockpit</span>
                    </div>
                    <h1 className="h3 mb-0 fw-bold text-white ls-tight uppercase">Executive Control Center</h1>
                    <p className="text-muted-soft smallest uppercase fw-bold ls-1 mt-1">Sincronizzazione Real-Time Società: {data?.company_name}</p>
                </div>

                {isSuperUser && permissions.companies?.length > 1 && (
                    <div className="d-flex gap-2">
                        <select
                            className="form-select noir-select py-2 smallest fw-bold border-white border-opacity-10"
                            value={selectedCompany}
                            onChange={(e) => setSelectedCompany(e.target.value)}
                            style={{ minWidth: '220px' }}
                        >
                            <option value="">TUTTE LE SOCIETÀ</option>
                            {permissions.companies.map(c => (
                                <option key={c.id} value={c.id}>{c.name.toUpperCase()}</option>
                            ))}
                        </select>
                    </div>
                )}
            </div>

            <div className="row g-4 mb-5">
                <div className="col-md-4">
                    <div className="glass-card p-4 border-white border-opacity-5 transition-all hover-translate-up text-center">
                        <p className="smallest fw-bold text-muted-soft uppercase ls-1 mb-3">Menu Creati (30gg)</p>
                        <h2 className="display-5 fw-bold text-nuvia-primary ls-tight mb-0">{data?.stats.total_menus_30d}</h2>
                        <div className="tiny text-muted-soft mt-2 uppercase fw-bold ls-1">Record Operativi</div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div className="glass-card p-4 border-white border-opacity-5 transition-all hover-translate-up text-center">
                        <p className="smallest fw-bold text-muted-soft uppercase ls-1 mb-3">Menu Pubblicati (30gg)</p>
                        <h2 className="display-5 fw-bold text-success ls-tight mb-0">{data?.stats.total_published_30d}</h2>
                        <div className="tiny text-muted-soft mt-2 uppercase fw-bold ls-1">Distribuzione Attiva</div>
                    </div>
                </div>
                <div className="col-md-4">
                    <div className="glass-card p-4 border-white border-opacity-5 transition-all hover-translate-up text-center">
                        <p className="smallest fw-bold text-muted-soft uppercase ls-1 mb-3">Export Documenti (30gg)</p>
                        <h2 className="display-5 fw-bold text-info ls-tight mb-0">{data?.stats.total_exports_30d}</h2>
                        <div className="tiny text-muted-soft mt-2 uppercase fw-bold ls-1">Volumi di Stampa</div>
                    </div>
                </div>
            </div>

            <div className="row g-4">
                <div className="col-lg-8">
                    <div className="d-flex align-items-center gap-2 mb-4 px-1">
                        <i className="fas fa-hotel smallest text-nuvia-accent"></i>
                        <h5 className="smallest fw-bold text-white uppercase ls-1 mb-0">Stato Operativo Strutture (Live Tiles)</h5>
                    </div>

                    <div className="row g-3">
                        {data?.structures.map(struct => (
                            <div key={struct.id} className="col-md-6">
                                <div className="glass-card p-4 h-100 d-flex flex-column border-white border-opacity-5 overflow-hidden position-relative">
                                    <div className="d-flex justify-content-between align-items-start mb-4">
                                        <div>
                                            <h6 className="mb-1 fw-bold text-white uppercase ls-tight">{struct.name}</h6>
                                            <span className="tiny-badge bg-white bg-opacity-5 text-muted-soft">REF: {struct.id}</span>
                                        </div>
                                        <div className={`smallest fw-bold px-3 py-1 rounded-pill border ${struct.is_active ? 'bg-success bg-opacity-10 text-success border-success border-opacity-20' : 'bg-danger bg-opacity-10 text-danger border-danger border-opacity-20'}`}>
                                            {struct.is_active ? 'ATTIVA' : 'INATTIVA'}
                                        </div>
                                    </div>

                                    <div className="mt-auto">
                                        <div className="d-flex justify-content-between align-items-center mb-2 pb-2 border-bottom border-white border-opacity-5">
                                            <span className="smallest text-muted-soft uppercase fw-bold">Menu Totali</span>
                                            <span className="smallest fw-bold text-white">{struct.total_menus}</span>
                                        </div>
                                        <div className="d-flex justify-content-between align-items-center mb-4">
                                            <span className="smallest text-muted-soft uppercase fw-bold">Ultimo Accesso</span>
                                            <span className="smallest fw-bold text-white">
                                                {struct.last_activity ? new Date(struct.last_activity).toLocaleDateString() : 'MAI'}
                                            </span>
                                        </div>

                                        {struct.last_menu_name && (
                                            <div className="p-3 rounded-3 bg-white bg-opacity-5 border border-white border-opacity-5 mb-4 animate-in">
                                                <span className="tiny-badge bg-nuvia-primary bg-opacity-10 text-nuvia-primary mb-2">ULTIMO MENU</span>
                                                <span className="smaller fw-bold text-truncate d-block text-white uppercase ls-tight">{struct.last_menu_name}</span>
                                            </div>
                                        )}

                                        <Link to={`/menu?struttura=${struct.id}`} className="btn btn-nuvia-ghost w-100 smallest fw-bold py-2 border-white border-opacity-10">
                                            ACCEDI AL REGISTRO &rarr;
                                        </Link>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="col-lg-4">
                    <div className="d-flex align-items-center gap-2 mb-4 px-1">
                        <i className="fas fa-crown smallest text-nuvia-accent"></i>
                        <h5 className="smallest fw-bold text-white uppercase ls-1 mb-0">Piatti più Richiesti (Top 5)</h5>
                    </div>

                    <div className="glass-card p-4 border-white border-opacity-5 h-100">
                        {data?.top_piatti.map((piatto, idx) => (
                            <div key={piatto.id} className="d-flex align-items-center gap-3 mb-4 last-no-border">
                                <div className="p-2 rounded bg-nuvia-primary bg-opacity-10 text-nuvia-primary smallest fw-bold" style={{ width: '32px', textAlign: 'center' }}>
                                    {idx + 1}
                                </div>
                                <div className="flex-grow-1 overflow-hidden">
                                    <span className="smaller fw-bold d-block text-white text-truncate uppercase ls-tight mb-1">{piatto.nome}</span>
                                    <div className="smallest text-muted-soft uppercase ls-1 fw-bold">
                                        <i className="fas fa-chart-bar me-1 tiny text-nuvia-primary"></i>
                                        {piatto.usage} utilizzi in servizio
                                    </div>
                                </div>
                            </div>
                        ))}
                        {data?.top_piatti.length === 0 && (
                            <div className="text-center py-5 opacity-25">
                                <i className="fas fa-inbox h3 mb-2 d-block"></i>
                                <p className="smallest uppercase fw-bold ls-1 mb-0">Dati non disponibili</p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ExecutiveDashboard;
