import Link from "next/link";
import { WidgetGallery, type Widget } from "./_components/WidgetGallery";

type Stat = {
  label: string;
  value: number;
  trend: number;
  trendLabel: string;
};

type Booking = {
  id: string;
  guest: string;
  status: string;
  eta: string;
  nights: number;
  note: string;
};

type Alert = {
  id: string;
  title: string;
  severity: "warning" | "critical" | "info";
  description: string;
  time: string;
};

type ScheduleItem = {
  hour: string;
  task: string;
  owner: string;
  status: "todo" | "doing" | "done";
};

type DeskLayout = {
  hero?: {
    title: string;
    subtitle: string;
    dateRange: string;
    occupancy: number;
    conciergeTasks: number;
    loyaltyGuests: number;
  };
  stats?: Stat[];
  widgets?: Widget[];
  bookings?: Booking[];
  alerts?: Alert[];
  schedule?: ScheduleItem[];
};

async function fetchDeskLayout(): Promise<DeskLayout | null> {
  try {
    const appOrigin = process.env.NEXT_PUBLIC_APP_ORIGIN?.trim() || "http://localhost:3000";
    const response = await fetch(new URL("/api/desk/layout", appOrigin).toString(), {
      next: { revalidate: 30 },
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as DeskLayout;
  } catch (error) {
    console.error("Desk layout unavailable", error);
    return null;
  }
}

const severityColor: Record<Alert["severity"], string> = {
  warning: "border-amber-400/40 bg-amber-400/10 text-amber-100",
  critical: "border-rose-400/40 bg-rose-500/10 text-rose-100",
  info: "border-sky-400/40 bg-sky-500/10 text-sky-100",
};

export default async function DeskPage() {
  const desk = await fetchDeskLayout();
  const hero =
    desk?.hero ??
    ({
      title: "Desk operativo",
      subtitle: "Backend non raggiungibile, mostra layout minimale.",
      dateRange: "-",
      occupancy: 0,
      conciergeTasks: 0,
      loyaltyGuests: 0,
    } as NonNullable<DeskLayout["hero"]>);

  const stats = desk?.stats ?? [];
  const widgets = desk?.widgets ?? [];
  const bookings = desk?.bookings ?? [];
  const alerts = desk?.alerts ?? [];
  const schedule = desk?.schedule ?? [];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 px-6 pb-16 pt-12">
        <header className="rounded-3xl border border-white/5 bg-white/5 p-8 shadow-[0_20px_80px_rgba(0,0,0,0.25)] backdrop-blur">
          <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-2">
              <p className="text-sm uppercase tracking-[0.3em] text-white/50">Desk ibrido</p>
              <h1 className="text-3xl font-semibold md:text-4xl">{hero.title}</h1>
              <p className="max-w-2xl text-base text-white/70">{hero.subtitle}</p>
              <div className="flex flex-wrap gap-3 text-sm text-white/70">
                <span className="rounded-full bg-white/10 px-3 py-1">Aggiornato: {hero.dateRange}</span>
                <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-emerald-100">
                  Occupazione {hero.occupancy}%
                </span>
                <span className="rounded-full bg-sky-500/10 px-3 py-1 text-sky-100">
                  Concierge attivi: {hero.conciergeTasks}
                </span>
                <span className="rounded-full bg-fuchsia-500/10 px-3 py-1 text-fuchsia-100">
                  Loyalty in arrivo: {hero.loyaltyGuests}
                </span>
              </div>
            </div>
            <div className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-black/30 p-4 text-sm text-white/80">
              <div className="flex items-center justify-between gap-4">
                <span>Switch esperienze</span>
                <Link
                  href="/"
                  className="rounded-full border border-white/20 px-4 py-2 text-xs font-semibold uppercase tracking-wide hover:border-white/40"
                >
                  Home shell
                </Link>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span>Progressivo rollout Next</span>
                <div className="relative h-2 flex-1 rounded-full bg-white/10">
                  <div className="absolute left-0 top-0 h-2 w-[68%] rounded-full bg-gradient-to-r from-emerald-400 to-sky-400" />
                </div>
                <span className="text-xs text-white/60">68%</span>
              </div>
              <div className="flex items-center justify-between gap-4">
                <span>Modalità mobile-first</span>
                <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold text-emerald-100">
                  Ottimizzata
                </span>
              </div>
            </div>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {stats.length === 0 ? (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-white/70 xl:col-span-4">
              Nessun dato ricevuto dal backend: verifica l&#39;API /api/desk/layout.
            </div>
          ) : (
            stats.map((stat) => {
              const positive = stat.trend >= 0;
              return (
                <div
                  key={stat.label}
                  className="rounded-2xl border border-white/5 bg-gradient-to-br from-white/5 via-white/5 to-white/0 p-5 shadow-[0_16px_60px_rgba(0,0,0,0.25)]"
              >
                <p className="text-sm text-white/60">{stat.label}</p>
                <div className="mt-2 flex items-end gap-2">
                  <span className="text-3xl font-semibold">{stat.value}</span>
                  <span
                    className={`flex items-center gap-1 rounded-full px-2 py-1 text-[11px] font-semibold uppercase ${
                      positive
                        ? "bg-emerald-400/10 text-emerald-100"
                        : "bg-rose-500/10 text-rose-100"
                    }`}
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth="1.5"
                      stroke="currentColor"
                      className="h-3 w-3"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d={positive ? "m4.5 15.75 7.5-7.5 7.5 7.5" : "m19.5 8.25-7.5 7.5-7.5-7.5"}
                      />
                    </svg>
                    {Math.abs(stat.trend)}%
                  </span>
                </div>
                <p className="mt-1 text-xs text-white/60">{stat.trendLabel}</p>
              </div>
            );
            })
          )}
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-white/5 bg-white/5 p-6 shadow-[0_20px_80px_rgba(0,0,0,0.25)]">
            <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-white/50">Prenotazioni</p>
                <h2 className="text-xl font-semibold">Monitor live</h2>
              </div>
              <Link href="/bookings" className="text-sm text-emerald-200 underline underline-offset-4">
                Apri vista completa
              </Link>
            </div>
            <div className="mt-4 divide-y divide-white/5">
              {bookings.length === 0 ? (
                <div className="py-6 text-sm text-white/70">Nessuna prenotazione caricata dal BFF.</div>
              ) : (
                bookings.map((booking) => (
                  <div key={booking.id} className="flex flex-col gap-1 py-3 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-white">{booking.guest}</p>
                      <p className="text-xs text-white/60">{booking.note}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs">
                      <span className="rounded-full bg-white/10 px-3 py-1 text-white/80">{booking.status}</span>
                      <span className="rounded-full bg-white/5 px-3 py-1 text-white/60">ETA {booking.eta}</span>
                      <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-emerald-100">{booking.nights} notti</span>
                      <span className="rounded-full bg-white/10 px-3 py-1 text-white/70">{booking.id}</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-3xl border border-white/5 bg-white/5 p-6 shadow-[0_20px_80px_rgba(0,0,0,0.25)]">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Agenda prossime 2h</h2>
                <span className="text-xs uppercase tracking-[0.2em] text-white/50">Sync live</span>
              </div>
              <div className="mt-4 space-y-3">
                {schedule.length === 0 ? (
                  <p className="text-sm text-white/70">Nessuna attività pianificata disponibile.</p>
                ) : (
                  schedule.map((item) => (
                    <div
                      key={`${item.hour}-${item.task}`}
                      className="flex items-center gap-3 rounded-2xl border border-white/5 bg-black/30 px-3 py-3"
                    >
                      <span className="rounded-xl bg-white/5 px-3 py-2 font-mono text-sm text-white/80">{item.hour}</span>
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-semibold text-white">{item.task}</p>
                        <p className="text-xs text-white/60">{item.owner}</p>
                      </div>
                      <span
                        className={`rounded-full px-3 py-1 text-[11px] font-semibold uppercase ${
                          item.status === "done"
                            ? "bg-emerald-500/10 text-emerald-100"
                            : item.status === "doing"
                              ? "bg-sky-500/10 text-sky-100"
                              : "bg-white/10 text-white/70"
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="rounded-3xl border border-white/5 bg-white/5 p-6 shadow-[0_20px_80px_rgba(0,0,0,0.25)]">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Avvisi</h2>
                <span className="text-xs uppercase tracking-[0.2em] text-white/50">Priorità</span>
              </div>
              <div className="mt-4 space-y-3">
                {alerts.length === 0 ? (
                  <p className="text-sm text-white/70">Nessun alert disponibile dal backend.</p>
                ) : (
                  alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className={`rounded-2xl border px-3 py-3 ${severityColor[alert.severity]} flex items-start gap-3`}
                    >
                      <div className="mt-1 h-2 w-2 rounded-full bg-white/70" />
                      <div className="flex-1 space-y-1">
                        <p className="text-sm font-semibold text-white">{alert.title}</p>
                        <p className="text-xs text-white/80">{alert.description}</p>
                        <p className="text-[11px] uppercase tracking-wide text-white/60">{alert.time}</p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-white/5 bg-gradient-to-br from-white/5 via-white/5 to-white/0 p-6 shadow-[0_20px_80px_rgba(0,0,0,0.25)]">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.3em] text-white/50">Componenti riutilizzabili</p>
              <h2 className="text-xl font-semibold">Widget gallery</h2>
            </div>
            <span className="text-xs text-white/60">Caricati da BFF /api/desk/layout</span>
          </div>
          {widgets.length === 0 ? (
            <div className="mt-4 rounded-2xl border border-white/10 bg-black/30 p-6 text-sm text-white/70">
              Nessun widget ricevuto: controlla la reachability del backend.
            </div>
          ) : (
            <WidgetGallery widgets={widgets} />
          )}
        </section>
      </div>
    </div>
  );
}
