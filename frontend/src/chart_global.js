// Espone Chart.js (bundlato, versione pinnata in package.json) come globale window.Chart
// per i template server-rendered che usano `new Chart(...)`.
// Sostituisce il caricamento da CDN esterno (fragile: si rompe se il CDN è bloccato,
// frequente nelle reti aziendali, e non è pinnato a una versione).
import Chart from 'chart.js/auto';

window.Chart = Chart;

export default Chart;
