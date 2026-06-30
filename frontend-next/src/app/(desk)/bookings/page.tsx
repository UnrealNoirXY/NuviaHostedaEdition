import Link from "next/link";

interface BookingItem {
  id?: string;
  guest?: string;
  status?: string;
  eta?: string;
  nights?: number;
  note?: string;
}

interface BookingPayload {
  bookings?: BookingItem[];
  kpis?: { label: string; value: string | number; trend?: string }[];
}

async function fetchBookings(): Promise<BookingPayload | null> {
  try {
    const appOrigin = process.env.NEXT_PUBLIC_APP_ORIGIN?.trim() || "http://localhost:3000";
    const res = await fetch(new URL("/api/bookings", appOrigin).toString(), {
      next: { revalidate: 20 },
    });
    if (!res.ok) return null;
    return (await res.json()) as BookingPayload;
  } catch (error) {
    console.error("Failed to load bookings", error);
    return null;
  }
}

export default async function BookingsPage() {
  const payload = await fetchBookings();
  const bookings = payload?.bookings ?? [];
  const kpis = payload?.kpis ?? [
    { label: "Caricamento", value: "-" },
    { label: "Prenotazioni", value: bookings.length || "-" },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 text-white">
      <main className="mx-auto flex max-w-5xl flex-col gap-8 px-6 py-12">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-white/50">Bookings</p>
            <h1 className="text-3xl font-semibold">Overview prenotazioni</h1>
            <p className="mt-2 max-w-xl text-sm text-white/70">
              Lista SSR delle prenotazioni critiche con note operative. I dati arrivano dal BFF Next che proxya Django con
              cookie HttpOnly.
            </p>
          </div>
          <Link
            href="/desk"
            className="rounded-full border border-white/20 px-4 py-2 text-sm font-medium text-white transition hover:border-white/40"
          >
            Torna alla scrivania
          </Link>
        </div>

        <div className="grid gap-4 md:grid-cols-4">
          {kpis.map((kpi) => (
            <div key={kpi.label} className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="text-xs uppercase tracking-[0.2em] text-white/50">{kpi.label}</p>
              <p className="mt-3 text-2xl font-semibold text-white">{kpi.value}</p>
              {kpi.trend ? <p className="text-xs text-emerald-200">{kpi.trend}</p> : null}
            </div>
          ))}
        </div>

        <div className="overflow-hidden rounded-3xl border border-white/10 bg-black/40 shadow-[0_20px_80px_rgba(0,0,0,0.35)]">
          <div className="grid grid-cols-12 bg-white/5 px-4 py-3 text-xs uppercase tracking-[0.15em] text-white/60">
            <span className="col-span-3">Prenotazione</span>
            <span className="col-span-2">Status</span>
            <span className="col-span-2">ETA</span>
            <span className="col-span-1">Notti</span>
            <span className="col-span-4">Note</span>
          </div>
          <div>
            {bookings.length === 0 ? (
              <div className="p-6 text-sm text-white/70">Nessuna prenotazione disponibile dal backend.</div>
            ) : (
              bookings.map((item) => (
                <div
                  key={item.id ?? crypto.randomUUID()}
                  className="grid grid-cols-12 items-center border-t border-white/5 px-4 py-4 text-sm text-white/80"
                >
                  <span className="col-span-3 font-semibold text-white">{item.guest ?? item.id ?? "-"}</span>
                  <span className="col-span-2 rounded-full bg-white/10 px-3 py-1 text-center text-xs font-semibold uppercase tracking-wide">
                    {item.status ?? "-"}
                  </span>
                  <span className="col-span-2 text-white/70">{item.eta ?? "-"}</span>
                  <span className="col-span-1 text-white/70">{item.nights ?? "-"}</span>
                  <span className="col-span-4 text-white/80">{item.note ?? ""}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
