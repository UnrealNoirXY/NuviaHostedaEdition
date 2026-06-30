import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

const brandIconSrc = '/static/img/logo.png';

const buildShortcut = ({ name, shortName, description, url }) => ({
  name,
  short_name: shortName,
  description,
  url,
  icons: [
    {
      src: brandIconSrc,
      sizes: '1024x1024',
      type: 'image/png',
    },
  ],
});

const shortcuts = [
  {
    name: 'Hub Operativo',
    shortName: 'Hub',
    description: 'Accedi al quartier generale della piattaforma Nuvia.',
    url: '/hub/',
  },
  {
    name: 'Cruscotto Check-in',
    shortName: 'Check-in',
    description: 'Accedi rapidamente al cruscotto delle prenotazioni.',
    url: '/bookings/dashboard/',
  },
  {
    name: 'Analysis Center',
    shortName: 'Insights',
    description: 'Raggiungi il centro analitico per approfondimenti immediati.',
    url: '/reviews/analysis-center/',
  },
].map(buildShortcut);

const manifest = {
  id: '/nuvia/platform',
  name: 'Nuvia Platform',
  short_name: 'Nuvia',
  description: 'La piattaforma omnicanale per coordinare operations, manutenzione e analisi in mobilità.',
  theme_color: '#0f172a',
  background_color: '#030712',
  display: 'standalone',
  orientation: 'portrait-primary',
  scope: '/',
  start_url: '/hub/',
  lang: 'it-IT',
  categories: ['business', 'productivity'],
  shortcuts,
  icons: [
    {
      src: brandIconSrc,
      sizes: '1024x1024',
      type: 'image/png',
      purpose: 'any maskable',
    },
  ],
};

const pwaPlugin = VitePWA({
  registerType: 'autoUpdate',
  manifest,
  strategies: 'injectManifest',
  srcDir: 'src/pwa',
  filename: 'service-worker.js',
  injectManifest: {
    globPatterns: ['**/*.{js,css,html,ico,png,svg,json,woff2}'],
  },
  devOptions: {
    enabled: true,
    suppressWarnings: true,
  },
});

export default defineConfig({
  plugins: [react(), pwaPlugin],
  base: '/vite/',   // served via nginx alias
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {
      input: {
        main: '/src/main.jsx',
        main_styles: '/src/main.css',
        analysis_center: '/src/analysis_center_main.jsx',
        bookings_dashboard_entry: '/src/bookings_dashboard_entry.jsx',
        economato_app: '/src/economato_entry.jsx',
        maintenance_app: '/src/maintenance_entry.jsx',
        menu_generator_studio: '/src/apps/menu_generator/MenuGeneratorStudio.jsx',
        hr_portal_app: '/src/hr_portal_entry.jsx',
        landing_styles: '/src/landing.css',
        login_styles: '/src/login.css',
        financials_dashboard_styles: '/src/financials-dashboard.css',
        pwa_bootstrap: '/src/pwa/bootstrap.js',
      },
    },
  },
});
