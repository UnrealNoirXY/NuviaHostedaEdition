import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { createMenu, getLayouts, getPiatti, validateMenuDraft } from '../api';
import { usePermissions } from '../permissions';

const DRAFT_STORAGE_KEY = 'menu-studio-service-draft-v1';
const TELEMETRY_STORAGE_KEY = 'menu-studio-telemetry-v1';
const USAGE_STORAGE_KEY = 'menu-studio-dish-usage-v1';
const ONBOARDING_STORAGE_PREFIX = 'menu-studio-onboarding-v1';

const steps = [
    { id: 'service', title: '1. QUANDO & DOVE', description: 'Data, turno e struttura' },
    { id: 'composition', title: '2. COSA SERVIAMO', description: 'Seleziona i piatti' },
    { id: 'checks', title: '3. SICUREZZA', description: 'Allergeni e controlli' },
    { id: 'output', title: '4. STAMPA', description: 'Stile e conferma finale' },
];

const onboardingSteps = [
    {
        id: 'welcome',
        title: 'Benvenuto nel Wizard Chef-first',
        description: 'Questo percorso è pensato per creare il menu servizio in pochi minuti senza passaggi tecnici dispersivi.',
    },
    {
        id: 'flow',
        title: 'Flusso in 4 step',
        description: 'Compila Servizio, seleziona i piatti, verifica controlli e apri l’editor. Ogni step mostra cosa manca per procedere.',
    },
    {
        id: 'resume',
        title: 'Ripresa automatica',
        description: 'Le bozze vengono salvate automaticamente. Se interrompi il lavoro, puoi riprendere dove avevi lasciato.',
    },
];

const serviceTemplates = [
    {
        id: 'colazione',
        label: 'Colazione standard',
        turno: 'colazione',
        namePrefix: 'Menu Colazione',
        note: 'Prediligere preparazioni veloci e opzioni senza lattosio/glutine.',
        categories: ['bevanda', 'dessert'],
    },
    {
        id: 'pranzo',
        label: 'Pranzo servizio',
        turno: 'pranzo',
        namePrefix: 'Menu Pranzo',
        note: 'Equilibrio tra primo e secondo, attenzione tempi uscita in sala.',
        categories: ['antipasto', 'primo', 'secondo'],
    },
    {
        id: 'cena',
        label: 'Cena degustazione',
        turno: 'cena',
        namePrefix: 'Menu Cena',
        note: 'Curare allergeni principali e bilanciamento portate.',
        categories: ['antipasto', 'primo', 'secondo', 'dessert'],
    },
    {
        id: 'evento',
        label: 'Evento speciale',
        turno: 'speciale',
        namePrefix: 'Menu Evento',
        note: 'Aggiungere note operative per timing buffet e sostituzioni.',
        categories: ['antipasto', 'secondo', 'dessert'],
    },
];

const requiredCategories = ['antipasto', 'primo', 'secondo', 'dessert'];

const parseApiError = (error, fallback) => {
    if (error?.response?.data?.detail) return String(error.response.data.detail);
    if (error?.response?.data?.error) return String(error.response.data.error);
    if (Array.isArray(error?.response?.data?.non_field_errors)) return error.response.data.non_field_errors.join(' · ');
    if (typeof error?.message === 'string' && error.message.trim()) return error.message;
    return fallback;
};

const resolveRoleLabel = (permissions) => {
    if (permissions?.is_superuser) return 'Super Admin';
    if (permissions?.is_owner) return 'Owner';
    const isChef = permissions?.structures?.some(s => s.role === 'Chef');
    if (isChef || permissions?.aggregate?.can_edit_menus) return 'Chef';
    if (permissions?.aggregate?.can_publish_menu) return 'Chef Manager';
    return 'Operatore Cucina';
};

const nowIso = () => new Date().toISOString();

const approvalLabel = {
    draft: 'Bozza',
    in_review: 'In revisione',
    approved: 'Approvato',
};

const approvalBadgeClass = {
    draft: 'status-chip status-chip--warning',
    in_review: 'status-chip status-chip--info',
    approved: 'status-chip status-chip--success',
};

