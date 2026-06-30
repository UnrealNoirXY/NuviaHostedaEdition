import React, { useState, useEffect, useMemo } from 'react';
import { createMenu, updateMenu } from '../api';
import Modal from 'react-bootstrap/Modal';
import Button from 'react-bootstrap/Button';
import { usePermissions } from '../permissions';

const MenuForm = ({ menu, onClose, onSuccess }) => {
    const { permissions, loading: permissionsLoading } = usePermissions();
    const [formData, setFormData] = useState({
        nome: '',
        data_evento: new Date().toISOString().slice(0, 10),
        turno: 'pranzo',
        struttura: '',
        company: '',
    });

    const companyOptions = useMemo(() => permissions?.companies || [], [permissions]);
    const structureOptions = useMemo(() => {
        let options = permissions?.structures_scope || [];
        if (permissions?.is_superuser) {
            if (formData.company) {
                options = options.filter(s => String(s.company_id) === String(formData.company));
            } else {
                return [];
            }
        } else if (permissions?.is_owner || permissions?.structures?.some(s => s.role === 'Chef')) {
            const userCompanyId = permissions?.companies?.[0]?.id;
            if (userCompanyId) {
                options = options.filter(s => String(s.company_id) === String(userCompanyId));
            }
        }
        return options;
    }, [permissions, formData.company]);

    const structuresWithPermissions = useMemo(() => permissions?.structures || [], [permissions]);
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const selectedStructure = useMemo(() => {
        if (!formData.struttura) return null;
        return structuresWithPermissions.find(
            (structure) => String(structure.id) === String(formData.struttura)
        );
    }, [formData.struttura, structuresWithPermissions]);
    const canEditSelectedStructure = permissions?.is_superuser
        || selectedStructure?.permissions?.can_edit_menus;

    useEffect(() => {
        if (menu) {
            setFormData({
                nome: menu.nome || '',
                data_evento: menu.data_evento ? menu.data_evento.slice(0, 10) : new Date().toISOString().slice(0, 10),
                turno: menu.turno || 'pranzo',
                struttura: menu.struttura || '',
                company: menu.company || '',
            });
        }
    }, [menu]);

    useEffect(() => {
        if (menu) {
            return;
        }
        if (!formData.struttura && structureOptions.length === 1) {
            setFormData((prev) => ({ ...prev, struttura: String(structureOptions[0].id) }));
        }
    }, [formData.struttura, menu, structureOptions]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        try {
            if (!formData.struttura) {
                setError('Seleziona una struttura prima di salvare il menu.');
                return;
            }
            if (!canEditSelectedStructure) {
                setError('Non hai i permessi per creare o modificare menu nella struttura selezionata.');
                return;
            }

            const payload = { ...formData };
            if (!payload.company && formData.struttura) {
                const struct = structureOptions.find(s => String(s.id) === String(formData.struttura));
                if (struct) payload.company = struct.company_id;
            }

            if (menu && menu.id) {
                await updateMenu(menu.id, payload);
            } else {
                await createMenu(payload);
            }
            onSuccess();
        } catch (err) {
            const errorMsg = err.response?.data ? JSON.stringify(err.response.data) : 'Si è verificato un errore.';
            setError(`Salvataggio fallito: ${errorMsg}`);
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Modal show onHide={onClose} backdrop="static" keyboard={false} contentClassName="noir-modal border-white border-opacity-10 rounded-4">
            <Modal.Header closeButton className="border-white border-opacity-5">
                <Modal.Title className="text-white fw-bold ls-tight">
                    {menu ? 'MODIFICA DETTAGLI' : 'NUOVO MENU RAPIDO'}
                </Modal.Title>
            </Modal.Header>
            <Modal.Body className="p-4">
                {error && <div className="alert alert-nuvia-warning smallest fw-bold mb-4">{error}</div>}

                <form id="menu-form" onSubmit={handleSubmit}>
                    {permissions?.is_superuser && !menu && (
                        <div className="mb-4">
                            <label htmlFor="form-company" className="smallest fw-bold text-muted-soft uppercase mb-2">Società / Azienda</label>
                            <select
                                id="form-company"
                                className="form-select noir-select py-2"
                                value={formData.company}
                                onChange={(e) => setFormData(prev => ({ ...prev, company: e.target.value, struttura: '' }))}
                            >
                                <option value="">Seleziona Società...</option>
                                {companyOptions.map((c) => (
                                    <option key={c.id} value={c.id}>{c.name}</option>
                                ))}
                            </select>
                        </div>
                    )}

                    <div className="mb-4">
                        <label htmlFor="nome" className="smallest fw-bold text-muted-soft uppercase mb-2">Titolo del Menu</label>
                        <input
                            type="text"
                            className="form-control noir-input py-2 fw-bold"
                            id="nome"
                            name="nome"
                            value={formData.nome}
                            onChange={handleChange}
                            placeholder="Es. Menu del Giorno"
                            required
                        />
                    </div>

                    <div className="row">
                        <div className="col-md-6 mb-4">
                            <label htmlFor="data_evento" className="smallest fw-bold text-muted-soft uppercase mb-2">Data</label>
                            <input
                                type="date"
                                className="form-control noir-input py-2"
                                id="data_evento"
                                name="data_evento"
                                value={formData.data_evento}
                                onChange={handleChange}
                                required
                            />
                        </div>
                        <div className="col-md-6 mb-4">
                            <label htmlFor="turno" className="smallest fw-bold text-muted-soft uppercase mb-2">Turno</label>
                            <select
                                className="form-select noir-select py-2"
                                id="turno"
                                name="turno"
                                value={formData.turno}
                                onChange={handleChange}
                            >
                                <option value="colazione">Colazione</option>
                                <option value="pranzo">Pranzo</option>
                                <option value="cena">Cena</option>
                                <option value="speciale">Speciale</option>
                            </select>
                        </div>
                    </div>

                    <div className="mb-2">
                        <label htmlFor="struttura" className="smallest fw-bold text-nuvia-accent uppercase mb-2">Struttura di Destinazione</label>
                        <select
                            className="form-select noir-select py-2"
                            id="struttura"
                            name="struttura"
                            value={formData.struttura}
                            onChange={handleChange}
                            disabled={permissionsLoading || (permissions?.is_superuser && !formData.company)}
                            required
                        >
                            {permissions?.is_superuser && !formData.company ? (
                                <option value="">Scegli prima una Società...</option>
                            ) : (
                                <option value="">Seleziona struttura...</option>
                            )}
                            {structureOptions.map((structure) => (
                                <option key={structure.id} value={structure.id}>
                                    {structure.company_name ? `[${structure.company_name}] ` : ''}{structure.name}
                                </option>
                            ))}
                        </select>

                        {formData.struttura && !canEditSelectedStructure && (
                            <div className="tiny text-danger mt-2 fw-bold uppercase">
                                <i className="fas fa-lock me-1"></i> Permessi insufficienti
                            </div>
                        )}
                        {structureOptions.length === 0 && !permissionsLoading && (
                            <div className="tiny text-danger mt-2 fw-bold uppercase">Nessuna struttura disponibile</div>
                        )}
                    </div>
                </form>
            </Modal.Body>
            <Modal.Footer className="border-white border-opacity-5 p-3">
                <button className="btn btn-nuvia-ghost px-4 smallest fw-bold" onClick={onClose} disabled={isLoading}>
                    ANNULLA
                </button>
                <button
                    className="btn btn-nuvia-primary px-4 smallest fw-bold"
                    type="submit"
                    form="menu-form"
                    disabled={isLoading || (!!formData.struttura && !canEditSelectedStructure)}
                >
                    {isLoading ? 'SALVATAGGIO...' : 'CONFERMA E SALVA'}
                </button>
            </Modal.Footer>
        </Modal>
    );
};

export default MenuForm;
