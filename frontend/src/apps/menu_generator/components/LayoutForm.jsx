import React, { useEffect, useMemo, useState } from 'react';
import { createLayout } from '../api';
import Modal from 'react-bootstrap/Modal';
import Button from 'react-bootstrap/Button';
import { useNavigate } from 'react-router-dom';
import { usePermissions } from '../permissions';

const LayoutForm = ({ onClose, onSuccess }) => {
    const [nome, setNome] = useState('');
    const [companyId, setCompanyId] = useState('');
    const [structureId, setStructureId] = useState('');
    const [error, setError] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const navigate = useNavigate();
    const { permissions, loading: permissionsLoading } = usePermissions();

    const companyOptions = useMemo(() => permissions?.companies || [], [permissions]);
    const structureOptions = useMemo(() => permissions?.structures_scope || [], [permissions]);

    const filteredStructures = useMemo(() => {
        if (!companyId) return structureOptions;
        return structureOptions.filter((structure) => String(structure.company_id) === String(companyId));
    }, [companyId, structureOptions]);

    useEffect(() => {
        if (!companyOptions.length) return;
        if (companyOptions.length === 1) {
            setCompanyId(String(companyOptions[0].id));
        }
    }, [companyOptions]);

    useEffect(() => {
        if (!filteredStructures.length) {
            setStructureId('');
            return;
        }
        if (filteredStructures.length === 1) {
            setStructureId(String(filteredStructures[0].id));
        } else if (
            structureId
            && !filteredStructures.some((structure) => String(structure.id) === String(structureId))
        ) {
            setStructureId('');
        }
    }, [filteredStructures, structureId]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        setError(null);

        const layoutData = {
            nome_layout: nome,
            struttura_blocchi: {
                columns: 1,
                order: { 1: ['logo', 'info', 'sections', 'legend'], 2: [] },
                blocks: {
                    logo: { enabled: true },
                    info: { enabled: true },
                    sections: { enabled: true },
                    legend: { enabled: true }
                }
            }
        };
        if (companyId) {
            layoutData.company = companyId;
        }
        if (structureId) {
            layoutData.struttura = structureId;
        }

        try {
            const response = await createLayout(layoutData);
            onSuccess();
            navigate(`/layout-editor/${response.data.id}`);
        } catch (err) {
            const errorMsg = err.response?.data ? JSON.stringify(err.response.data) : 'Si è verificato un errore.';
            setError(`Creazione fallita: ${errorMsg}`);
            console.error(err);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Modal show onHide={onClose} backdrop="static" contentClassName="noir-modal border-white border-opacity-10 rounded-4" centered>
            <Modal.Header closeButton className="border-white border-opacity-5">
                <Modal.Title className="text-white fw-bold ls-tight">NUOVO TEMPLATE GRAFICO</Modal.Title>
            </Modal.Header>
            <Modal.Body className="p-4">
                {error && <div className="alert alert-nuvia-warning smallest fw-bold mb-4">{error}</div>}

                <form id="layout-form" onSubmit={handleSubmit}>
                    <div className="mb-4">
                        <label htmlFor="layout-company" className="smallest fw-bold text-muted-soft uppercase mb-2">Società / Azienda</label>
                        <select
                            id="layout-company"
                            className="form-select noir-select py-2"
                            value={companyId}
                            onChange={(e) => setCompanyId(e.target.value)}
                            disabled={permissionsLoading}
                            required={companyOptions.length > 1}
                        >
                            {companyOptions.length > 1 && <option value="">Seleziona società...</option>}
                            {companyOptions.map((company) => (
                                <option key={company.id} value={company.id}>
                                    {company.name.toUpperCase()}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="mb-4">
                        <label htmlFor="layout-structure" className="smallest fw-bold text-muted-soft uppercase mb-2">Struttura di Destinazione</label>
                        <select
                            id="layout-structure"
                            className="form-select noir-select py-2"
                            value={structureId}
                            onChange={(e) => setStructureId(e.target.value)}
                            disabled={permissionsLoading}
                            required={filteredStructures.length > 1}
                        >
                            {filteredStructures.length > 1 && <option value="">Seleziona struttura...</option>}
                            {filteredStructures.map((structure) => (
                                <option key={structure.id} value={structure.id}>
                                    {structure.name.toUpperCase()}
                                </option>
                            ))}
                        </select>
                        <div className="tiny text-muted-soft mt-2 uppercase ls-1">Il layout sarà visibile solo ai menu di questa sede.</div>
                    </div>

                    <div className="mb-2">
                        <label htmlFor="nome_layout" className="smallest fw-bold text-muted-soft uppercase mb-2">Nome Identificativo Stile</label>
                        <input
                            type="text"
                            className="form-control noir-input py-2 fw-bold"
                            id="nome_layout"
                            value={nome}
                            onChange={(e) => setNome(e.target.value)}
                            placeholder="Es. GALA NOIR, BISTRO MODERNO"
                            required
                        />
                        <div className="tiny text-nuvia-primary mt-2 fw-bold uppercase ls-1">Accesso al Designer Visuale dopo la creazione.</div>
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
                    form="layout-form"
                    disabled={isLoading}
                >
                    {isLoading ? 'CONFIGURAZIONE...' : 'CREA E APRI DESIGNER'}
                </button>
            </Modal.Footer>
        </Modal>
    );
};

export default LayoutForm;
