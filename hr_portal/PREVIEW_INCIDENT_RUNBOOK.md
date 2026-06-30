# Runbook operativo — Incidenti preview buste paga

## Obiettivo
Ridurre il tempo di risposta su incidenti preview (SSE/polling, worker, OCR/rendering) con controlli rapidi standardizzati.

## Trigger principali
- `alert_level = warning|critical` in `/api/hr/kpi/`.
- `fallback_rate` sopra soglia.
- `failure_rate` in crescita rispetto alla finestra precedente.

## Checklist rapida (5-10 min)
1. **Worker queue health**
   - Verificare worker online e task attivi.
   - Hint: `celery -A gestione_manutenzioni inspect active`
2. **SSE / reverse proxy**
   - Verificare buffering disabilitato (`X-Accel-Buffering: no`) e timeout upstream adeguati.
3. **OCR/rendering stack**
   - Verificare dipendenze installate e accesso storage media.
   - Hint: `python -c 'import pypdfium2; print("ok")'`
4. **DB/eventi**
   - Controllare andamento `preview_started/completed/failed/fallback` sulla finestra corrente.

## KPI target operativi
- MTTA target: **15 min**
- MTTR target: **30 min**

## Escalation
- Se `alert_level=critical` e MTTA > 15 min: escalation owner tecnico.
- Se MTTR > 30 min: aprire postmortem sintetico con root cause e action items.
