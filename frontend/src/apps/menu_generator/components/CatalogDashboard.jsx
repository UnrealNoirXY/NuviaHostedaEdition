import React, { useEffect, useMemo, useState } from 'react';
import {
    createAlimentoBase,
    createAllergene,
    createCavaliere,
    createIngrediente,
    deleteAlimentoBase,
    deleteAllergene,
    deleteCavaliere,
    deleteIngrediente,
    getAllergeni,
    getAlimentiBase,
    getCavalieri,
    getIngredienti,
    getLayouts,
    updateAlimentoBase,
    updateAllergene,
    updateCavaliere,
    updateIngrediente,
} from '../api';
import { usePermissions } from '../permissions';

const CATEGORIE_PIATTI = [
    { value: 'antipasto', label: 'Antipasto' },
    { value: 'primo', label: 'Primo' },
    { value: 'secondo', label: 'Secondo' },
    { value: 'contorno', label: 'Contorno' },
    { value: 'dessert', label: 'Dessert' },
    { value: 'bevanda', label: 'Bevanda' },
    { value: 'altro', label: 'Altro' },
];

const STAGIONALITA = [
    { value: 'annuale', label: 'Tutto l\'anno' },
    { value: 'primavera', label: 'Primavera' },
    { value: 'estate', label: 'Estate' },
    { value: 'autunno', label: 'Autunno' },
    { value: 'inverno', label: 'Inverno' },
];

const SectionCard = ({ title, description, children, icon }) => (
    <div className="glass-card p-4 mb-4 border-white border-opacity-5">
        <div className="d-flex align-items-center gap-3 mb-4 pb-4 border-bottom border-white border-opacity-5">
            <div className="p-3 bg-nuvia-primary bg-opacity-10 rounded-circle text-nuvia-primary" style={{ width: '48px', height: '48px', display: 'grid', placeItems: 'center' }}>
                <i className={`fas ${icon}`}></i>
            </div>
            <div>
                <h3 className="h5 mb-1 text-white fw-bold ls-tight">{title.toUpperCase()}</h3>
                {description && <div className="text-muted-soft smallest uppercase fw-bold ls-1">{description}</div>}
            </div>
        </div>
        {children}
    </div>
);

