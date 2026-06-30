import React, { useState, useEffect } from 'react';
import { getPiatti, deletePiatto } from '../api';

const PiattoList = ({ refreshTrigger, onEdit }) => {
    const [piatti, setPiatti] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedRow, setExpandedRow] = useState(null);

    const fetchPiatti = async () => {
        try {
            setLoading(true);
            const response = await getPiatti({ detailed: true }); // Assume backend can provide detailed response
            setPiatti(response.data);
            setError(null);
        } catch (err) {
            setError('Impossibile caricare l\'elenco dei piatti.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPiatti();
    }, [refreshTrigger]);

    const handleDelete = async (id) => {
        if (window.confirm('Sei sicuro di voler eliminare questo piatto?')) {
            try {
                await deletePiatto(id);
                fetchPiatti(); // Refresh the list
            } catch (err) {
                setError('Errore durante l\'eliminazione del piatto.');
                console.error(err);
            }
        }
    };

    const toggleRow = (id) => {
        setExpandedRow(expandedRow === id ? null : id);
    };

    if (loading) return <div className="text-center py-5 animate-pulse text-muted-soft smallest fw-bold uppercase ls-1">Caricamento Ricettario...</div>;
    if (error) return <div className="alert alert-nuvia-warning m-3 smallest fw-bold uppercase ls-1">{error}</div>;

    return (
        <div className="glass-card border-white border-opacity-5 overflow-hidden">
            <div className="p-4 border-bottom border-white border-opacity-5 bg-white bg-opacity-5">
                <div className="d-flex align-items-center gap-2">
                    <i className="fas fa-utensils text-nuvia-accent"></i>
                    <h5 className="mb-0 fw-bold text-white ls-tight uppercase">Catalogo Portate</h5>
                </div>
            </div>

            <div className="p-0">
                {piatti.length === 0 ? (
                    <div className="text-center py-5 opacity-50">
                        <i className="fas fa-folder-open h2 mb-3 d-block"></i>
                        <p className="smallest uppercase ls-1 fw-bold">Nessun piatto registrato.</p>
                    </div>
                ) : (
                    <div className="table-responsive">
                        <table className="table table-dark table-hover table-modern mb-0">
                            <thead className="bg-black bg-opacity-50">
                                <tr>
                                    <th className="ps-4 py-3 smallest fw-bold text-muted-soft uppercase ls-1">Stato</th>
                                    <th className="py-3 smallest fw-bold text-muted-soft uppercase ls-1">Dettagli Portata</th>
                                    <th className="py-3 smallest fw-bold text-muted-soft uppercase ls-1">Categoria</th>
                                    <th className="py-3 smallest fw-bold text-muted-soft uppercase ls-1">Prezzo</th>
                                    <th className="pe-4 py-3 smallest fw-bold text-muted-soft uppercase ls-1 text-end">Operazioni</th>
                                </tr>
                            </thead>
                            <tbody>
                                {piatti.map((piatto) => (
                                    <React.Fragment key={piatto.id}>
                                        <tr className="align-middle border-bottom border-white border-opacity-5">
                                            <td className="ps-4">
                                                <button className={`btn btn-sm p-2 rounded-circle border-0 ${expandedRow === piatto.id ? 'bg-nuvia-primary text-white' : 'bg-white bg-opacity-10 text-muted-soft'}`} onClick={() => toggleRow(piatto.id)}>
                                                    <i className={`fas ${expandedRow === piatto.id ? 'fa-minus' : 'fa-plus'} tiny`}></i>
                                                </button>
                                            </td>
                                            <td>
                                                <div className="d-flex align-items-center gap-3">
                                                    {piatto.immagine && <img src={piatto.immagine} alt="" className="rounded-2 border border-white border-opacity-10" style={{ width: '40px', height: '40px', objectFit: 'cover' }} />}
                                                    <span className="smaller fw-bold text-white uppercase ls-tight">{piatto.nome}</span>
                                                </div>
                                            </td>
                                            <td>
                                                <span className="tiny-badge bg-white bg-opacity-5 text-muted-soft border-white border-opacity-10">{piatto.categoria_display?.toUpperCase()}</span>
                                            </td>
                                            <td>
                                                <span className="smaller fw-bold text-nuvia-accent">{piatto.prezzo ? `${piatto.prezzo} €` : '—'}</span>
                                            </td>
                                            <td className="pe-4 text-end">
                                                <button onClick={() => onEdit(piatto)} className="btn btn-nuvia-ghost smallest py-1 px-3 me-2 border-white border-opacity-10 fw-bold">MODIFICA</button>
                                                <button onClick={() => handleDelete(piatto.id)} className="btn btn-nuvia-ghost smallest py-1 px-3 text-danger border-danger border-opacity-10 fw-bold">ELIMINA</button>
                                            </td>
                                        </tr>
                                        {expandedRow === piatto.id && (
                                            <tr>
                                                <td colSpan="5" className="p-0 border-0">
                                                    <div className="p-4 bg-black bg-opacity-40 animate-in">
                                                        <div className="row g-4">
                                                            <div className="col-md-4">
                                                                <h6 className="smallest fw-bold text-nuvia-accent uppercase ls-1 mb-3">Scheda Tecnica</h6>
                                                                {piatto.immagine ? (
                                                                    <img src={piatto.immagine} alt={piatto.nome} className="img-fluid rounded-4 border border-white border-opacity-10 shadow-lg mb-3" />
                                                                ) : (
                                                                    <div className="p-5 bg-white bg-opacity-5 border border-dashed border-white border-opacity-10 rounded-4 text-center mb-3">
                                                                        <i className="fas fa-camera h3 opacity-10"></i>
                                                                    </div>
                                                                )}
                                                            </div>
                                                            <div className="col-md-8">
                                                                <div className="mb-4">
                                                                    <h6 className="smallest fw-bold text-muted-soft uppercase ls-1 mb-2">Descrizione Gastronomica</h6>
                                                                    <p className="smaller text-white opacity-75 lh-base mb-0">{piatto.descrizione || 'Nessuna descrizione disponibile.'}</p>
                                                                </div>

                                                                <div className="row g-4">
                                                                    <div className="col-md-6">
                                                                        <h6 className="smallest fw-bold text-muted-soft uppercase ls-1 mb-3">Ingredienti</h6>
                                                                        <div className="d-flex flex-wrap gap-1">
                                                                            {piatto.ingredienti?.length > 0 ? (
                                                                                piatto.ingredienti.map(ing => <span key={ing.id} className="tiny-badge bg-white bg-opacity-10 text-white border-0">{ing.nome.toUpperCase()}</span>)
                                                                            ) : <span className="tiny text-muted-soft">Non specificati</span>}
                                                                        </div>
                                                                    </div>
                                                                    <div className="col-md-6">
                                                                        <h6 className="smallest fw-bold text-muted-soft uppercase ls-1 mb-3">Sicurezza Allergeni</h6>
                                                                        <div className="d-flex flex-wrap gap-1">
                                                                            {piatto.allergeni?.length > 0 ? (
                                                                                piatto.allergeni.map(al => <span key={al.id} className="tiny-badge bg-warning bg-opacity-20 text-warning border-warning border-opacity-20">{al.nome.toUpperCase()}</span>)
                                                                            ) : <span className="tiny text-success fw-bold uppercase">Allergen-Free</span>}
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                    </React.Fragment>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default PiattoList;
