import Link from "next/link";

interface SupplyItem {
  name?: string;
  level?: string;
  eta?: string;
  owner?: string;
}

interface EconomatoPayload {
  supplies?: SupplyItem[];
  alerts?: { title: string; severity?: "warning" | "critical" | "info"; description?: string }[];
}

async function fetchEconomato(): Promise<EconomatoPayload | null> {
  try {
    const appOrigin = process.env.NEXT_PUBLIC_APP_ORIGIN?.trim() || "http://localhost:3000";
    const res = await fetch(new URL("/api/economato", appOrigin).toString(), {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return (await res.json()) as EconomatoPayload;
  } catch (error) {
    console.error("Failed to load economato", error);
    return null;
  }
}

const severityClass: Record<string, string> = {
  critical: "bg-rose-500/10 text-rose-100", 
  warning: "bg-amber-500/10 text-amber-100",
  info: "bg-sky-500/10 text-sky-100",
};

export default async function EconomatoPage() {
  const payload = await fetchEconomato();
  const supplies = payload?.supplies ?? [];
  const alerts = payload?.alerts ?? [];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white">
      <main className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-12">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-white/50">Economato</p>
            <h1 className="text-3xl font-semibold">Magazzino e forniture</h1>
            <p className="mt-2 max-w-xl text-sm text-white/70">
              Disponibilità e alert provenienti dal backend Django via BFF Next. Pagina SSR ottimizzata per mobile e desktop.
            </p>
          </div>
          <Link
            href="/desk"
            className="rounded-full border border-white/20 px-4 py-2 text-sm font-medium text-white transition hover:border-white/40"
          >
            Torna alla scrivania
          </Link>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-3xl border border-white/10 bg-black/40 p-6 shadow-[0_20px_80px_rgba(0,0,0,0.35)]">
            <div className="flex items-center justify-between">
              <p className="text-sm uppercase tracking-[0.2em] text-white/50">Disponibilità</p>
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white">SSR</span>
            </div>
            <div className="mt-4 space-y-3">
              {supplies.length === 0 ? (
                <p className="text-sm text-white/70">Nessun dato disponibile dal backend.</p>
              ) : (
                supplies.map((supply) => (
                  <div
                    key={supply.name ?? crypto.randomUUID()}
                    className="flex items-center justify-between rounded-2xl border border-white/5 bg-white/5 px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-semibold text-white">{supply.name}</p>
                      <p className="text-xs text-white/60">{supply.owner ?? ""}</p>
                    </div>
                    <div className="text-right text-sm text-white/80">
                      <p>{supply.level ?? "-"}</p>
                      <p className="text-xs text-white/50">ETA {supply.eta ?? "-"}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="rounded-3xl border border-white/10 bg-black/40 p-6 shadow-[0_20px_80px_rgba(0,0,0,0.35)]">
            <div className="flex items-center justify-between">
              <p className="text-sm uppercase tracking-[0.2em] text-white/50">Alert</p>
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold text-white">Monitor</span>
            </div>
            <div className="mt-4 space-y-3">
              {alerts.length === 0 ? (
                <p className="text-sm text-white/70">Nessun alert dal backend.</p>
              ) : (
                alerts.map((alert) => (
                  <div
                    key={alert.title ?? crypto.randomUUID()}
                    className="rounded-2xl border border-white/5 bg-white/5 px-4 py-3"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-white">{alert.title}</p>
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${
                          severityClass[alert.severity ?? "info"] ?? severityClass.info
                        }`}
                      >
                        {alert.severity ?? "info"}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-white/70">{alert.description}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
