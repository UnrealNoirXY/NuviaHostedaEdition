import React, { useEffect, useState, useMemo } from 'react';
import {
    getMenuVersions,
    getMenuVersionDiff,
    restoreMenuVersion,
    createMenuSnapshot,
} from '../api';
import { toast } from 'react-toastify';

const VersionBadge = ({ label }) => (
    <span className="tiny-badge bg-white bg-opacity-10 text-white border-white border-opacity-10">{label}</span>
);

const VersionDiff = ({ diff, baseLabel, compareLabel, emptyMessage }) => {
    if (!diff) return <div className="text-muted-soft smallest py-3 text-center uppercase ls-1 fw-bold italic opacity-50">{emptyMessage}</div>;

    const hasChanges =
        (diff.changed_fields && diff.changed_fields.length > 0) ||
        (diff.piatti && ((diff.piatti.added || []).length || (diff.piatti.removed || []).length || diff.piatti.order_changed));

    if (!hasChanges) return <div className="smallest text-success bg-success bg-opacity-5 p-3 rounded-3 text-center mt-2 border border-success border-opacity-10 fw-bold">✓ NESSUNA DIFFERENZA RILEVATA</div>;

    return (
        <div className="mt-3 animate-in border-top border-white border-opacity-5 pt-3">
            {diff.changed_fields?.length > 0 && (
                <div className="mb-3">
                    <div className="smallest fw-bold text-nuvia-accent mb-3 uppercase ls-1">Modifiche Strutturali</div>
                    <div className="d-flex flex-column gap-2">
                        {diff.changed_fields.map((change) => (
                            <div key={change.field} className="p-2 rounded bg-white bg-opacity-5 border border-white border-opacity-5">
                                <div className="fw-bold uppercase text-white mb-1" style={{ fontSize: '0.6rem' }}>{change.field.replace('_', ' ')}</div>
                                <div className="d-flex justify-content-between align-items-center">
                                    <span className="tiny text-muted-soft text-decoration-line-through">{String(change.version || '—')}</span>
                                    <i className="fas fa-arrow-right tiny text-nuvia-primary"></i>
                                    <span className="tiny text-white fw-bold">{String(change.current || '—')}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

const MenuVersionHistory = ({ menuId, onRestored }) => {
    const [versions, setVersions] = useState([]);
    const [selectedVersionId, setSelectedVersionId] = useState(null);
    const [compareBaseId, setCompareBaseId] = useState('current');
    const [compareTargetId, setCompareTargetId] = useState(null);
    const [diff, setDiff] = useState(null);
    const [loading, setLoading] = useState(false);
    const [diffLoading, setDiffLoading] = useState(false);

    const sortedVersions = useMemo(() => [...versions].sort((a, b) => new Date(b.creato_il) - new Date(a.creato_il)), [versions]);

    const fetchVersions = async () => {
        setLoading(true);
        try {
            const res = await getMenuVersions(menuId);
            const payload = res.data || [];
            setVersions(payload);
            if (payload.length > 0 && !compareTargetId) setCompareTargetId(payload[0].id);
        } catch (error) {
            toast.error('Impossibile caricare le versioni');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchVersions(); }, [menuId]);

    const handleRestore = async () => {
        if (!selectedVersionId) return;
        try {
            await restoreMenuVersion(menuId, selectedVersionId);
            toast.success('Versione ripristinata');
            setDiff(null);
            setSelectedVersionId(null);
            fetchVersions();
            onRestored?.();
        } catch (error) {
            toast.error('Ripristino fallito');
        }
    };

    const handleSnapshot = async () => {
        try {
            await createMenuSnapshot(menuId);
            toast.success('Snapshot creato');
            fetchVersions();
        } catch (error) {
            toast.error('Errore snapshot');
        }
    };

    useEffect(() => {
        const fetchDiff = async () => {
            if (!compareTargetId || (compareBaseId !== 'current' && compareBaseId === compareTargetId)) {
                setDiff(null);
                return;
            }
            setDiffLoading(true);
            try {
                if (compareBaseId === 'current') {
                    const res = await getMenuVersionDiff(menuId, compareTargetId);
                    setDiff(res.data);
                } else {
                    setDiff(null); // Simple diff for now in UI
                }
            } catch (error) {
                setDiff(null);
            } finally {
                setDiffLoading(false);
            }
        };
        fetchDiff();
    }, [compareBaseId, compareTargetId, menuId]);

    return (
        <div className="d-flex flex-column h-100 overflow-hidden mt-4">
            <div className="d-flex justify-content-between align-items-center mb-3">
                <div className="d-flex align-items-center gap-2">
                    <i className="fas fa-history tiny text-nuvia-accent"></i>
                    <span className="smallest fw-bold text-white uppercase ls-1">Versione & Rollback</span>
                </div>
                <button className="btn btn-nuvia-ghost smallest fw-bold px-3 py-1 border-white border-opacity-10" onClick={handleSnapshot}>
                    <i className="fas fa-camera me-1"></i> SNAPSHOT
                </button>
            </div>

            <div className="flex-grow-1 overflow-hidden d-flex flex-column gap-3">
                <div className="overflow-auto p-1 studio-version-list" style={{ maxHeight: '180px' }}>
                    {loading ? (
                        <div className="text-center py-4 animate-pulse smallest text-muted-soft uppercase fw-bold">Accesso archivio...</div>
                    ) : versions.length === 0 ? (
                        <div className="text-center py-4 text-muted-soft smallest border border-dashed border-white border-opacity-10 rounded-3">Nessuna versione salvata</div>
                    ) : sortedVersions.map((v) => (
                        <div
                            key={v.id}
                            className={`p-3 mb-2 rounded-3 cursor-pointer transition-all d-flex justify-content-between align-items-center border ${selectedVersionId === v.id ? 'bg-nuvia-primary bg-opacity-10 border-nuvia-primary' : 'bg-white bg-opacity-5 border-white border-opacity-5 hover-bg-white-5'}`}
                            onClick={() => {
                                setSelectedVersionId(v.id);
                                setCompareTargetId(v.id);
                            }}
                        >
                            <div className="smallest">
                                <div className="fw-bold text-white uppercase ls-tight">{new Date(v.creato_il).toLocaleDateString()} &bull; {new Date(v.creato_il).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}</div>
                                <div className="text-muted-soft tiny fw-bold uppercase ls-1 mt-1">{v.creato_da_display}</div>
                            </div>
                            <VersionBadge label={`V${v.id}`} />
                        </div>
                    ))}
                </div>

                <div className="p-4 rounded-4 bg-black bg-opacity-30 border border-white border-opacity-5">
                     <div className="d-flex justify-content-between align-items-center mb-3">
                        <div className="smallest fw-bold text-white uppercase ls-1">Analisi Differenze</div>
                        {selectedVersionId && (
                            <button className="btn btn-nuvia-primary smallest py-1 px-4 fw-bold" onClick={handleRestore}>RIPRISTINA ORA</button>
                        )}
                     </div>
                     <div className="overflow-auto" style={{ maxHeight: '150px' }}>
                         {diffLoading ? <div className="text-center py-3 smallest animate-pulse text-muted-soft uppercase fw-bold">Calcolo differenze...</div> : <VersionDiff diff={diff} emptyMessage="Seleziona una versione precedente" />}
                     </div>
                </div>
            </div>
        </div>
    );
};

export default MenuVersionHistory;
