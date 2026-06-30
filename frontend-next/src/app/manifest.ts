import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Desk Unificato",
    short_name: "Desk",
    description: "Frontend Next.js SSR con BFF per Django e caching PWA coerente.",
    start_url: "/",
    display: "standalone",
    background_color: "#030712",
    theme_color: "#0ea5e9",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "maskable",
      },
    ],
    shortcuts: [
      {
        name: "Scrivania",
        url: "/desk",
      },
      {
        name: "Prenotazioni",
        url: "/bookings",
      },
      {
        name: "Economato",
        url: "/economato",
      },
    ],
    screenshots: [
      {
        src: "/screens/desk-light.png",
        sizes: "1280x720",
        type: "image/png",
        form_factor: "wide",
      },
    ],
  };
}
