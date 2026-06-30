export const metadata = {
  title: "Offline",
};

export default function OfflinePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-950 px-6 text-center text-white">
      <div className="max-w-md space-y-4 rounded-3xl border border-white/10 bg-white/5 p-8 shadow-[0_20px_80px_rgba(0,0,0,0.35)]">
        <p className="text-xs uppercase tracking-[0.2em] text-white/50">Offline</p>
        <h1 className="text-2xl font-semibold">Connessione assente</h1>
        <p className="text-sm text-white/70">
          Non riesci a raggiungere il backend. Riprova quando sei online: il service worker manterrà cache coerente degli asset
          e delle ultime pagine SSR visitate.
        </p>
        <div className="rounded-2xl border border-white/10 bg-black/40 p-4 text-left text-xs text-white/70">
          <p className="font-semibold text-white">Suggerimenti</p>
          <ul className="mt-2 space-y-1 list-disc pl-4">
            <li>Verifica la connessione di rete o VPN.</li>
            <li>Assicurati che il backend Django sia raggiungibile.</li>
            <li>Ricarica la pagina per ripristinare la sessione.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
