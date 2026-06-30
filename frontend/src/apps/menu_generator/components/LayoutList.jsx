import React, { useState, useEffect } from 'react';
import { getLayouts, deleteLayout } from '../api';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';

const LayoutList = ({ onEdit, refreshTrigger }) => {
    const [layouts, setLayouts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchLayouts = async () => {
        try {
            setLoading(true);
            const response = await getLayouts();
            setLayouts(response.data);
            setError(null);
        } catch (err) {
            setError('Impossibile caricare l\'elenco dei layout.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchLayouts();
    }, [refreshTrigger]);

    const handleDelete = async (id) => {
        if (window.confirm('Sei sicuro di voler eliminare questo layout?')) {
            try {
                await deleteLayout(id);
                toast.success('Layout eliminato');
                fetchLayouts();
            } catch (err) {
                toast.error('Errore durante l\'eliminazione');
            }
        }
    };

    if (loading) return <div className="text-center py-5 animate-pulse text-muted-soft">Caricamento designer...</div>;
    if (error) return <div className="alert alert-danger">{error}</div>;

    return (
        <div className="row g-4 mt-2">
            {layouts.length === 0 ? (
                <div className="col-12 text-center py-5 glass-card bg-opacity-10 border-dashed border-white border-opacity-10 rounded-4">
                    <div className="p-4 rounded-circle bg-white bg-opacity-5 d-inline-block mb-3">
                        <i className="fas fa-palette h3 text-muted-soft mb-0"></i>
                    </div>
                    <h5 className="text-white fw-bold">Nessun Layout Grafico</h5>
                    <p className="text-muted-soft smallest uppercase ls-1 mb-0">Crea il tuo primo template per iniziare a stampare</p>
                </div>
            ) : (
                layouts.map((layout) => (
                    <div className="col-md-6 col-xl-4" key={layout.id}>
                        <div className="glass-card h-100 transition-all hover-translate-up border-white border-opacity-5 overflow-hidden">
                            <div className="p-4 d-flex flex-column h-100">
                                <div className="d-flex justify-content-between align-items-center mb-4">
                                    <div className={`tiny-badge fw-bold px-3 py-1 ${layout.is_preset ? 'bg-nuvia-accent bg-opacity-10 text-nuvia-accent border border-nuvia-accent border-opacity-20' : 'bg-white bg-opacity-10 text-white border border-white border-opacity-20'}`}>
                                        {layout.is_preset ? 'PRESET DI SISTEMA' : 'TEMPLATE CUSTOM'}
                                    </div>
                                    <span className="smallest text-muted-soft fw-bold ls-1">v{layout.versione}.0</span>
                                </div>

                                <h5 className="mb-2 text-white fw-bold ls-tight">{layout.nome_layout.toUpperCase()}</h5>

                                <div className="d-flex flex-column gap-2 mb-4">
                                    <div className="d-flex align-items-center gap-2">
                                        <i className="fas fa-clock tiny text-nuvia-primary"></i>
                                        <span className="smallest text-muted-soft uppercase fw-bold ls-1">
                                            Aggiornato il {new Date(layout.data_modifica).toLocaleDateString()}
                                        </span>
                                    </div>
                                    {layout.font_principale && (
                                        <div className="d-flex align-items-center gap-2">
                                            <i className="fas fa-font tiny text-nuvia-primary"></i>
                                            <span className="smallest text-muted-soft uppercase fw-bold ls-1">{layout.font_principale}</span>
                                        </div>
                                    )}
                                </div>

                                <div className="mt-auto pt-4 border-top border-white border-opacity-10 d-flex gap-2">
                                    <Link to={`/layout-editor/${layout.id}`} className="btn btn-nuvia-primary flex-grow-1 smallest py-2 fw-bold">
                                        <i className="fas fa-pen-nib me-2"></i> APRI DESIGNER
                                    </Link>
                                    {!layout.is_preset && (
                                        <button onClick={() => handleDelete(layout.id)} className="btn btn-nuvia-ghost smallest py-2 px-3 text-danger border-danger border-opacity-10" title="Elimina">
                                            <i className="fas fa-trash-alt"></i>
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                ))
            )}
        </div>
    );
};

export default LayoutList;
