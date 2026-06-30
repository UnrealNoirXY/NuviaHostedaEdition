import Link from "next/link";

const quickActions = [
  {
    title: "Desk ibrido",
    href: "/desk",
    description: "Pannello SSR con componenti idratati solo dove serve.",
  },
  {
    title: "Prenotazioni",
    href: "/bookings",
    description: "Vista SSR che legge il BFF Next e rende i dati server-side.",
  },
  {
    title: "Economato",
    href: "/economato",
    description: "Magazzino e alert serviti tramite route handler Next.",
  },
  {
    title: "Manifest PWA",
    href: "/manifest.webmanifest",
    description: "Asset fingerprintati, cache coerenti e fallback offline.",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white">
      <main className="mx-auto flex max-w-5xl flex-col gap-10 px-6 pb-16 pt-16">
        <section className="rounded-3xl border border-white/5 bg-white/5 p-10 shadow-[0_20px_80px_rgba(0,0,0,0.25)] backdrop-blur">
          <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div className="space-y-4">
              <p className="text-sm uppercase tracking-[0.3em] text-white/50">Next.js + Django</p>
              <h1 className="text-4xl font-semibold leading-tight md:text-5xl">
                Shell SSR pronta per il rollout mobile-first
              </h1>
              <p className="max-w-2xl text-lg text-white/70">
                Shell SSR che sostituisce la build Vite fragile: BFF Next con caching SWR, middleware di autenticazione
                condivisa e PWA integrata per evitare schermate vuote e migliorare SEO.
              </p>
              <div className="flex flex-wrap gap-3 text-sm text-white/70">
                <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-emerald-100">App Router</span>
                <span className="rounded-full bg-sky-500/10 px-3 py-1 text-sky-100">Route handlers BFF</span>
                <span className="rounded-full bg-fuchsia-500/10 px-3 py-1 text-fuchsia-100">PWA ready</span>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/desk"
                  className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:-translate-y-1"
                >
                  Apri la scrivania SSR
                </Link>
                <a
                  href="https://nextjs.org/blog/next-15"
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-full border border-white/20 px-5 py-3 text-sm font-semibold text-white transition hover:border-white/40"
                >
                  Roadmap Next 15
                </a>
              </div>
            </div>
            <div className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-black/30 p-6 text-sm text-white/80">
              <div className="flex items-center justify-between">
                <span>Middleware auth</span>
                <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold text-emerald-100">Refresh</span>
              </div>
              <div className="flex items-center justify-between">
                <span>next-pwa</span>
                <span className="rounded-full bg-sky-500/10 px-3 py-1 text-[11px] font-semibold text-sky-100">Configurato</span>
              </div>
              <div className="flex items-center justify-between">
                <span>Rewrites</span>
                <span className="rounded-full bg-white/10 px-3 py-1 text-[11px] font-semibold text-white/80">BFF proxied</span>
              </div>
              <div className="flex items-center justify-between">
                <span>UI streaming</span>
                <span className="rounded-full bg-fuchsia-500/10 px-3 py-1 text-[11px] font-semibold text-fuchsia-100">
                  React 19
                </span>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3">
          {quickActions.map((action) => (
            <Link
              key={action.href}
              href={action.href}
              className="rounded-2xl border border-white/10 bg-white/5 p-6 shadow-[0_16px_60px_rgba(0,0,0,0.25)] transition hover:-translate-y-1 hover:border-white/30 hover:bg-white/10"
            >
              <p className="text-xs uppercase tracking-[0.2em] text-white/50">Azioni</p>
              <h3 className="mt-2 text-lg font-semibold text-white">{action.title}</h3>
              <p className="mt-2 text-sm text-white/70">{action.description}</p>
            </Link>
          ))}
        </section>

        <section className="rounded-3xl border border-white/5 bg-white/5 p-8 shadow-[0_20px_80px_rgba(0,0,0,0.25)]">
          <h2 className="text-xl font-semibold text-white">Prossimi passi del piano</h2>
          <p className="mt-2 text-sm text-white/70">
            Sezioni booking/analysis/economato già SSR; completato il manifest centralizzato e il fallback offline. Il rollout è
            pronto con route handler che proxano Django mantenendo i cookie HttpOnly.
          </p>
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm font-semibold text-white">BFF API</p>
              <p className="text-xs text-white/70">Normalizzare errori, caching SWR e forwarding cookie HttpOnly.</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4">
              <p className="text-sm font-semibold text-white">CI/CD</p>
              <p className="text-xs text-white/70">Lint, test e build Next + deploy container dietro CDN con rollback sicuro.</p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
