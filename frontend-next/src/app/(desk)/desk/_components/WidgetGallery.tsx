"use client";

import { useMemo, useState } from "react";

export type Widget = {
  id: string;
  title: string;
  description: string;
  category: string;
  status: string;
  kpi?: string;
  tags?: string[];
};

type WidgetGalleryProps = {
  widgets: Widget[];
};

const filters = ["Tutti", "Operations", "Cleaning", "Experience", "Risk", "Facilities"];

export function WidgetGallery({ widgets }: WidgetGalleryProps) {
  const [activeFilter, setActiveFilter] = useState<string>("Tutti");
  const [query, setQuery] = useState<string>("");

  const filteredWidgets = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();

    return widgets.filter((widget) => {
      const matchesFilter =
        activeFilter === "Tutti" || widget.category.toLowerCase() === activeFilter.toLowerCase();

      if (!matchesFilter) return false;

      if (!normalizedQuery) return true;

      return (
        widget.title.toLowerCase().includes(normalizedQuery) ||
        widget.description.toLowerCase().includes(normalizedQuery) ||
        widget.tags?.some((tag) => tag.toLowerCase().includes(normalizedQuery))
      );
    });
  }, [widgets, activeFilter, query]);

  return (
    <section className="mt-6 space-y-4">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex flex-wrap gap-2">
          {filters.map((filter) => {
            const isActive = activeFilter === filter;
            return (
              <button
                key={filter}
                className={`rounded-full border px-4 py-2 text-sm transition hover:-translate-y-0.5 hover:border-white/40 hover:text-white ${
                  isActive
                    ? "border-white/60 bg-white/10 text-white shadow-lg"
                    : "border-white/10 bg-white/5 text-white/70"
                }`}
                onClick={() => setActiveFilter(filter)}
              >
                {filter}
              </button>
            );
          })}
        </div>
        <label className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-white/80 backdrop-blur">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth="1.5"
            stroke="currentColor"
            className="h-4 w-4"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-4.35-4.35m0 0A7.5 7.5 0 1 0 5.64 5.64a7.5 7.5 0 0 0 10.61 10.61Z"
            />
          </svg>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Cerca componenti"
            className="w-48 bg-transparent text-sm text-white placeholder:text-white/50 focus:outline-none"
          />
        </label>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {filteredWidgets.map((widget) => (
          <article
            key={widget.id}
            className="group rounded-2xl border border-white/10 bg-white/5 p-5 shadow-[0_10px_40px_rgba(0,0,0,0.2)] transition hover:-translate-y-1 hover:border-white/30 hover:bg-white/10"
          >
            <div className="flex items-start justify-between">
              <div>
                <div className="text-xs uppercase tracking-wider text-white/60">{widget.category}</div>
                <h3 className="mt-2 text-lg font-semibold text-white">{widget.title}</h3>
              </div>
              <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs font-semibold text-emerald-200">
                {widget.status}
              </span>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-white/70">{widget.description}</p>
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-white/70">
              {widget.tags?.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-white/10 px-2 py-1 text-[11px] uppercase tracking-wide text-white/80"
                >
                  {tag}
                </span>
              ))}
              {widget.kpi ? (
                <span className="ml-auto flex items-center gap-1 rounded-full bg-emerald-500/10 px-3 py-1 text-[11px] font-semibold text-emerald-100">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 24 24"
                    fill="currentColor"
                    className="h-4 w-4"
                    aria-hidden="true"
                  >
                    <path d="M4.5 15.75a.75.75 0 0 0 0 1.5h15a.75.75 0 0 0 0-1.5h-15Z" />
                    <path
                      d="m6.75 12.75 3.5-4.5 3 3.75 2.25-3 3.75 4.5"
                      stroke="currentColor"
                      strokeWidth="1.4"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      fill="none"
                    />
                  </svg>
                  {widget.kpi}
                </span>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
