import React from 'react';

const InsightBadge = ({ label, value, tone = 'primary' }) => {
    const toneMap = {
        primary: 'bg-nuvia-primary bg-opacity-10 text-nuvia-primary border-nuvia-primary border-opacity-20',
        danger: 'bg-danger bg-opacity-10 text-danger border-danger border-opacity-20',
        info: 'bg-info bg-opacity-10 text-info border-info border-opacity-20',
        success: 'bg-success bg-opacity-10 text-success border-success border-opacity-20',
        warning: 'bg-warning bg-opacity-10 text-warning border-warning border-opacity-20',
    };
    return (
        <span className={`px-2 py-1 rounded border smallest fw-bold uppercase ls-1 me-2 mb-2 d-inline-block ${toneMap[tone] || toneMap.primary}`}>
            {label}{value ? ` · ${value}` : ''}
        </span>
    );
};

const MenuInsights = ({ insights, loading, error, onRefresh }) => {
    const allergenSummary = insights?.allergeni?.summary || [];
    const missingAllergens = insights?.allergeni?.missing_allergeni || [];
    const highFrequency = insights?.allergeni?.high_frequency || [];
    const seasonalityIssues = insights?.stagionalita?.fuori_stagione || [];
    const suggestions = insights?.suggestions || [];
    const finanza = insights?.finanza;
    const currentSeason = insights?.stagionalita?.stagione_corrente;
    const inSeasonRatio = insights?.stagionalita?.in_season_ratio;
    const seasonalIngredients = insights?.stagionalita?.ingredienti_stagionali || [];

    return (
        <div className="d-flex flex-column h-100 overflow-hidden">
            <div className="d-flex justify-content-between align-items-center mb-4">
                <div className="d-flex align-items-center gap-2">
                    <i className="fas fa-brain tiny text-nuvia-accent"></i>
                    <span className="smallest fw-bold text-white uppercase ls-1">Analisi A.I.D.A.</span>
                </div>
                <button className="btn btn-nuvia-ghost smallest fw-bold px-3 py-1 border-white border-opacity-10" onClick={onRefresh} disabled={loading}>
                    {loading ? 'ANALISI...' : 'AGGIORNA'}
                </button>
            </div>

            <div className="flex-grow-1 overflow-auto pe-1">
                {error && <div className="alert alert-nuvia-warning smallest fw-bold mb-4">{error}</div>}

                {!loading && !insights && !error && (
                    <div className="text-center py-5 opacity-25">
                        <i className="fas fa-microchip h3 mb-2 d-block"></i>
                        <p className="smallest uppercase fw-bold ls-1 mb-0">Nessun Insight</p>
                    </div>
                )}

                {finanza && (
                    <section className="mb-5 animate-in">
                         <div className="d-flex justify-content-between align-items-center mb-3">
                            <h6 className="smallest fw-bold text-nuvia-accent uppercase ls-1 mb-0">Theoretical Food Cost</h6>
                            <span className={`tiny-badge ${finanza.margine_percentuale < 65 ? 'bg-danger' : 'bg-success'} text-white`}>
                                Margine: {finanza.margine_percentuale}%
                            </span>
                        </div>
                        <div className="glass-card p-3 border-white border-opacity-5 mb-3">
                            <div className="d-flex justify-content-between mb-2">
                                <span className="smallest text-muted-soft uppercase">Costo Totale Menu</span>
                                <span className="smaller fw-bold text-white">€ {finanza.food_cost_totale}</span>
                            </div>
                            <div className="d-flex justify-content-between">
                                <span className="smallest text-muted-soft uppercase">Ricavo Previsto</span>
                                <span className="smaller fw-bold text-white">€ {finanza.ricavo_teorico}</span>
                            </div>
                        </div>

                        {finanza.piatti_critici.length > 0 && (
                            <div className="p-3 rounded-3 bg-danger bg-opacity-5 border border-danger border-opacity-10 animate-in">
                                <p className="smallest text-danger fw-bold uppercase ls-1 mb-2">
                                    <i className="fas fa-exclamation-circle me-2"></i>
                                    Punti di Perdita (FC &gt; 35%):
                                </p>
                                <div className="d-flex flex-column gap-1">
                                    {finanza.piatti_critici.map(p => (
                                        <div key={p.id} className="d-flex justify-content-between smallest">
                                            <span className="text-muted-soft">{p.nome}</span>
                                            <span className="text-danger fw-bold">{p.cost_percent}%</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </section>
                )}

                <section className="mb-5 animate-in">
                    <div className="d-flex justify-content-between align-items-center mb-3">
                        <h6 className="smallest fw-bold text-nuvia-accent uppercase ls-1 mb-0">Rilevamento Allergeni</h6>
                        {missingAllergens.length > 0 && (
                            <span className="tiny-badge bg-warning bg-opacity-20 text-warning">Dati Parziali</span>
                        )}
                    </div>
                    <div className="mb-3">
                        {allergenSummary.length === 0 && <span className="text-muted-soft smallest uppercase ls-1">Nessun allergene dichiarato.</span>}
                        {allergenSummary.map((item) => (
                            <InsightBadge
                                key={item.id}
                                label={item.nome || item.codice || 'Allergene'}
                                value={`x${item.conteggio}`}
                                tone={highFrequency.find((hf) => hf.id === item.id) ? 'danger' : 'info'}
                            />
                        ))}
                    </div>
                    {highFrequency.length > 0 && (
                        <div className="p-3 rounded-3 bg-danger bg-opacity-5 border border-danger border-opacity-10 mb-3 animate-in">
                            <p className="smallest text-danger fw-bold uppercase ls-1 mb-0">
                                <i className="fas fa-exclamation-triangle me-2"></i>
                                Elevata concentrazione: {highFrequency.map((item) => item.nome || item.codice).join(', ')}
                            </p>
                        </div>
                    )}
                </section>

                <section className="mb-5 animate-in">
                    <div className="d-flex justify-content-between align-items-center mb-3">
                        <h6 className="smallest fw-bold text-nuvia-accent uppercase ls-1 mb-0">Stagionalità & Menu</h6>
                        {currentSeason && <span className="tiny-badge bg-nuvia-primary bg-opacity-20 text-nuvia-primary">{currentSeason.toUpperCase()}</span>}
                    </div>

                    <div className="mb-4">
                        {typeof inSeasonRatio === 'number' && (
                            <div className="d-flex align-items-center gap-3 mb-3">
                                <div className="flex-grow-1 bg-white bg-opacity-5 rounded-pill" style={{ height: '6px' }}>
                                    <div className="bg-success rounded-pill" style={{ width: `${inSeasonRatio * 100}%`, height: '100%' }}></div>
                                </div>
                                <span className="smallest fw-bold text-success">{(inSeasonRatio * 100).toFixed(0)}% IN STAGIONE</span>
                            </div>
                        )}

                        {seasonalityIssues.length > 0 && (
                            <div className="d-flex flex-column gap-2">
                                {seasonalityIssues.slice(0, 3).map((issue, idx) => (
                                    <div key={idx} className="p-2 rounded bg-white bg-opacity-5 border border-white border-opacity-5 d-flex align-items-center gap-3 animate-in">
                                        <span className="tiny-badge bg-secondary bg-opacity-20 text-muted-soft">{issue.ingrediente.stagionalita.toUpperCase()}</span>
                                        <span className="smallest fw-bold text-white text-truncate flex-grow-1">{issue.ingrediente.nome}</span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="d-flex flex-wrap gap-1">
                        {seasonalIngredients.map((item) => (
                            <InsightBadge
                                key={item.id}
                                label={item.nome}
                                tone="success"
                            />
                        ))}
                    </div>
                </section>

                <section className="animate-in">
                    <div className="d-flex align-items-center gap-2 mb-3">
                        <i className="fas fa-magic tiny text-nuvia-accent"></i>
                        <h6 className="smallest fw-bold text-white uppercase ls-1 mb-0">Ottimizzazione A.I.D.A.</h6>
                    </div>
                    {suggestions.length === 0 && (
                        <div className="text-muted-soft smallest uppercase ls-1 fw-bold border border-dashed border-white border-opacity-5 p-4 rounded-3 text-center">Analisi completata: nessun conflitto.</div>
                    )}
                    {suggestions.map((tip, idx) => (
                        <div key={idx} className="p-3 rounded-4 bg-nuvia-primary bg-opacity-5 border border-nuvia-primary border-opacity-10 smallest fw-bold text-white mb-2 ls-tight">
                            {tip}
                        </div>
                    ))}
                </section>
            </div>
        </div>
    );
};

export default MenuInsights;
