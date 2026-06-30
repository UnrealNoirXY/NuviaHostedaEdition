import Link from "next/link";

interface InsightCard {
  title?: string;
  delta?: string;
  description?: string;
}

interface AnalysisPayload {
  insights?: InsightCard[];
  charts?: { title: string; value: string }[];
}

async function fetchInsights(): Promise<AnalysisPayload | null> {
  try {
    const appOrigin = process.env.NEXT_PUBLIC_APP_ORIGIN?.trim() || "http://localhost:3000";
    const res = await fetch(new URL("/api/analysis", appOrigin).toString(), {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return (await res.json()) as AnalysisPayload;
  } catch (error) {
    console.error("Failed to load analysis", error);
    return null;
  }
}

export default async function AnalysisPage() {
  const payload = await fetchInsights();
  const insights = payload?.insights ?? [];
  const charts = payload?.charts ?? [
    { title: "ADR", value: "-" },
    { title: "Occupancy", value: "-" },
    { title: "RevPAR", value: "-" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white">
      <main className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-12">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-white/50">Analysis</p>
            <h1 className="text-3xl font-semibold">Performance e trend</h1>
            <p className="mt-2 max-w-xl text-sm text-white/70">
              Sezione SSR con insight provenienti da Django via BFF Next. Ideale per dispositivi lenti grazie allo streaming
              server-side.
            </p>
          </div>
          <Link
            href="/desk"
            className="rounded-full border border-white/20 px-4 py-2 text-sm font-medium text-white transition hover:border-white/40"
          >
            Torna alla scrivania
          </Link>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {charts.map((chart) => (
            <div key={chart.title} className="rounded-2xl border border-white/10 bg-white/5 p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-white/50">{chart.title}</p>
              <p className="mt-4 text-3xl font-semibold text-white">{chart.value}</p>
              <p className="mt-2 text-xs text-white/60">Aggiornamento live dal backend</p>
            </div>
          ))}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {insights.length === 0 ? (
            <div className="rounded-3xl border border-white/10 bg-black/40 p-6 text-sm text-white/70">
              Nessun insight disponibile: controlla le API del backend.
            </div>
          ) : (
            insights.map((insight) => (
              <div
                key={insight.title ?? crypto.randomUUID()}
                className="rounded-3xl border border-white/10 bg-black/40 p-6 shadow-[0_16px_60px_rgba(0,0,0,0.35)]"
              >
                <div className="flex items-center justify-between">
                  <p className="text-lg font-semibold text-white">{insight.title}</p>
                  {insight.delta ? (
                    <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-semibold text-emerald-100">
                      {insight.delta}
                    </span>
                  ) : null}
                </div>
                <p className="mt-3 text-sm text-white/70">{insight.description}</p>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}