const AllergeniManager = ({ canManageAllergens }) => {
    const [items, setItems] = useState([]);
    const [formData, setFormData] = useState({ id: null, codice: '', nome: '', icona_svg: '' });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [search, setSearch] = useState('');

    const fetchAll = async () => {
        setLoading(true);
        try {
            const { data } = await getAllergeni(search ? { search } : {});
            setItems(data || []);
        } catch (err) {
            setError('Errore caricamento.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchAll(); }, []);

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            if (formData.id) await updateAllergene(formData.id, formData);
            else await createAllergene(formData);
            setFormData({ id: null, codice: '', nome: '', icona_svg: '' });
            fetchAll();
        } catch (err) { setError('Salvataggio fallito.'); }
    };

    return (
        <SectionCard title="Allergeni" description="Registro ufficiale allergeni" icon="bi-exclamation-octagon">
            {canManageAllergens && (
                <form onSubmit={handleSubmit} className="row g-3 mb-4">
                    <div className="col-md-3">
                        <label className="small-label">Codice</label>
                        <input className="form-control noir-input py-1 smallest" value={formData.codice} onChange={e => setFormData({...formData, codice: e.target.value})} required placeholder="es. glutine" />
                    </div>
                    <div className="col-md-5">
                        <label className="small-label">Nome Visualizzato</label>
                        <input className="form-control noir-input py-1 smallest" value={formData.nome} onChange={e => setFormData({...formData, nome: e.target.value})} required placeholder="es. Glutine" />
                    </div>
                    <div className="col-md-4 d-flex align-items-end gap-2">
                        <button className="btn btn-nuvia-primary flex-grow-1 smallest py-2 fw-bold" type="submit">{formData.id ? 'UPDATE' : 'ADD'}</button>
                        {formData.id && <button className="btn btn-nuvia-ghost smallest py-2" type="button" onClick={() => setFormData({id:null, codice:'', nome:'', icona_svg:''})}><i className="bi bi-x-lg"></i></button>}
                    </div>
                </form>
            )}
            <div className="table-responsive" style={{ maxHeight: '300px' }}>
                <table className="table table-dark table-hover table-modern smallest mb-0">
                    <thead className="sticky-top bg-dark"><tr><th>COD</th><th>NOME</th><th className="text-end">AZIONI</th></tr></thead>
                    <tbody>
                        {items.length === 0 ? (
                            <tr><td colSpan="3" className="text-center py-4 text-muted-soft">Nessun allergene configurato.</td></tr>
                        ) : items.map(i => (
                            <tr key={i.id}>
                                <td className="fw-bold text-nuvia-primary">{i.codice}</td>
                                <td>{i.nome}</td>
                                <td className="text-end">
                                    <button className="btn btn-link smallest text-muted-soft p-0 me-2" onClick={() => setFormData(i)} disabled={!canManageAllergens}>Modifica</button>
                                    <button className="btn btn-link smallest text-danger p-0" onClick={() => { if(window.confirm('Eliminare?')) deleteAllergene(i.id).then(fetchAll) }} disabled={!canManageAllergens}>Elimina</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </SectionCard>
    );
};

const IngredientiManager = ({ canManageAllergens }) => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchAll = async () => {
        setLoading(true);
        try {
            const res = await getIngredienti();
            setItems(res.data || []);
        } catch (err) {} finally { setLoading(false); }
    };

    useEffect(() => { fetchAll(); }, []);

    return (
        <SectionCard title="Ingredienti" description="Anagrafica materie prime" icon="bi-leaf">
             <div className="row g-3" style={{ maxHeight: '420px', overflowY: 'auto' }}>
                {items.length === 0 ? (
                    <div className="col-12 text-center py-5 text-muted-soft smaller">Nessun ingrediente in archivio.</div>
                ) : items.map(i => (
                    <div key={i.id} className="col-md-6">
                        <div className="p-3 rounded-3 bg-white bg-opacity-5 border border-white border-opacity-5 d-flex justify-content-between align-items-center hover-bg-white-5 transition-all">
                            <div>
                                <div className="fw-bold smaller text-white">{i.nome}</div>
                                <div className="smallest text-muted-soft uppercase ls-1">{i.stagionalita}</div>
                            </div>
                            <i className="bi bi-chevron-right smallest opacity-25"></i>
                        </div>
                    </div>
                ))}
             </div>
        </SectionCard>
    );
};

const CatalogDashboard = () => {
    const { permissions } = usePermissions();
    const canManageAllergens = permissions?.aggregate?.can_manage_allergens || permissions?.is_superuser;

    return (
        <div className="menu-studio-shell p-0 animate-in">
             <div className="mb-5 px-3 d-flex justify-content-between align-items-center flex-wrap gap-4">
                <div>
                    <div className="d-flex align-items-center gap-2 mb-2">
                        <div className="p-2 rounded bg-nuvia-primary bg-opacity-10 text-nuvia-primary">
                            <i className="fas fa-database"></i>
                        </div>
                        <span className="smallest fw-bold text-nuvia-accent uppercase ls-1">Archivio Centrale</span>
                    </div>
                    <h2 className="h3 mb-0 fw-bold text-white ls-tight">ANAGRAFICA & MASTER DATA</h2>
                    <p className="text-muted-soft smallest uppercase fw-bold ls-1 mt-1">Sincronizzazione globale degli ingredienti e standard di sicurezza</p>
                </div>
                <div className="d-flex gap-2">
                    <button className="btn btn-nuvia-ghost smallest fw-bold px-4 py-2 border-white border-opacity-10">
                        <i className="fas fa-file-csv me-2"></i> ESPORTA DATI
                    </button>
                </div>
            </div>
            <div className="row px-3 g-4">
                <div className="col-lg-6"><AllergeniManager canManageAllergens={canManageAllergens} /></div>
                <div className="col-lg-6"><IngredientiManager canManageAllergens={canManageAllergens} /></div>
            </div>
        </div>
    );
};

export default CatalogDashboard;
