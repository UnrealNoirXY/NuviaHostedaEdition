import React, { useState, useEffect, useMemo } from 'react';
import { createPiatto, updatePiatto, getIngredienti, getAllergeni } from '../api';
import AsyncSelect from 'react-select/async';
import { usePermissions } from '../permissions';

const PiattoForm = ({ onSuccess, editingPiatto, clearEditing }) => {
    const { permissions } = usePermissions();
    const canEditDishes = permissions?.aggregate?.can_edit_dishes || permissions?.is_superuser;

    const [formData, setFormData] = useState({
        id: null,
        nome: '',
        descrizione: '',
        categoria: 'antipasto',
        prezzo: '',
        composizione: [], // [{ ingrediente_id, label, quantita, unita, scarto, costo_unitario }]
        allergeni: [],
        base_item: null,
        immagine: null,
    });
    const [allAllergeni, setAllAllergeni] = useState([]);
    const [error, setError] = useState(null);

    // Fetch global data on component mount
    useEffect(() => {
        const fetchGlobalData = async () => {
            try {
                const allergeniRes = await getAllergeni();
                setAllAllergeni(allergeniRes.data);
            } catch (err) {
                console.error("Failed to fetch global data:", err);
            }
        };
        fetchGlobalData();
    }, []);

    // Effect to populate form when editingPiatto changes
    const normalizeSelectItems = (items = []) => items.map((item) => {
        if (item === null || item === undefined) return null;
        if (typeof item === 'string' || typeof item === 'number') {
            return {
                id: item,
                value: item,
                label: String(item),
            };
        }
        return {
            ...item,
            label: item.label || item.nome,
            value: item.value || item.id,
        };
    }).filter(Boolean);

    const [alimentiBase, setAlimentiBase] = useState([]);
    const [immaginePreview, setImmaginePreview] = useState(null);

    useEffect(() => {
        if (editingPiatto) {
            setFormData({
                id: editingPiatto.id,
                nome: editingPiatto.nome || '',
                descrizione: editingPiatto.descrizione || '',
                categoria: editingPiatto.categoria || 'antipasto',
                prezzo: editingPiatto.prezzo || '',
                composizione: (editingPiatto.composizione_details || []).map(c => ({
                    ingrediente_id: c.ingrediente,
                    label: c.ingrediente_nome,
                    quantita: c.quantita,
                    unita: c.unita_misura,
                    scarto: c.scarto_percentuale,
                    costo_teorico: c.costo_teorico
                })),
                allergeni: normalizeSelectItems(editingPiatto.allergeni_details || editingPiatto.allergeni || []),
                base_item: editingPiatto.base_item || null,
                immagine: null,
            });
            setImmaginePreview(editingPiatto.immagine || null);
        } else {
            resetForm();
        }
    }, [editingPiatto]);

    const resetForm = () => {
        setFormData({
            id: null,
            nome: '',
            descrizione: '',
            categoria: 'antipasto',
            prezzo: '',
            composizione: [],
            allergeni: [],
            base_item: null,
            immagine: null,
        });
        setImmaginePreview(null);
        setError(null);
    };

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleAddIngrediente = (ing) => {
        if (formData.composizione.find(c => c.ingrediente_id === ing.id)) return;
        setFormData(prev => ({
            ...prev,
            composizione: [...prev.composizione, {
                ingrediente_id: ing.id,
                label: ing.nome,
                quantita: 100,
                unita: 'g',
                scarto: 0,
                costo_unitario: ing.economato_item_details?.last_purchase_price || 0,
                allergeni: ing.allergeni || []
            }]
        }));
    };

    const updateComposizione = (index, changes) => {
        setFormData(prev => {
            const next = [...prev.composizione];
            next[index] = { ...next[index], ...changes };
            return { ...prev, composizione: next };
        });
    };

    const removeComposizione = (index) => {
        setFormData(prev => ({
            ...prev,
            composizione: prev.composizione.filter((_, i) => i !== index)
        }));
    };

    const handleAllergeniChange = (selectedOptions) => {
        setFormData(prev => ({ ...prev, allergeni: selectedOptions || [] }));
    };

    // Memoized calculation of allergens based on selected ingredients
    const derivedAllergeni = useMemo(() => {
        const allergeniIds = new Set();
        formData.composizione.forEach(ing => {
            (ing.allergeni || []).forEach(id => allergeniIds.add(id));
        });
        return allAllergeni.filter(allergene => allergeniIds.has(allergene.id));
    }, [formData.composizione, allAllergeni]);

    const combinedAllergeni = useMemo(() => {
        const combined = new Map();
        derivedAllergeni.forEach((allergene) => combined.set(allergene.id, allergene));
        formData.allergeni.forEach((allergene) => combined.set(allergene.id, allergene));
        return Array.from(combined.values());
    }, [derivedAllergeni, formData.allergeni]);

    const liveFoodCost = useMemo(() => {
        return formData.composizione.reduce((total, c) => {
            let qty = parseFloat(c.quantita) || 0;
            if (c.unita === 'g' || c.unita === 'ml') qty /= 1000;
            const yieldFactor = c.scarto < 100 ? 1 / (1 - (c.scarto / 100)) : 1;
            return total + (qty * (parseFloat(c.costo_unitario) || 0) * yieldFactor);
        }, 0);
    }, [formData.composizione]);

    const liveMargin = useMemo(() => {
        const price = parseFloat(formData.prezzo) || 0;
        if (price <= 0) return 0;
        return ((price - liveFoodCost) / price) * 100;
    }, [liveFoodCost, formData.prezzo]);

    // Async function to load ingredients for react-select
    const loadIngredienti = async (inputValue) => {
        try {
            const res = await getIngredienti({ search: inputValue });
            return res.data.map(ing => ({
                ...ing,
                label: ing.nome,
                value: ing.id,
            }));
        } catch (err) {
            console.error("Failed to load ingredients:", err);
            return [];
        }
    };

    const loadAllergeni = async (inputValue) => {
        try {
            const res = await getAllergeni({ search: inputValue });
            return res.data.map((al) => ({
                ...al,
                label: al.nome,
                value: al.id,
            }));
        } catch (err) {
            console.error("Failed to load allergens:", err);
            return [];
        }
    };

    const handleBaseItemChange = async (e) => {
        const baseId = e.target.value;
        if (!baseId) {
            setFormData(prev => ({ ...prev, base_item: null }));
            return;
        }

        const base = alimentiBase.find(b => String(b.id) === String(baseId));
        if (base) {
            setFormData(prev => ({
                ...prev,
                base_item: base.id,
                nome: prev.nome || base.nome,
                descrizione: prev.descrizione || base.descrizione,
                categoria: base.categoria,
                ingredienti: normalizeSelectItems(base.ingredienti_details || []),
                allergeni: normalizeSelectItems(base.allergeni_details || []),
            }));
        }
    };

    useEffect(() => {
        const fetchAlimentiBase = async () => {
            try {
                const { data } = await getAlimentiBase();
                setAlimentiBase(data || []);
            } catch (err) {
                console.error("Failed to fetch alimenti base", err);
            }
        };
        fetchAlimentiBase();
    }, []);

    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setFormData(prev => ({ ...prev, immagine: file }));
            setImmaginePreview(URL.createObjectURL(file));
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        if (!canEditDishes) {
            setError('Non hai i permessi per salvare i piatti.');
            return;
        }

        const data = new FormData();
        data.append('nome', formData.nome);
        data.append('descrizione', formData.descrizione);
        data.append('categoria', formData.categoria);
        if (formData.prezzo) data.append('prezzo', formData.prezzo);
        if (formData.base_item) data.append('base_item', formData.base_item);
        if (formData.immagine) data.append('immagine', formData.immagine);

        // Composizione come JSON string per il backend
        const composizioneInput = formData.composizione.map(c => ({
            ingrediente_id: c.ingrediente_id,
            quantita: c.quantita,
            unita_misura: c.unita,
            scarto_percentuale: c.scarto
        }));
        data.append('composizione_input', JSON.stringify(composizioneInput));

        combinedAllergeni.forEach(al => data.append('allergeni_ids', al.id));

        try {
            if (formData.id) {
                await updatePiatto(formData.id, data);
            } else {
                await createPiatto(data);
            }
            onSuccess();
            clearEditing();
        } catch (err) {
            const errorMsg = err.response?.data ? JSON.stringify(err.response.data) : `Si è verificato un errore.`;
            setError(`Salvataggio fallito: ${errorMsg}`);
            console.error(err);
        }
    };

    const customAsyncSelectStyles = {
        control: (base) => ({
            ...base,
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            borderColor: 'rgba(255, 255, 255, 0.15)',
            borderRadius: '14px',
            padding: '4px',
            color: '#fff'
        }),
        menu: (base) => ({
            ...base,
            backgroundColor: '#0f172a',
            border: '1px solid rgba(255, 255, 255, 0.1)'
        }),
        option: (base, state) => ({
            ...base,
            backgroundColor: state.isFocused ? '#38bdf8' : 'transparent',
            color: state.isFocused ? '#000' : '#fff'
        }),
        multiValue: (base) => ({
            ...base,
            backgroundColor: 'rgba(56, 189, 248, 0.15)',
            borderRadius: '6px',
        }),
        multiValueLabel: (base) => ({
            ...base,
            color: '#38bdf8',
            fontWeight: 'bold',
            fontSize: '0.75rem'
        }),
        multiValueRemove: (base) => ({
            ...base,
            color: '#38bdf8',
            ':hover': {
                backgroundColor: '#38bdf8',
                color: '#000',
            },
        }),
    };

    return (
        <div className="glass-card p-4 border-white border-opacity-5 position-sticky" style={{ top: '20px' }}>
            <div className="d-flex align-items-center gap-2 mb-4 pb-3 border-bottom border-white border-opacity-5">
                <div className="p-2 rounded bg-nuvia-primary bg-opacity-10 text-nuvia-primary">
                    <i className={`fas ${formData.id ? 'fa-pen-nib' : 'fa-plus-circle'}`}></i>
                </div>
                <h5 className="mb-0 fw-bold text-white ls-tight">{formData.id ? 'REVISIONE PIATTO' : 'NUOVA RICETTA'}</h5>
            </div>

            <form onSubmit={handleSubmit}>
                {error && <div className="alert alert-nuvia-warning smallest fw-bold mb-4">{error}</div>}

                {!canEditDishes && (
                    <div className="p-3 rounded-3 bg-warning bg-opacity-10 border border-warning border-opacity-10 mb-4 animate-in">
                        <p className="smallest text-warning fw-bold uppercase ls-1 mb-0">
                            <i className="fas fa-lock me-2"></i> Modalità Sola Lettura
                        </p>
                    </div>
                )}

                <div className="mb-4">
                    <label htmlFor="base_item" className="smallest fw-bold text-muted-soft uppercase mb-2">Importa da Alimento Base</label>
                    <select
                        className="form-select noir-select py-2 smallest"
                        id="base_item"
                        value={formData.base_item || ''}
                        onChange={handleBaseItemChange}
                        disabled={!canEditDishes}
                    >
                        <option value="">Seleziona Catalogo...</option>
                        {alimentiBase.map(base => (
                            <option key={base.id} value={base.id}>{base.nome.toUpperCase()}</option>
                        ))}
                    </select>
                </div>

                <div className="mb-4">
                    <label htmlFor="nome" className="smallest fw-bold text-muted-soft uppercase mb-2">Nome della Portata</label>
                    <input
                        type="text"
                        className="form-control noir-input py-2 fw-bold"
                        id="nome"
                        name="nome"
                        value={formData.nome}
                        onChange={handleInputChange}
                        required
                        disabled={!canEditDishes}
                    />
                </div>

                <div className="mb-4">
                    <label className="smallest fw-bold text-muted-soft uppercase mb-2">Media & Visual</label>
                    <div className="p-3 rounded-4 border border-dashed border-white border-opacity-10 bg-white bg-opacity-5 text-center">
                        {immaginePreview ? (
                            <div className="position-relative d-inline-block">
                                <img src={immaginePreview} alt="Preview" style={{ maxWidth: '100%', maxHeight: '120px', borderRadius: '12px' }} className="shadow-lg" />
                                <button type="button" className="btn btn-dark btn-sm position-absolute top-0 end-0 rounded-circle m-1 shadow" onClick={() => {setFormData({...formData, immagine: null}); setImmaginePreview(null)}}>
                                    <i className="fas fa-times"></i>
                                </button>
                            </div>
                        ) : (
                            <div className="py-3">
                                <i className="fas fa-camera h3 text-muted-soft opacity-25 mb-2 d-block"></i>
                                <label htmlFor="immagine" className="btn btn-nuvia-ghost smallest fw-bold cursor-pointer">CARICA FOTO</label>
                            </div>
                        )}
                        <input type="file" className="d-none" id="immagine" accept="image/*" onChange={handleFileChange} disabled={!canEditDishes} />
                    </div>
                </div>

                <div className="mb-4">
                    <label htmlFor="descrizione" className="smallest fw-bold text-muted-soft uppercase mb-2">Descrizione in Menu</label>
                    <textarea
                        className="form-control noir-input smallest"
                        id="descrizione"
                        name="descrizione"
                        rows="3"
                        value={formData.descrizione}
                        onChange={handleInputChange}
                        disabled={!canEditDishes}
                        placeholder="Es: Pasta trafilata al bronzo con pomodoro San Marzano..."
                    ></textarea>
                </div>

                <div className="row">
                    <div className="col-md-6 mb-4">
                        <label htmlFor="categoria" className="smallest fw-bold text-muted-soft uppercase mb-2">Categoria</label>
                        <select
                            className="form-select noir-select py-2 smallest"
                            id="categoria"
                            name="categoria"
                            value={formData.categoria}
                            onChange={handleInputChange}
                            disabled={!canEditDishes}
                        >
                            {/* Categories... */}
                            <option value="antipasto">ANTIPASTO</option>
                            <option value="primo">PRIMO</option>
                            <option value="secondo">SECONDO</option>
                            <option value="contorno">CONTORNO</option>
                            <option value="dessert">DESSERT</option>
                            <option value="bevanda">BEVANDA</option>
                            <option value="altro">ALTRO</option>
                        </select>
                    </div>
                    <div className="col-md-6 mb-4">
                        <label htmlFor="prezzo" className="smallest fw-bold text-muted-soft uppercase mb-2">Prezzo (€)</label>
                        <input
                            type="number"
                            className="form-control noir-input py-2 fw-bold"
                            id="prezzo"
                            name="prezzo"
                            value={formData.prezzo}
                            onChange={handleInputChange}
                            step="0.01"
                            disabled={!canEditDishes}
                        />
                    </div>
                </div>

                <div className="mb-4">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                        <label className="smallest fw-bold text-muted-soft uppercase">Ricetta Tecnica (Engineering)</label>
                        <span className={`tiny-badge ${liveMargin < 65 ? 'bg-danger' : 'bg-success'} text-white`}>
                            Margine: {liveMargin.toFixed(1)}%
                        </span>
                    </div>

                    <div className="composizione-list mb-3">
                        {formData.composizione.map((c, idx) => (
                            <div key={idx} className="p-3 rounded-3 bg-white bg-opacity-5 border border-white border-opacity-10 mb-2 animate-in">
                                <div className="d-flex justify-content-between align-items-start mb-2">
                                    <span className="smallest fw-bold text-white uppercase">{c.label}</span>
                                    <button type="button" className="btn btn-link text-danger p-0 smallest" onClick={() => removeComposizione(idx)}>
                                        <i className="fas fa-trash"></i>
                                    </button>
                                </div>
                                <div className="row g-2">
                                    <div className="col-4">
                                        <label className="tiny text-muted-soft">Peso/Dose</label>
                                        <input type="number" className="form-control form-control-sm noir-input py-1 smallest" value={c.quantita} onChange={e => updateComposizione(idx, { quantita: e.target.value })} />
                                    </div>
                                    <div className="col-3">
                                        <label className="tiny text-muted-soft">U.M.</label>
                                        <select className="form-select form-select-sm noir-select py-1 smallest" value={c.unita} onChange={e => updateComposizione(idx, { unita: e.target.value })}>
                                            <option value="g">g</option>
                                            <option value="kg">kg</option>
                                            <option value="ml">ml</option>
                                            <option value="lt">lt</option>
                                            <option value="pz">pz</option>
                                        </select>
                                    </div>
                                    <div className="col-3">
                                        <label className="tiny text-muted-soft">Scarto %</label>
                                        <input type="number" className="form-control form-control-sm noir-input py-1 smallest" value={c.scarto} onChange={e => updateComposizione(idx, { scarto: e.target.value })} />
                                    </div>
                                    <div className="col-2 text-end">
                                        <label className="tiny text-muted-soft">Costo</label>
                                        <div className="smallest fw-bold text-nuvia-accent">
                                            €{(c.costo_teorico !== undefined ? parseFloat(c.costo_teorico) : (() => {
                                                let qty = parseFloat(c.quantita) || 0;
                                                if (c.unita === 'g' || c.unita === 'ml') qty /= 1000;
                                                const yieldFactor = c.scarto < 100 ? 1 / (1 - (c.scarto / 100)) : 1;
                                                return qty * (parseFloat(c.costo_unitario) || 0) * yieldFactor;
                                            })()).toFixed(2)}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    <AsyncSelect
                        styles={customAsyncSelectStyles}
                        cacheOptions
                        defaultOptions
                        isDisabled={!canEditDishes}
                        loadOptions={loadIngredienti}
                        onChange={handleAddIngrediente}
                        placeholder="Aggiungi ingrediente alla ricetta..."
                        value={null}
                    />
                </div>

                <div className="p-3 rounded-4 bg-nuvia-primary bg-opacity-10 border border-nuvia-primary border-opacity-20 mb-4 d-flex justify-content-between align-items-center">
                    <div>
                        <span className="smallest fw-bold text-muted-soft uppercase d-block">Food Cost Teorico</span>
                        <h4 className="mb-0 fw-bold text-white">€ {liveFoodCost.toFixed(2)}</h4>
                    </div>
                    <div className="text-end">
                        <span className="smallest fw-bold text-muted-soft uppercase d-block">Incidenza %</span>
                        <h4 className={`mb-0 fw-bold ${liveMargin < 65 ? 'text-danger' : 'text-success'}`}>
                            {liveMargin > 0 ? (liveFoodCost / (parseFloat(formData.prezzo) || 1) * 100).toFixed(1) : 0}%
                        </h4>
                    </div>
                </div>

                <div className="mb-4">
                    <label className="smallest fw-bold text-muted-soft uppercase mb-2">Sicurezza Alimentare (Allergeni)</label>
                    <div className="p-3 rounded-4 bg-black bg-opacity-30 border border-white border-opacity-5 mb-3">
                        <span className="smallest fw-bold text-muted-soft uppercase ls-1 mb-2 d-block">Tracciamento Combinato:</span>
                        <div className="d-flex flex-wrap gap-1">
                            {combinedAllergeni.length > 0
                                ? combinedAllergeni.map(al => (
                                      <span key={al.id} className="px-2 py-1 rounded bg-warning bg-opacity-10 text-warning border border-warning border-opacity-20 tiny fw-bold uppercase">
                                          {al.nome}
                                      </span>
                                  ))
                                : <span className="tiny text-muted-soft italic">Nessun allergene rilevato.</span>
                            }
                        </div>
                    </div>
                    <AsyncSelect
                        styles={customAsyncSelectStyles}
                        isMulti
                        cacheOptions
                        defaultOptions
                        isDisabled={!canEditDishes}
                        loadOptions={loadAllergeni}
                        value={formData.allergeni}
                        onChange={handleAllergeniChange}
                        placeholder="Aggiungi allergeni extra..."
                    />
                </div>

                <div className="pt-3 d-flex gap-2">
                    <button type="submit" className="btn btn-nuvia-primary flex-grow-1 smallest fw-bold" disabled={!canEditDishes}>
                        {formData.id ? 'AGGIORNA SCHEDA' : 'SALVA RICETTA'}
                    </button>
                    {formData.id && (
                        <button type="button" onClick={clearEditing} className="btn btn-nuvia-ghost px-4 smallest fw-bold">
                            ANNULLA
                        </button>
                    )}
                </div>
            </form>
        </div>
    );
};

export default PiattoForm;
