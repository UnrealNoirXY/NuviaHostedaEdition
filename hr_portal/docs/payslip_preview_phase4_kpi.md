# Fase 4 KPI operativi preview

Metriche aggiunte nel payload `payslip_preview_pipeline` (`/api/hr/kpi/`):

- `avg_preview_to_confirm_minutes`: tempo medio preview→conferma.
- `first_pass_resolution_rate`: percentuale di preview confermate senza assegnazioni manuali.
- `first_pass_resolved`: conteggio assoluto conferme al primo passaggio.
- `manual_review_confirmed`: conferme che hanno richiesto assegnazioni manuali.
- `manual_assignment_errors_current`: conteggio `payslip_resolved` nella finestra KPI.
- `manual_assignment_errors_previous`: stesso conteggio nella finestra precedente equivalente.
- `manual_assignment_error_reduction_rate`: riduzione percentuale tra finestra precedente e corrente.

## Blocco di monitoraggio operativo
Il payload include anche `phase4_summary` con:
- `targets` (soglie operative),
- `status` (`ok` / `warning` per ciascun KPI Fase 4),
- `baseline` (confronto errori periodo precedente vs corrente).

Queste metriche supportano il monitoraggio richiesto nel piano Fase 4:
- tempo medio preview→conferma,
- risoluzione al primo passaggio,
- trend errori di assegnazione manuale.
