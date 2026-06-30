import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Desk ibrido | Next + Django",
  description: "Shell SSR con BFF Next, middleware di autenticazione e componenti pronti per il rollout mobile-first.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="it">
      <body className="antialiased bg-slate-950">{children}</body>
    </html>
  );
}