const MenuWizard = () => {
    const navigate = useNavigate();
    const { permissions } = usePermissions();

    const [currentStep, setCurrentStep] = useState(0);
    const [draft, setDraft] = useState({
        nome: '',
        data_evento: new Date().toISOString().slice(0, 10),
        turno: 'pranzo',
        struttura: '',
        company: '',
        layout: null,
        note_servizio: '',
        piatti: [],
        applied_template: '',
        approval_status: 'draft',
        reviewer_name: '',
        reviewer_notes: '',
        scheduled_publish_at: '',
    });

    const [piatti, setPiatti] = useState([]);
    const [layouts, setLayouts] = useState([]);
    const [search, setSearch] = useState('');
    const [validation, setValidation] = useState(null);

    const [loadingState, setLoadingState] = useState('idle'); // idle|loading|success|error
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isValidating, setIsValidating] = useState(false);
    const [error, setError] = useState(null);
    const [isDraftHydrated, setIsDraftHydrated] = useState(false);

    const [onboardingOpen, setOnboardingOpen] = useState(false);
    const [onboardingStep, setOnboardingStep] = useState(0);
    const [dishUsage, setDishUsage] = useState({});
    const [telemetrySnapshot, setTelemetrySnapshot] = useState({
        sessions_completed: 0,
        sessions_abandoned: 0,
        avg_completion_minutes: null,
        last_completed_at: null,
        step_dropoffs: {},
    });

    const stepRefs = useRef({
        service: null,
        composition: null,
        checks: null,
        output: null,
    });
    const stepEnterAtRef = useRef(Date.now());
    const telemetrySavedRef = useRef(false);

    const roleLabel = useMemo(() => resolveRoleLabel(permissions), [permissions]);

    const companyOptions = useMemo(() => permissions?.companies || [], [permissions]);

    const resolveCompanyId = (companyValue) => {
        if (!companyValue) return '';
        const normalizedValue = String(companyValue).trim().toLowerCase();
        const directMatch = companyOptions.find((company) => String(company.id) === String(companyValue));
        if (directMatch) {
            return String(directMatch.id);
        }

        const byName = companyOptions.find((company) => company.name?.trim().toLowerCase() === normalizedValue);
        return byName ? String(byName.id) : '';
    };

    const structureOptions = useMemo(() => {
        let options = permissions?.structures_scope || [];
        if (permissions?.is_superuser) {
            const selectedCompanyId = resolveCompanyId(draft.company);
            if (selectedCompanyId) {
                options = options.filter((s) => String(s.company_id) === selectedCompanyId);
            } else {
                // Se superuser ma nessuna azienda selezionata, non mostriamo nulla per sicurezza
                return [];
            }
        } else if (permissions?.is_owner || permissions?.structures?.some(s => s.role === 'Chef')) {
            // Se owner o chef della company, filtriamo per la company dell'utente se disponibile
            const userCompanyId = permissions?.companies?.[0]?.id;
            if (userCompanyId) {
                options = options.filter(s => String(s.company_id) === String(userCompanyId));
            }
        }
        return options;
    }, [permissions, draft.company, companyOptions]);

    useEffect(() => {
        if (!permissions?.is_superuser || !companyOptions.length) return;

        const normalizedCompanyId = resolveCompanyId(draft.company);
        if (normalizedCompanyId && String(draft.company) !== normalizedCompanyId) {
            updateDraft({ company: normalizedCompanyId, struttura: '' });
            return;
        }

        if (!draft.company && companyOptions.length === 1) {
            updateDraft({ company: String(companyOptions[0].id), struttura: '' });
        }
    }, [permissions, companyOptions, draft.company]);

    const selectedPiattiDetails = useMemo(() => {
        const map = new Map(piatti.map((p) => [p.id, p]));
        return draft.piatti.map((id) => map.get(id)).filter(Boolean);
    }, [draft.piatti, piatti]);

    const filteredPiatti = useMemo(() => {
        const term = search.toLowerCase();
        return piatti.filter((p) => (
            p.nome?.toLowerCase().includes(term)
            || p.categoria_display?.toLowerCase().includes(term)
        ));
    }, [piatti, search]);

    const categoryCoverage = useMemo(() => {
        const selected = new Set(selectedPiattiDetails.map((p) => p.categoria));
        const missing = requiredCategories.filter((category) => !selected.has(category));
        return { missing };
    }, [selectedPiattiDetails]);

    const allergensSummary = useMemo(() => {
        const counters = new Map();
        selectedPiattiDetails.forEach((piatto) => {
            const allergeni = piatto.allergeni_details || piatto.allergeni || [];
            allergeni.forEach((allergene) => {
                const code = allergene.codice || allergene.nome;
                counters.set(code, (counters.get(code) || 0) + 1);
            });
        });
        return Array.from(counters.entries()).sort((a, b) => b[1] - a[1]);
    }, [selectedPiattiDetails]);

    const mostUsedDishes = useMemo(() => {
        const usageEntries = Object.entries(dishUsage)
            .map(([id, count]) => ({ id: Number(id), count }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 6);

        const lookup = new Map(piatti.map((dish) => [dish.id, dish]));
        return usageEntries
            .map((entry) => ({ ...entry, dish: lookup.get(entry.id) }))
            .filter((entry) => entry.dish);
    }, [dishUsage, piatti]);

    const suggestedByTemplate = useMemo(() => {
        const selectedTemplate = serviceTemplates.find((tpl) => tpl.id === draft.applied_template);
        if (!selectedTemplate) return [];

        const selectedSet = new Set(draft.piatti);
        return piatti
            .filter((dish) => selectedTemplate.categories.includes(dish.categoria) && !selectedSet.has(dish.id))
            .slice(0, 6);
    }, [draft.applied_template, piatti, draft.piatti]);

    const stepIssues = useMemo(() => ({
        service: [
            !draft.nome?.trim() ? 'Inserisci il nome del menu servizio.' : null,
            !draft.data_evento ? 'Seleziona la data del servizio.' : null,
            !draft.struttura ? 'Seleziona la struttura di riferimento.' : null,
        ].filter(Boolean),
        composition: [
            draft.piatti.length === 0 ? 'Seleziona almeno un piatto per creare il menu.' : null,
        ].filter(Boolean),
        checks: [
            categoryCoverage.missing.length > 0
                ? `Copertura categorie consigliata incompleta: mancano ${categoryCoverage.missing.join(', ')}.`
                : null,
        ].filter(Boolean),
        output: [
            draft.approval_status !== 'approved' ? 'Imposta lo stato su Approvato prima di aprire l\'editor.' : null,
            !draft.reviewer_name?.trim() ? 'Inserisci il nome del reviewer per la tracciabilità.' : null,
        ].filter(Boolean),
    }), [draft.nome, draft.data_evento, draft.struttura, draft.piatti.length, categoryCoverage.missing, draft.approval_status, draft.reviewer_name]);

    const unresolvedIssues = useMemo(
        () => steps.flatMap((step, idx) => (stepIssues[step.id] || []).map((issue) => ({ issue, stepId: step.id, stepIndex: idx, stepTitle: step.title }))),
        [stepIssues],
    );

    const currentStepId = steps[currentStep].id;
    const currentStepIssues = stepIssues[currentStepId] || [];
    const canGoNext = currentStepIssues.length === 0;

    const publishState = useMemo(() => {
        if (isSubmitting) return { key: 'publishing', label: 'Pubblicazione in corso', cls: 'status-chip status-chip--info' };
        if (validation?.can_publish) return { key: 'ready', label: 'Bozza pubblicabile', cls: 'status-chip status-chip--success' };
        return { key: 'draft', label: 'Bozza in compilazione', cls: 'status-chip status-chip--warning' };
    }, [isSubmitting, validation]);

    const canOpenStep = (targetIndex) => {
        if (targetIndex <= currentStep) return true;
        for (let idx = 0; idx < targetIndex; idx += 1) {
            const priorStep = steps[idx].id;
            if ((stepIssues[priorStep] || []).length > 0) return false;
        }
        return true;
    };

    const recordTelemetryEvent = (type, payload = {}) => {
        const raw = window.localStorage.getItem(TELEMETRY_STORAGE_KEY);
        const state = raw ? JSON.parse(raw) : {
            sessions_completed: 0,
            sessions_abandoned: 0,
            avg_completion_minutes: null,
            completion_minutes_total: 0,
            last_completed_at: null,
            step_dropoffs: {},
            events: [],
        };

        if (type === 'complete') {
            const minutes = payload.completion_minutes || 0;
            state.sessions_completed += 1;
            state.completion_minutes_total += minutes;
            state.avg_completion_minutes = Number((state.completion_minutes_total / Math.max(state.sessions_completed, 1)).toFixed(1));
            state.last_completed_at = nowIso();
        }

        if (type === 'abandon') {
            state.sessions_abandoned += 1;
            const stepId = payload.step_id || 'unknown';
            state.step_dropoffs[stepId] = (state.step_dropoffs[stepId] || 0) + 1;
        }

        state.events.unshift({ type, at: nowIso(), ...payload });
        state.events = state.events.slice(0, 30);

        window.localStorage.setItem(TELEMETRY_STORAGE_KEY, JSON.stringify(state));
        setTelemetrySnapshot({
            sessions_completed: state.sessions_completed,
            sessions_abandoned: state.sessions_abandoned,
            avg_completion_minutes: state.avg_completion_minutes,
            last_completed_at: state.last_completed_at,
            step_dropoffs: state.step_dropoffs,
        });
    };

    const incrementDishUsage = (dishIds) => {
        const next = { ...dishUsage };
        dishIds.forEach((id) => {
            next[id] = (next[id] || 0) + 1;
        });
        setDishUsage(next);
        window.localStorage.setItem(USAGE_STORAGE_KEY, JSON.stringify(next));
    };

    const goToStep = (stepIndex) => {
        if (stepIndex < 0 || stepIndex >= steps.length) return;
        const prevStepId = steps[currentStep]?.id;
        const spentMs = Date.now() - stepEnterAtRef.current;
        recordTelemetryEvent('step_transition', {
            from: prevStepId,
            to: steps[stepIndex].id,
            spent_ms: spentMs,
        });

        setCurrentStep(stepIndex);
        stepEnterAtRef.current = Date.now();

        const step = steps[stepIndex];
        const target = stepRefs.current[step.id];
        if (target?.scrollIntoView) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    const applyTemplate = (template) => {
        const today = new Date().toISOString().slice(0, 10);
        setDraft((prev) => ({
            ...prev,
            turno: template.turno,
            nome: prev.nome?.trim() ? prev.nome : `${template.namePrefix} ${today}`,
            note_servizio: prev.note_servizio?.trim() ? prev.note_servizio : template.note,
            applied_template: template.id,
        }));
        recordTelemetryEvent('template_applied', { template_id: template.id });
    };

    useEffect(() => {
        const storedDraft = window.localStorage.getItem(DRAFT_STORAGE_KEY);
        if (storedDraft) {
            try {
                const parsed = JSON.parse(storedDraft);
                setDraft((prev) => ({ ...prev, ...parsed }));
            } catch {
                window.localStorage.removeItem(DRAFT_STORAGE_KEY);
            }
        }

        const savedUsage = window.localStorage.getItem(USAGE_STORAGE_KEY);
        if (savedUsage) {
            try {
                setDishUsage(JSON.parse(savedUsage));
            } catch {
                window.localStorage.removeItem(USAGE_STORAGE_KEY);
            }
        }

        const rawTelemetry = window.localStorage.getItem(TELEMETRY_STORAGE_KEY);
        if (rawTelemetry) {
            try {
                const parsedTelemetry = JSON.parse(rawTelemetry);
                setTelemetrySnapshot({
                    sessions_completed: parsedTelemetry.sessions_completed || 0,
                    sessions_abandoned: parsedTelemetry.sessions_abandoned || 0,
                    avg_completion_minutes: parsedTelemetry.avg_completion_minutes || null,
                    last_completed_at: parsedTelemetry.last_completed_at || null,
                    step_dropoffs: parsedTelemetry.step_dropoffs || {},
                });
            } catch {
                window.localStorage.removeItem(TELEMETRY_STORAGE_KEY);
            }
        }

        const onboardingKey = `${ONBOARDING_STORAGE_PREFIX}:${roleLabel}`;
        const onboardingSeen = window.localStorage.getItem(onboardingKey) === 'seen';
        if (!onboardingSeen) {
            setOnboardingOpen(true);
        }

        stepEnterAtRef.current = Date.now();
        setIsDraftHydrated(true);
        recordTelemetryEvent('session_open', { role: roleLabel });

        const handleBeforeUnload = () => {
            if (!telemetrySavedRef.current) {
                recordTelemetryEvent('abandon', { step_id: steps[currentStep]?.id });
                telemetrySavedRef.current = true;
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
            if (!telemetrySavedRef.current) {
                recordTelemetryEvent('abandon', { step_id: steps[currentStep]?.id });
                telemetrySavedRef.current = true;
            }
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [roleLabel]);

    useEffect(() => {
        if (!isDraftHydrated) return;
        window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
    }, [draft, isDraftHydrated]);

    useEffect(() => {
        const fetchInitialData = async () => {
            setLoadingState('loading');
            setError(null);
            try {
                const [piattiRes, layoutsRes] = await Promise.all([
                    getPiatti({ detailed: true }),
                    getLayouts(),
                ]);
                setPiatti(piattiRes.data || []);
                setLayouts(layoutsRes.data || []);
                setLoadingState('success');
            } catch (err) {
                setLoadingState('error');
                setError(parseApiError(err, 'Non riesco a caricare catalogo piatti e layout. Riprova tra pochi secondi.'));
            }
        };
        fetchInitialData();
    }, []);

    // Auto-selezione struttura se ce n'è solo una disponibile
    useEffect(() => {
        if (structureOptions.length === 1 && !draft.struttura) {
            updateDraft({ struttura: String(structureOptions[0].id) });
        }
    }, [structureOptions, draft.struttura]);

    const updateDraft = (changes) => {
        setDraft((prev) => ({ ...prev, ...changes }));
    };

    const togglePiatto = (piattoId) => {
        setDraft((prev) => {
            if (prev.piatti.includes(piattoId)) {
                return { ...prev, piatti: prev.piatti.filter((id) => id !== piattoId) };
            }
            return { ...prev, piatti: [...prev.piatti, piattoId] };
        });
    };

    const runValidation = async () => {
        setIsValidating(true);
        setError(null);
        try {
            const response = await validateMenuDraft({ ...draft, struttura: draft.struttura || null });
            setValidation(response.data);
            return response.data;
        } catch (err) {
            setError(parseApiError(err, 'Non posso validare il menu ora. Controlla i campi obbligatori e riprova.'));
            return null;
        } finally {
            setIsValidating(false);
        }
    };


    const buildHandoffPayload = () => ({
        generated_at: nowIso(),
        service: {
            nome: draft.nome,
            data_evento: draft.data_evento,
            turno: draft.turno,
            struttura: structureOptions.find((s) => String(s.id) === String(draft.struttura))?.name || null,
        },
        governance: {
            approval_status: draft.approval_status,
            reviewer_name: draft.reviewer_name,
            reviewer_notes: draft.reviewer_notes,
            scheduled_publish_at: draft.scheduled_publish_at || null,
        },
        composition: selectedPiattiDetails.map((dish) => ({ id: dish.id, nome: dish.nome, categoria: dish.categoria_display })),
        allergeni_top: allergensSummary.slice(0, 8).map(([name, count]) => ({ name, count })),
        issues_open: unresolvedIssues.map((item) => ({ step: item.stepTitle, message: item.issue })),
    });

    const exportHandoff = async () => {
        const payload = buildHandoffPayload();
        const json = JSON.stringify(payload, null, 2);
        try {
            await navigator.clipboard.writeText(json);
            recordTelemetryEvent('handoff_copied', { bytes: json.length });
        } catch {
            setError('Non riesco a copiare il pacchetto handoff. Copia manualmente dal pannello debug browser.');
        }
    };

    const handleSubmit = async () => {
        setIsSubmitting(true);
        const latestValidation = await runValidation();
        if (!latestValidation || !latestValidation.can_publish || stepIssues.output.length > 0) {
            setIsSubmitting(false);
            return;
        }
        try {
            const response = await createMenu({ ...draft, layout: draft.layout || null });
            window.localStorage.removeItem(DRAFT_STORAGE_KEY);
            incrementDishUsage(draft.piatti);
            const completionMinutes = Number(((Date.now() - stepEnterAtRef.current) / 60000).toFixed(1));
            recordTelemetryEvent('complete', { completion_minutes: completionMinutes, piatti_count: draft.piatti.length });
            telemetrySavedRef.current = true;
            navigate(`/menu-editor/${response.data.id}`);
        } catch (err) {
            setError(parseApiError(err, 'Il salvataggio non è riuscito. Verifica connessione o permessi e riprova.'));
        } finally {
            setIsSubmitting(false);
        }
    };

    const completeOnboarding = () => {
        const onboardingKey = `${ONBOARDING_STORAGE_PREFIX}:${roleLabel}`;
        window.localStorage.setItem(onboardingKey, 'seen');
        setOnboardingOpen(false);
        recordTelemetryEvent('onboarding_completed', { role: roleLabel });
    };

    const renderServiceStep = () => (
        <div className="wizard-step-card animate-in border-white border-opacity-5" ref={(el) => { stepRefs.current.service = el; }}>
            <div className="mb-4">
                <p className="small-label mb-3 text-nuvia-accent fw-bold uppercase ls-1">1. Scegli un Template di Partenza</p>
                <div className="template-grid">
                    {serviceTemplates.map((template) => (
                        <button
                            type="button"
                            key={template.id}
                            className={`template-card border-white border-opacity-10 ${draft.applied_template === template.id ? 'active border-nuvia-primary' : ''}`}
                            onClick={() => applyTemplate(template)}
                        >
                            <strong className="text-white d-block mb-1">{template.label}</strong>
                            <span className="tiny text-muted-soft lh-sm">{template.note}</span>
                        </button>
                    ))}
                </div>
            </div>

            <div className="row g-4 pt-3">
                {permissions?.is_superuser && (
                    <div className="col-md-12">
                        <label className="form-label smallest fw-bold uppercase text-muted-soft mb-2">Società (Azienda)</label>
                        <select className="form-select noir-select py-3" value={draft.company} onChange={(e) => updateDraft({ company: e.target.value, struttura: '' })}>
                            <option value="">Seleziona azienda...</option>
                            {companyOptions.map((company) => <option key={company.id} value={company.id}>{company.name}</option>)}
                        </select>
                    </div>
                )}
                <div className="col-md-12">
                    <label className="form-label smallest fw-bold uppercase text-muted-soft mb-2">Nome Identificativo Menu</label>
                    <input type="text" className="form-control noir-input py-3" value={draft.nome} onChange={(e) => updateDraft({ nome: e.target.value })} placeholder="Es. Pranzo servizio Sabato 15" />
                </div>
                <div className="col-md-6">
                    <label className="form-label smallest fw-bold uppercase text-muted-soft mb-2">Data Servizio</label>
                    <input type="date" className="form-control noir-input py-3" value={draft.data_evento} onChange={(e) => updateDraft({ data_evento: e.target.value })} />
                </div>
                <div className="col-md-6">
                    <label className="form-label smallest fw-bold uppercase text-muted-soft mb-2">Turno Operativo</label>
                    <select className="form-select noir-select py-3" value={draft.turno} onChange={(e) => updateDraft({ turno: e.target.value })}>
                        <option value="colazione">Colazione</option>
                        <option value="pranzo">Pranzo</option>
                        <option value="cena">Cena</option>
                        <option value="speciale">Evento speciale</option>
                    </select>
                </div>
                <div className="col-md-12">
                    <label className="form-label smallest fw-bold uppercase text-nuvia-accent mb-2">Struttura di Riferimento</label>
                    <select
                        className="form-select noir-select py-3"
                        value={draft.struttura}
                        onChange={(e) => updateDraft({ struttura: e.target.value })}
                        disabled={permissions?.is_superuser && !draft.company}
                        required
                    >
                        {permissions?.is_superuser && !draft.company ? (
                            <option value="">Scegli prima una Società...</option>
                        ) : (
                            <option value="">Seleziona struttura...</option>
                        )}
                        {structureOptions.map((s) => (
                            <option key={s.id} value={s.id}>
                                {s.company_name ? `[${s.company_name}] ` : ''}{s.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>
        </div>
    );

    const renderCompositionStep = () => (
        <div className="wizard-step-card animate-in p-0 overflow-hidden border-white border-opacity-5" ref={(el) => { stepRefs.current.composition = el; }}>
            <div className="p-4 border-bottom border-white border-opacity-10 bg-white bg-opacity-5">
                <p className="smallest fw-bold uppercase text-nuvia-accent ls-1 mb-3">Suggerimenti in base all'utilizzo</p>
                <div className="d-flex flex-wrap gap-2">
                    {mostUsedDishes.length === 0 ? (
                        <span className="text-muted-soft smallest">Le statistiche di utilizzo compariranno dopo i primi menu creati.</span>
                    ) : (
                        mostUsedDishes.map((entry) => (
                            <button type="button" key={entry.id} className={`btn btn-sm smallest fw-bold px-3 py-2 ${draft.piatti.includes(entry.id) ? 'btn-nuvia-primary' : 'btn-nuvia-ghost'}`} onClick={() => togglePiatto(entry.id)}>
                                {entry.dish.nome} <span className="opacity-50 ms-1">({entry.count})</span>
                            </button>
                        ))
                    )}
                </div>
            </div>

            <div className="d-flex" style={{ height: '540px' }}>
                <div className="flex-grow-1 border-end border-white border-opacity-5 p-4 overflow-auto bg-black bg-opacity-20">
                    <div className="position-relative mb-4">
                        <i className="fas fa-search position-absolute top-50 start-0 translate-middle-y ms-3 text-muted-soft"></i>
                        <input type="search" className="form-control noir-input py-3 ps-5 smallest fw-bold" placeholder="CERCA PIATTO O CATEGORIA..." value={search} onChange={(e) => setSearch(e.target.value)} />
                    </div>

                    {loadingState === 'success' && filteredPiatti.length === 0 && (
                        <div className="alert alert-nuvia-warning smallest fw-bold">Nessun risultato trovato.</div>
                    )}

                    <div className="d-flex flex-column gap-2">
                        {filteredPiatti.map((p) => (
                            <button type="button" key={p.id} className={`piatto-selection-item p-3 w-100 text-start border-white border-opacity-5 rounded-3 transition-all ${draft.piatti.includes(p.id) ? 'selected bg-nuvia-primary bg-opacity-10 border-nuvia-primary' : 'bg-white bg-opacity-5'}`} onClick={() => togglePiatto(p.id)}>
                                <div className="d-flex justify-content-between align-items-center">
                                    <div>
                                        <span className="smaller fw-bold d-block text-white mb-1 uppercase ls-tight">{p.nome}</span>
                                        <span className="tiny text-muted-soft uppercase fw-bold ls-1">{p.categoria_display}</span>
                                    </div>
                                    <div className={`p-2 rounded-circle border ${draft.piatti.includes(p.id) ? 'bg-nuvia-primary border-nuvia-primary text-white' : 'border-white border-opacity-20 text-transparent'}`}>
                                        <i className="fas fa-check tiny"></i>
                                    </div>
                                </div>
                            </button>
                        ))}
                    </div>
                </div>
                <div className="w-40 bg-black bg-opacity-40 p-4 overflow-auto">
                    <h6 className="smallest uppercase fw-bold text-nuvia-accent mb-4 ls-1">PIATTI IN SERVIZIO ({draft.piatti.length})</h6>
                    {selectedPiattiDetails.length === 0 && (
                        <div className="text-center py-5 opacity-50">
                            <i className="fas fa-utensils h3 mb-3 d-block"></i>
                            <p className="smallest uppercase fw-bold ls-1">Nessun Piatto</p>
                        </div>
                    )}
                    <div className="d-flex flex-column gap-2">
                        {selectedPiattiDetails.map((p) => (
                            <div key={p.id} className="p-3 rounded-3 bg-white bg-opacity-5 border border-white border-opacity-5 d-flex justify-content-between align-items-center gap-2 animate-in">
                                <div>
                                    <span className="smallest fw-bold d-block text-white uppercase ls-tight">{p.nome}</span>
                                    <span className="tiny text-nuvia-primary uppercase fw-bold ls-1">{p.categoria_display}</span>
                                </div>
                                <button type="button" className="btn btn-link text-danger p-0 border-0" onClick={() => togglePiatto(p.id)}>
                                    <i className="fas fa-times-circle"></i>
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );

    const renderChecksStep = () => (
        <div className="wizard-step-card animate-in border-white border-opacity-5" ref={(el) => { stepRefs.current.checks = el; }}>
            <div className="row g-4">
                <div className="col-md-12">
                    <p className="smallest fw-bold uppercase text-nuvia-accent ls-1 mb-3">Copertura Categorie Obbligatorie</p>
                    <div className="d-flex gap-3 flex-wrap">
                        {requiredCategories.map((category) => {
                            const covered = !categoryCoverage.missing.includes(category);
                            return (
                                <div key={category} className={`px-4 py-2 rounded-pill smallest fw-bold border ${covered ? 'bg-success bg-opacity-10 text-success border-success border-opacity-20' : 'bg-white bg-opacity-5 text-muted-soft border-white border-opacity-10'}`}>
                                    <i className={`fas ${covered ? 'fa-check-circle' : 'fa-times-circle'} me-2`}></i>
                                    {category.toUpperCase()}
                                </div>
                            );
                        })}
                    </div>
                </div>
                <div className="col-md-12">
                    <p className="smallest fw-bold uppercase text-nuvia-accent ls-1 mb-3">Rilevamento Allergeni nel Servizio</p>
                    {allergensSummary.length === 0 ? (
                        <p className="smaller text-muted-soft italic mb-0">Nessun allergene critico rilevato nei piatti selezionati.</p>
                    ) : (
                        <div className="d-flex flex-wrap gap-2">
                            {allergensSummary.slice(0, 8).map(([allergene, count]) => (
                                <span key={allergene} className="px-3 py-2 rounded bg-warning bg-opacity-10 text-warning border border-warning border-opacity-20 smallest fw-bold">
                                    {allergene.toUpperCase()} · <span className="opacity-50">{count}x</span>
                                </span>
                            ))}
                        </div>
                    )}
                </div>
                {suggestedByTemplate.length > 0 && (
                    <div className="col-md-12">
                        <p className="smallest fw-bold uppercase text-nuvia-accent ls-1 mb-3">Abbinamenti Suggeriti per {draft.applied_template.toUpperCase()}</p>
                        <div className="d-flex flex-wrap gap-2">
                            {suggestedByTemplate.map((dish) => (
                                <button type="button" key={dish.id} className="btn btn-sm btn-nuvia-ghost smallest fw-bold border-white border-opacity-10 px-3 py-2" onClick={() => togglePiatto(dish.id)}>
                                    <i className="fas fa-plus-circle me-2 text-nuvia-primary"></i> AGGIUNGI {dish.nome.toUpperCase()}
                                </button>
                            ))}
                        </div>
                    </div>
                )}
                <div className="col-md-12 pt-3">
                    <label className="smallest fw-bold uppercase text-muted-soft mb-2">Note Operative per lo Staff</label>
                    <textarea className="form-control noir-input py-3" rows={5} placeholder="Inserisci note per la sala, priorità uscita piatti o varianti allergeni..." value={draft.note_servizio} onChange={(e) => updateDraft({ note_servizio: e.target.value })} />
                </div>
            </div>
        </div>
    );

    const renderOutputStep = () => (
        <div className="wizard-step-card animate-in border-white border-opacity-5" ref={(el) => { stepRefs.current.output = el; }}>
            <div className="row g-4">
                <div className="col-md-6">
                    <div className="p-4 rounded-4 bg-white bg-opacity-5 border border-white border-opacity-5 h-100">
                        <p className="smallest fw-bold uppercase text-nuvia-accent ls-1 mb-3">Riepilogo Registrazione</p>
                        <h4 className="text-white fw-bold mb-1">{draft.nome || 'MENU SENZA NOME'}</h4>
                        <p className="smallest text-muted-soft uppercase fw-bold ls-1 mb-4">
                            <i className="fas fa-calendar-check me-2 text-nuvia-primary"></i>
                            {new Date(draft.data_evento).toLocaleDateString()} · {draft.turno.toUpperCase()}
                        </p>

                        <div className="d-flex flex-column gap-3 pt-3 border-top border-white border-opacity-10">
                            <div className="d-flex justify-content-between align-items-center smallest">
                                <span className="text-muted-soft uppercase fw-bold ls-1">Struttura</span>
                                <span className="text-white fw-bold">{structureOptions.find((s) => String(s.id) === String(draft.struttura))?.name || 'DA DEFINIRE'}</span>
                            </div>
                            <div className="d-flex justify-content-between align-items-center smallest">
                                <span className="text-muted-soft uppercase fw-bold ls-1">Template</span>
                                <span className="text-white fw-bold">{draft.applied_template.toUpperCase() || 'MANUALE'}</span>
                            </div>
                            <div className="d-flex justify-content-between align-items-center smallest">
                                <span className="text-muted-soft uppercase fw-bold ls-1">Piatti Totali</span>
                                <span className="text-white fw-bold badge bg-nuvia-primary rounded-pill">{draft.piatti.length}</span>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="col-md-6 d-flex flex-column gap-4">
                    <div>
                        <label className="smallest fw-bold uppercase text-muted-soft mb-2">Stile Grafico Predisposto</label>
                        <select className="form-select noir-select py-3" value={draft.layout ?? ''} onChange={(e) => updateDraft({ layout: e.target.value ? Number(e.target.value) : null })}>
                            <option value="">STILE AUTOMATICO INTELLIGENTE</option>
                            {layouts.map((layout) => <option key={layout.id} value={layout.id}>{layout.nome_layout.toUpperCase()}</option>)}
                        </select>
                    </div>
                    <div>
                        <label className="smallest fw-bold uppercase text-muted-soft mb-2">Stato Approvazione</label>
                        <select className="form-select noir-select py-3" value={draft.approval_status} onChange={(e) => updateDraft({ approval_status: e.target.value })}>
                            <option value="draft">🔴 BOZZA IN LAVORAZIONE</option>
                            <option value="in_review">🟡 IN ATTESA DI REVISIONE</option>
                            <option value="approved">🟢 APPROVATO PER SERVIZIO</option>
                        </select>
                    </div>
                </div>

                <div className="col-md-6">
                    <label className="smallest fw-bold uppercase text-muted-soft mb-2">Chef / Manager Responsabile</label>
                    <input type="text" className="form-control noir-input py-3" value={draft.reviewer_name} onChange={(e) => updateDraft({ reviewer_name: e.target.value })} placeholder="Nome dell'approvatore" />
                </div>
                <div className="col-md-6">
                    <label className="smallest fw-bold uppercase text-muted-soft mb-2">Pianifica Pubblicazione</label>
                    <input type="datetime-local" className="form-control noir-input py-3" value={draft.scheduled_publish_at} onChange={(e) => updateDraft({ scheduled_publish_at: e.target.value })} />
                </div>
                <div className="col-md-12">
                    <label className="smallest fw-bold uppercase text-muted-soft mb-2">Note Finali di Revisione</label>
                    <textarea className="form-control noir-input py-3" rows={3} value={draft.reviewer_notes} onChange={(e) => updateDraft({ reviewer_notes: e.target.value })} placeholder="Note finali per l'archiviazione..." />
                </div>

                {validation && (
                    <div className="col-md-12">
                        <div className={`p-3 rounded-3 border smallest fw-bold text-center uppercase ls-1 ${validation.can_publish ? 'bg-success bg-opacity-10 text-success border-success border-opacity-20' : 'bg-warning bg-opacity-10 text-warning border-warning border-opacity-20'}`}>
                            {validation.can_publish ? '✓ Configurazione Valida: Pronto per il Design' : '⚠ Configurazione Incompleta: Controlla gli step precedenti'}
                        </div>
                    </div>
                )}
            </div>
            <div className="mt-5 pt-4 border-top border-white border-opacity-10 d-flex flex-column gap-3">
                <button type="button" className="btn btn-nuvia-ghost smallest fw-bold py-3 uppercase ls-1 border-white border-opacity-5" onClick={exportHandoff}>
                    <i className="fas fa-code me-2"></i> Esporta Log di Configurazione (JSON)
                </button>
                <button className="btn btn-nuvia-primary w-100 py-3 fw-bold h5 mb-0" onClick={handleSubmit} disabled={isSubmitting || isValidating || stepIssues.output.length > 0}>
                    {isSubmitting ? 'GENERAZIONE STUDIO IN CORSO...' : 'APRI STUDIO DI DESIGN'}
                </button>
            </div>
        </div>
    );

    const renderStepContent = () => {
        if (currentStepId === 'service') return renderServiceStep();
        if (currentStepId === 'composition') return renderCompositionStep();
        if (currentStepId === 'checks') return renderChecksStep();
        return renderOutputStep();
    };

    if (loadingState === 'loading' || loadingState === 'idle') {
        return <div className="text-center py-5 animate-pulse text-muted-soft">Caricamento wizard servizio...</div>;
    }

    if (loadingState === 'error') {
        return (
            <div className="glass-card p-4 mx-4">
                <div className="alert alert-warning mb-3" role="alert">{error || 'Errore di caricamento dati iniziali.'}</div>
                <button className="btn btn-nuvia-primary" onClick={() => window.location.reload()}>Riprova caricamento</button>
            </div>
        );
    }

    return (
        <div className="glass-card p-4 mx-4 border-white border-opacity-5">
            {onboardingOpen && (
                <div className="onboarding-overlay" role="dialog" aria-modal="true">
                    <div className="onboarding-card border-nuvia-primary">
                        <div className="mb-3 d-flex align-items-center gap-2">
                            <div className="p-2 rounded-circle bg-nuvia-primary bg-opacity-10 text-nuvia-primary">
                                <i className="fas fa-magic"></i>
                            </div>
                            <p className="small-label mb-0">Onboarding rapido · {roleLabel}</p>
                        </div>
                        <h2 className="h4 fw-bold mb-3 text-white">{onboardingSteps[onboardingStep].title}</h2>
                        <p className="text-muted-soft mb-4 lh-base">{onboardingSteps[onboardingStep].description}</p>
                        <div className="d-flex justify-content-between align-items-center pt-3 border-top border-white border-opacity-10">
                            <span className="smallest fw-bold text-muted-soft">STEP {onboardingStep + 1} / {onboardingSteps.length}</span>
                            <div className="d-flex gap-2">
                                {onboardingStep > 0 && (
                                    <button type="button" className="btn btn-sm btn-nuvia-ghost px-3" onClick={() => setOnboardingStep((prev) => Math.max(0, prev - 1))}>INDIETRO</button>
                                )}
                                {onboardingStep < onboardingSteps.length - 1 ? (
                                    <button type="button" className="btn btn-sm btn-nuvia-primary px-3" onClick={() => setOnboardingStep((prev) => Math.min(onboardingSteps.length - 1, prev + 1))}>AVANTI</button>
                                ) : (
                                    <button type="button" className="btn btn-sm btn-nuvia-primary px-4 fw-bold" onClick={completeOnboarding}>INIZIA ORA</button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <div className="d-flex justify-content-between align-items-center mb-4 flex-wrap gap-2">
                <div className="d-flex gap-2 align-items-center">
                    <span className={publishState.cls + " smallest fw-bold uppercase px-3"}>{publishState.label}</span>
                    <span className={(approvalBadgeClass[draft.approval_status] || 'status-chip status-chip--warning') + " smallest fw-bold uppercase px-3"}>{approvalLabel[draft.approval_status] || 'Bozza'}</span>
                </div>
                <span className="smallest text-muted-soft uppercase ls-1">Sessione Locale: <strong className="text-nuvia-primary">{isDraftHydrated ? 'SINCRONIZZATA' : 'ATTESA...'}</strong></span>
            </div>

            {(error || currentStepIssues.length > 0) && (
                <div className="alert alert-nuvia-warning mb-4 animate-in" role="alert">
                    <div className="d-flex align-items-center gap-2 mb-2">
                        <i className="fas fa-exclamation-triangle"></i>
                        <span className="fw-bold uppercase smallest">Attenzione</span>
                    </div>
                    {error && <p className="mb-2 smaller">{error}</p>}
                    {currentStepIssues.length > 0 && (
                        <ul className="mb-0 ps-3 smaller">
                            {currentStepIssues.map((issue) => <li key={issue}>{issue}</li>)}
                        </ul>
                    )}
                </div>
            )}

            {unresolvedIssues.length > 0 && (
                <div className="issue-panel mb-4 border-danger border-opacity-20 bg-danger bg-opacity-5">
                    <div className="d-flex align-items-center gap-2 mb-3">
                        <div className="p-1 rounded bg-danger bg-opacity-20 text-danger smallest">
                           <i className="fas fa-tasks"></i>
                        </div>
                        <p className="smallest fw-bold uppercase mb-0 text-white ls-1">Azioni richieste ({unresolvedIssues.length})</p>
                    </div>
                    <div className="d-flex flex-column gap-2">
                        {unresolvedIssues.map((item) => (
                            <button type="button" key={`${item.stepId}-${item.issue}`} className="issue-panel__item border-white border-opacity-5" onClick={() => goToStep(item.stepIndex)}>
                                <span className="tiny-badge bg-white bg-opacity-10 text-white me-2">{item.stepTitle.split('.')[0]}</span>
                                <span className="smaller text-muted-soft"><strong>{item.stepTitle.split(' ')[1]}</strong>: {item.issue}</span>
                            </button>
                        ))}
                    </div>
                </div>
            )}

            <div className="d-flex justify-content-between align-items-center mb-5 flex-wrap gap-3">
                <div className="d-flex align-items-center gap-3">
                    <Link to="/menu" className="btn btn-nuvia-ghost p-2 rounded-circle" style={{ width: '40px', height: '40px', display: 'grid', placeItems: 'center' }}>
                        <i className="fas fa-arrow-left"></i>
                    </Link>
                    <div>
                        <span className="tiny-badge bg-nuvia-primary mb-1">Workflow Assistito</span>
                        <h1 className="h4 mb-0 fw-bold text-white">NUOVO MENU SERVIZIO</h1>
                    </div>
                </div>
                <div className="d-flex gap-2">
                    <button className="btn btn-nuvia-ghost px-4 smallest fw-bold" onClick={() => goToStep(Math.max(0, currentStep - 1))} disabled={currentStep === 0}>INDIETRO</button>
                    {currentStep < steps.length - 1 && (
                        <button className="btn btn-nuvia-primary px-4 smallest fw-bold" onClick={() => goToStep(Math.min(steps.length - 1, currentStep + 1))} disabled={!canGoNext}>PROSEGUI &rarr;</button>
                    )}
                </div>
            </div>

            <div className="wizard-stepper-noir mb-5">
                {steps.map((step, idx) => (
                    <button type="button" key={step.id} className={`step-item border-0 bg-transparent text-white ${idx === currentStep ? 'active' : ''} ${idx < currentStep ? 'completed' : ''}`} onClick={() => canOpenStep(idx) && goToStep(idx)} disabled={!canOpenStep(idx)}>
                        <div className="step-circle">{idx + 1}</div>
                        <span className="step-label">{step.title}</span>
                        <span className="tiny text-muted-soft text-uppercase">{step.description}</span>
                    </button>
                ))}
            </div>

            <div className="row">
                <div className="col-lg-8">{renderStepContent()}</div>
                <div className="col-lg-4">
                    <div className="validation-sidebar-noir">
                        <div className="sidebar-header border-bottom border-white border-opacity-10 pb-3 mb-4">
                            <h6 className="mb-1 text-white fw-bold">Stato servizio</h6>
                            <span className="tiny-badge">Adozione & telemetria locale</span>
                        </div>
                        <div className="checklist-container">
                            <div className="telemetry-box mb-3">
                                <p className="small-label mb-2">KPI locali</p>
                                <p className="mb-1 smallest">Sessioni completate: <strong>{telemetrySnapshot.sessions_completed}</strong></p>
                                <p className="mb-1 smallest">Sessioni interrotte: <strong>{telemetrySnapshot.sessions_abandoned}</strong></p>
                                <p className="mb-1 smallest">Tempo medio completamento: <strong>{telemetrySnapshot.avg_completion_minutes ?? 'N/A'} min</strong></p>
                                <p className="mb-0 smallest">Ultimo completamento: <strong>{telemetrySnapshot.last_completed_at ? new Date(telemetrySnapshot.last_completed_at).toLocaleString() : 'N/A'}</strong></p>
                            </div>

                            <div className="workflow-box mb-3">
                                <p className="small-label mb-2">Workflow approvazione</p>
                                <p className="smallest mb-1">Stato: <strong>{approvalLabel[draft.approval_status]}</strong></p>
                                <p className="smallest mb-1">Reviewer: <strong>{draft.reviewer_name || 'N/A'}</strong></p>
                                <p className="smallest mb-0">Pubblicazione pianificata: <strong>{draft.scheduled_publish_at || 'N/A'}</strong></p>
                            </div>

                            {steps.map((step, idx) => {
                                const issues = stepIssues[step.id] || [];
                                const done = idx < currentStep ? issues.length === 0 : false;
                                const dropoff = telemetrySnapshot.step_dropoffs?.[step.id] || 0;
                                return (
                                    <div key={step.id} className="mb-3 p-2 rounded-3 bg-white bg-opacity-0">
                                        <div className="d-flex align-items-center justify-content-between gap-2">
                                            <span className={`smallest uppercase ls-1 ${issues.length === 0 ? 'text-white fw-bold' : 'text-muted-soft'}`}>{step.title}</span>
                                            <span className={`badge ${issues.length === 0 ? 'text-bg-success' : 'text-bg-warning'}`}>{issues.length === 0 ? 'OK' : `${issues.length} azione/i`}</span>
                                        </div>
                                        {done && <div className="tiny text-success mt-1">Step completato</div>}
                                        <div className="tiny text-muted-soft mt-1">Interruzioni storiche: {dropoff}</div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MenuWizard;
