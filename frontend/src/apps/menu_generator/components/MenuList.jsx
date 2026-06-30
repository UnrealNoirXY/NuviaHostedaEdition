import React, { useState, useEffect } from 'react';
import { getMenus, deleteMenu } from '../api';
import { Link } from 'react-router-dom';
import { toast } from 'react-toastify';

const MenuList = ({ onEdit, refreshTrigger }) => {
    const [menus, setMenus] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchMenus = async () => {
        try {
            setLoading(true);
            const response = await getMenus();
            setMenus(response.data);
            setError(null);
        } catch (err) {
            setError('Impossibile caricare l\'elenco dei menu.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchMenus(); }, [refreshTrigger]);

    const handleDelete = async (id) => {
        if (window.confirm('Sei sicuro di voler eliminare questo menu?')) {
            try {
                await deleteMenu(id);
                toast.success('Menu eliminato');
                setMenus(prev => prev.filter(menu => menu.id !== id));
            } catch (err) {
                toast.error('Errore durante l\'eliminazione');
            }
        }
    };

    if (loading) return <div className="text-center py-5 animate-pulse text-muted-soft smallest uppercase ls-1">Sincronizzazione registri...</div>;
    if (error) return <div className="alert alert-danger smaller m-3">{error}</div>;

    return (
        <div className="row g-4">
            {menus.length === 0 ? (
                <div className="col-12 text-center py-5 glass-card bg-opacity-10 border-dashed border-white border-opacity-10 rounded-4">
                    <div className="p-4 rounded-circle bg-white bg-opacity-5 d-inline-block mb-3">
                        <i className="fas fa-file-signature h3 text-muted-soft mb-0"></i>
                    </div>
                    <h5 className="text-white fw-bold">Nessun Registro Servizio</h5>
                    <p className="text-muted-soft smallest uppercase ls-1 mb-4">Inizia dal wizard o utilizza il tasto 'Nuovo Menu'</p>
                    <Link to="/wizard" className="btn btn-nuvia-primary px-4 fw-bold smallest">AVVIA WIZARD ORA</Link>
                </div>
            ) : (
                menus.map((m) => (
                    <div className="col-md-6 col-xl-4" key={m.id}>
                        <div className="glass-card h-100 transition-all hover-translate-up border-white border-opacity-5 overflow-hidden">
                            <div className="p-4 d-flex flex-column h-100">
                                <div className="d-flex justify-content-between align-items-center mb-4">
                                    <div className={`tiny-badge fw-bold px-3 py-1 ${m.is_published ? 'bg-success bg-opacity-10 text-success border border-success border-opacity-20' : 'bg-warning bg-opacity-10 text-warning border border-warning border-opacity-20'}`}>
                                        {m.is_published ? 'PUBBLICATO' : 'IN BOZZA'}
                                    </div>
                                    <span className="smallest text-muted-soft fw-bold ls-1">#{m.id}</span>
                                </div>

                                <h5 className="mb-2 text-white fw-bold ls-tight">{m.nome}</h5>

                                <div className="d-flex flex-column gap-2 mb-4">
                                    <div className="d-flex align-items-center gap-2">
                                        <i className="fas fa-calendar-day tiny text-nuvia-primary"></i>
                                        <span className="smallest text-muted-soft uppercase fw-bold ls-1">
                                            {new Date(m.data_evento).toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric' })}
                                        </span>
                                    </div>
                                    <div className="d-flex align-items-center gap-2">
                                        <i className="fas fa-clock tiny text-nuvia-primary"></i>
                                        <span className="smallest text-muted-soft uppercase fw-bold ls-1">{m.turno}</span>
                                    </div>
                                    {m.struttura_name && (
                                        <div className="d-flex align-items-center gap-2">
                                            <i className="fas fa-hotel tiny text-nuvia-primary"></i>
                                            <span className="smallest text-muted-soft uppercase fw-bold ls-1">{m.struttura_name}</span>
                                        </div>
                                    )}
                                </div>

                                <div className="mt-auto pt-4 border-top border-white border-opacity-10 d-flex gap-2">
                                    <Link to={`/menu-editor/${m.id}`} className="btn btn-nuvia-primary flex-grow-1 smallest py-2 fw-bold">
                                        <i className="fas fa-pencil-alt me-2"></i> STUDIO
                                    </Link>
                                    <div className="btn-group">
                                        <button onClick={() => onEdit(m)} className="btn btn-nuvia-ghost smallest py-2 px-3" title="Modifica Dettagli">
                                            <i className="fas fa-cog"></i>
                                        </button>
                                        <button onClick={() => handleDelete(m.id)} className="btn btn-nuvia-ghost smallest py-2 px-3 text-danger border-danger border-opacity-10" title="Elimina">
                                            <i className="fas fa-trash-alt"></i>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ))
            )}
        </div>
    );
};

export default MenuList;
