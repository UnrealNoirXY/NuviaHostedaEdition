import React from 'react';
import axios from 'axios';
import { Line, Bar, Pie } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    LineElement,
    BarElement,
    ArcElement,
    Title,
    Tooltip,
    Legend,
} from 'chart.js';

import './AnalysisCenter.css';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const VeratourCrossAnalysisWidget = ({ data }) => {
    if (!data || !data.cross_analysis) return null;

    return (
        <div className="veratour-cross-analysis mt-4">
            <h4 className="mb-3"><i className="fas fa-balance-scale me-2"></i>Comparazione Reparti (Report vs IA)</h4>
            <div className="table-responsive">
                <table className="table noir-table align-middle">
                    <thead>
                        <tr>
                            <th>Reparto</th>
                            <th className="text-center">Report (+%)</th>
                            <th className="text-center">IA Sentiment (+%)</th>
                            <th className="text-center">Gap Negativo</th>
                            <th className="text-center">Commenti</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.cross_analysis.map((item) => (
                            <tr key={item.department} className={item.critical ? 'table-danger-soft' : item.alert ? 'table-warning-soft' : ''}>
                                <td className="fw-bold">{item.department}</td>
                                <td className="text-center">{item.report_pos}%</td>
                                <td className="text-center">{item.ia_pos}%</td>
                                <td className={`text-center fw-bold ${item.gap > 10 ? 'text-danger' : item.gap > 5 ? 'text-warning' : 'text-success'}`}>
                                    {item.gap > 0 ? `+${item.gap}` : item.gap}%
                                    {item.critical && <i className="fas fa-circle-exclamation ms-2" title="Discrepanza Critica"></i>}
                                </td>
                                <td className="text-center">
                                    <span className="badge rounded-pill bg-secondary">{item.count}</span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            {(data.cross_analysis.some(i => i.alert)) && (
                <div className="alert alert-noir-warning d-flex align-items-center mt-3">
                    <i className="fas fa-lightbulb me-3 fa-2x"></i>
                    <div>
                        <strong>Attenzione:</strong> I reparti evidenziati mostrano una discrepanza tra i giudizi del Report e l'analisi IA dei testi. Il feedback testuale risulta più critico.
                    </div>
                </div>
            )}
        </div>
    );
};

const KPISummaryWidget = ({ data, hasQuery, isVeratourOnly }) => {
    if (!data || !data.current) {
        return <div className="analysis-loading">Caricamento...</div>;
    }

    if (data.current.total_reviews === 0 && hasQuery) {
        return <div className="analysis-empty">Nessun dato trovato per questo termine di ricerca.</div>;
    }

    const veratour = data.veratour || {};

    const calculateDelta = (curr, prev) => {
        if (!prev) return null;
        const diff = curr - prev;
        const percent = ((diff / prev) * 100).toFixed(1);
        return {
            diff: diff.toFixed(2),
            percent,
            isPositive: diff >= 0
        };
    };

    const kpis = [
        {
            label: 'Recensioni totali',
            value: data.current.total_reviews,
            icon: 'fa-comments',
            delta: calculateDelta(data.current.total_reviews, data.previous.total_reviews)
        },
        {
            label: 'Rating medio',
            value: Number(data.current.average_rating).toFixed(1),
            icon: 'fa-star',
            delta: calculateDelta(data.current.average_rating, data.previous.average_rating)
        },
        {
            label: 'Sentiment medio',
            value: Number(data.current.average_sentiment).toFixed(1),
            icon: 'fa-face-smile',
            delta: calculateDelta(data.current.average_sentiment, data.previous.average_sentiment)
        },
    ];

    if (isVeratourOnly && veratour.response_rate !== null && veratour.response_rate !== undefined) {
        kpis.push({
            label: 'Tasso di Commento',
            value: `${veratour.response_rate}%`,
            icon: 'fa-paper-plane',
            delta: null,
            subLabel: veratour.sample_reliability
        });
    }

    if (data.current.anomalies_count > 0) {
        kpis.push({
            label: 'Anomalie Rilevate',
            value: data.current.anomalies_count,
            icon: 'fa-triangle-exclamation text-danger',
            delta: null,
            isAnomaly: true
        });
    }

    return (
        <div className="analysis-kpi-grid">
            {isVeratourOnly && veratour.critical_alert && (
                <div className={`analysis-alert-card ${veratour.critical_alert.level === 'critical' ? 'is-critical' : 'is-warning'} w-100 mb-3`} style={{ gridColumn: '1 / -1' }}>
                    <div className="analysis-alert-header">
                        <i className={`fa-solid ${veratour.critical_alert.level === 'critical' ? 'fa-triangle-exclamation text-danger' : 'fa-circle-exclamation text-warning'} me-2`}></i>
                        <strong>{veratour.critical_alert.title}</strong>
                    </div>
                    <div className="analysis-alert-body mt-1">
                        {veratour.critical_alert.message}
                    </div>
                </div>
            )}
            {kpis.map((kpi) => (
                <article className="analysis-kpi-card" key={kpi.label}>
                    <div className="analysis-kpi-main">
                        <span className="analysis-kpi-icon">
                            <i className={`fa-solid ${kpi.icon}`} aria-hidden="true" />
                        </span>
                        <div className="analysis-kpi-info">
                            <span className="analysis-kpi-value">{kpi.value}</span>
                            <span className="analysis-kpi-label">
                                {kpi.label}
                                {kpi.subLabel && <div className="text-muted-soft small" style={{fontSize: '0.7rem'}}>{kpi.subLabel}</div>}
                            </span>
                        </div>
                    </div>
                    {kpi.delta && (
                        <div className={`analysis-kpi-delta ${kpi.delta.isPositive ? 'is-positive' : 'is-negative'}`}>
                            <i className={`fa-solid fa-arrow-${kpi.delta.isPositive ? 'up' : 'down'}`}></i>
                            <span>{Math.abs(kpi.delta.percent)}%</span>
                            <span className="analysis-kpi-delta-label">vs anno prec.</span>
                        </div>
                    )}
                </article>
            ))}
        </div>
    );
};

const TrendChartWidget = React.forwardRef(({ data, hasQuery }, ref) => {
    if (!data) {
        return <div className="analysis-loading">Caricamento...</div>;
    }

    if ((!data.labels || data.labels.length === 0) && hasQuery) {
        return <div className="analysis-empty">Nessun trend disponibile per i criteri selezionati.</div>;
    }

    const chartData = {
        labels: data.labels,
        datasets: data.datasets.map((ds, index) => {
            const base = { ...ds };
            if (index === 0) {
                base.borderColor = 'rgb(75, 192, 192)';
                base.backgroundColor = 'rgba(75, 192, 192, 0.5)';
            } else if (index === 1) {
                base.borderColor = 'rgb(255, 99, 132)';
                base.backgroundColor = 'rgba(255, 99, 132, 0.5)';
            } else if (index === 2) {
                base.type = 'bar';
                base.borderColor = 'rgb(54, 162, 235)';
                base.backgroundColor = 'rgba(54, 162, 235, 0.5)';
            } else if (index === 3) { // Rating Anno Prec
                base.borderColor = 'rgba(75, 192, 192, 0.3)';
                base.backgroundColor = 'transparent';
                base.borderDash = [5, 5];
            } else if (index === 4) { // Sentiment Anno Prec
                base.borderColor = 'rgba(255, 99, 132, 0.3)';
                base.backgroundColor = 'transparent';
                base.borderDash = [5, 5];
            } else if (ds.label === 'Occupazione (%)') {
                base.borderColor = 'rgba(156, 163, 175, 0.5)';
                base.backgroundColor = 'rgba(156, 163, 175, 0.2)';
            }
            return base;
        }),
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
            'y-axis-rating': {
                type: 'linear',
                position: 'left',
                title: {
                    display: true,
                    text: 'Rating'
                }
            },
            'y-axis-sentiment': {
                type: 'linear',
                position: 'right',
                title: {
                    display: true,
                    text: 'Sentiment'
                },
                grid: {
                    drawOnChartArea: false,
                },
            },
            'y-axis-count': {
                type: 'linear',
                position: 'right',
                title: {
                    display: true,
                    text: 'N. Recensioni'
                },
                grid: {
                    drawOnChartArea: false,
                },
                ticks: {
                    precision: 0
                }
            },
            'y-axis-occupancy': {
                type: 'linear',
                position: 'left',
                display: false, // Hidden but used for scaling if needed, or overlayed
                min: 0,
                max: 100,
                grid: {
                    drawOnChartArea: false,
                },
            }
        },
    };

    return <Line ref={ref} data={chartData} options={options} />;
});

const PlatformComparisonWidget = React.forwardRef(({ data }, ref) => {
    if (!data) {
        return <div className="analysis-loading">Caricamento...</div>;
    }

    const chartData = {
        labels: data.labels,
        datasets: [
            {
                ...data.datasets[0], // Numero di Recensioni
                backgroundColor: 'rgba(54, 162, 235, 0.5)',
            },
            {
                ...data.datasets[1], // Valutazione Media
                backgroundColor: 'rgba(255, 206, 86, 0.5)',
            },
        ],
    };

    const options = {
        responsive: true,
    }

    return <Bar ref={ref} data={chartData} options={options} />;
});

const ThematicAnalysisWidget = React.forwardRef(({ data }, ref) => {
    if (!data || !data.labels || data.labels.length === 0) {
        return <div className="analysis-empty">Nessun dato tematico da analizzare per i filtri selezionati.</div>;
    }

    const chartData = {
        labels: data.labels,
        datasets: [
            {
                ...data.datasets[0],
                backgroundColor: 'rgba(153, 102, 255, 0.5)',
            },
        ],
    };

    const options = {
        indexAxis: 'y', // To make it a horizontal bar chart
        responsive: true,
        plugins: {
            legend: {
                display: false,
            },
        },
    };

    return <Bar ref={ref} data={chartData} options={options} />;
});

const palette = [
    '#2563eb',
    '#f97316',
    '#22c55e',
    '#a855f7',
    '#ef4444',
    '#06b6d4',
    '#facc15',
    '#4b5563',
    '#8b5cf6',
    '#14b8a6',
];

const RatingDistributionWidget = React.forwardRef(({ data }, ref) => {
    const [selectedPlatform, setSelectedPlatform] = React.useState('overall');
    const [mode, setMode] = React.useState('analitica'); // 'analitica' o 'sintetica'

    React.useEffect(() => {
        if (!data) {
            return;
        }

        const availablePlatforms = ['overall', ...data.platforms.map((platform) => platform.name)];
        if (!availablePlatforms.includes(selectedPlatform)) {
            setSelectedPlatform('overall');
        }
    }, [data, selectedPlatform]);

    if (!data) {
        return <div className="analysis-loading">Caricamento...</div>;
    }

    const formatDate = (dateString) => {
        if (!dateString) {
            return '—';
        }

        const date = new Date(dateString);
        if (Number.isNaN(date.getTime())) {
            return dateString;
        }

        return date.toLocaleDateString();
    };

    const handlePlatformChange = (event) => {
        setSelectedPlatform(event.target.value);
    };

    const findPlatformData = () => {
        if (selectedPlatform === 'overall') {
            return {
                name: 'Tutte le piattaforme',
                ...data.overall,
            };
        }

        return data.platforms.find((platform) => platform.name === selectedPlatform) || {
            name: selectedPlatform,
            labels: [],
            current_counts: [],
            previous_counts: [],
            totals: { current: 0, previous: 0 },
        };
    };

    const platformData = findPlatformData();
    const { labels: rawLabels, current_counts: rawCurrentCounts, previous_counts: rawPreviousCounts, totals } = platformData;

    const getSinteticaData = () => {
        const clusters = [
            { label: 'Rosso (1-2)', range: [1, 2], color: '#dc2626' },
            { label: 'Arancione (3-4)', range: [3, 4], color: '#f97316' },
            { label: 'Giallo (5-6)', range: [5, 6], color: '#facc15' },
            { label: 'Verde Chiaro (7-8)', range: [7, 8], color: '#84cc16' },
            { label: 'Verde Scuro (9-10)', range: [9, 10], color: '#16a34a' },
        ];

        const clusterCurrent = clusters.map(() => 0);
        const clusterPrevious = clusters.map(() => 0);

        rawLabels.forEach((label, idx) => {
            const rating = parseInt(label, 10);
            const clusterIdx = clusters.findIndex(c => rating >= c.range[0] && rating <= c.range[1]);
            if (clusterIdx !== -1) {
                clusterCurrent[clusterIdx] += rawCurrentCounts[idx] || 0;
                clusterPrevious[clusterIdx] += rawPreviousCounts[idx] || 0;
            }
        });

        return {
            labels: clusters.map(c => c.label),
            currentCounts: clusterCurrent,
            previousCounts: clusterPrevious,
            colors: clusters.map(c => c.color)
        };
    };

    const isSintetica = mode === 'sintetica';
    const processedData = isSintetica ? getSinteticaData() : {
        labels: rawLabels,
        currentCounts: rawCurrentCounts,
        previousCounts: rawPreviousCounts,
        colors: rawLabels.map((_, index) => palette[index % palette.length])
    };

    const { labels, currentCounts, previousCounts } = processedData;

    const totalsDifference = totals.current - totals.previous;
    const totalsDifferenceClass = totalsDifference > 0
        ? 'analysis-rating-diff-positive'
        : totalsDifference < 0
            ? 'analysis-rating-diff-negative'
            : '';
    const totalsDifferenceLabel = totalsDifference > 0 ? `+${totalsDifference}` : totalsDifference;

    const pieChartData = {
        labels,
        datasets: [
            {
                data: currentCounts,
                backgroundColor: processedData.colors,
                borderWidth: 1,
            },
        ],
    };

    const pieOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom',
            },
        },
    };

    return (
        <div className="analysis-rating-distribution">
            <div className="analysis-rating-controls">
                <div className="analysis-rating-summary">
                    <div>
                        <label htmlFor="analysis-rating-platform" className="form-label mb-0">
                            Piattaforma
                        </label>
                        <select
                            id="analysis-rating-platform"
                            className="form-select"
                            value={selectedPlatform}
                            onChange={handlePlatformChange}
                        >
                            <option value="overall">Tutte le piattaforme</option>
                            {data.platforms.map((platform) => (
                                <option key={platform.name} value={platform.name}>
                                    {platform.name}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="form-label mb-0">Modalità</label>
                        <div className="btn-group w-100" role="group">
                            <button
                                type="button"
                                className={`btn btn-sm ${mode === 'analitica' ? 'btn-primary' : 'btn-outline-primary'}`}
                                onClick={() => setMode('analitica')}
                            >
                                Analitica
                            </button>
                            <button
                                type="button"
                                className={`btn btn-sm ${mode === 'sintetica' ? 'btn-primary' : 'btn-outline-primary'}`}
                                onClick={() => setMode('sintetica')}
                            >
                                Sintetica
                            </button>
                        </div>
                    </div>
                    <div className="analysis-rating-period">
                        <p className="mb-0">
                            Periodo attuale: <strong>{formatDate(data.current_period.start)}</strong>
                            {' '}→{' '}
                            <strong>{formatDate(data.current_period.end)}</strong>
                        </p>
                        <p className="mb-0">
                            Periodo anno precedente: <strong>{formatDate(data.previous_period.start)}</strong>
                            {' '}→{' '}
                            <strong>{formatDate(data.previous_period.end)}</strong>
                        </p>
                    </div>
                </div>
            </div>
            <div className="analysis-rating-content">
                <div className="analysis-rating-chart">
                    {totals.current > 0 ? (
                        <Pie ref={ref} data={pieChartData} options={pieOptions} />
                    ) : (
                        <div className="analysis-empty">Nessuna recensione nel periodo selezionato.</div>
                    )}
                </div>
                <div className="analysis-rating-table">
                    <div className="table-responsive">
                        <table className="table table-sm align-middle">
                            <thead>
                                <tr>
                                    <th scope="col">Valutazione</th>
                                    <th scope="col">Periodo attuale</th>
                                    <th scope="col">Anno precedente</th>
                                    <th scope="col">Differenza</th>
                                </tr>
                            </thead>
                            <tbody>
                                {labels.map((label, index) => {
                                    const currentValue = currentCounts[index] || 0;
                                    const previousValue = previousCounts[index] || 0;
                                    const difference = currentValue - previousValue;
                                    const differenceClass = difference > 0
                                        ? 'analysis-rating-diff-positive'
                                        : difference < 0
                                            ? 'analysis-rating-diff-negative'
                                            : '';

                                    return (
                                        <tr key={`rating-${label}`}>
                                            <th scope="row">{label}</th>
                                            <td>{currentValue}</td>
                                            <td>{previousValue}</td>
                                            <td className={differenceClass}>
                                                {difference > 0 ? `+${difference}` : difference}
                                            </td>
                                        </tr>
                                    );
                                })}
                                <tr>
                                    <th scope="row">Totale</th>
                                    <td><strong>{totals.current}</strong></td>
                                    <td><strong>{totals.previous}</strong></td>
                                    <td className={totalsDifferenceClass}>{totalsDifferenceLabel}</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
});

const RatingDisplay = ({ rating, source }) => {
    const isFiveScale = ['Google', 'Tripadvisor'].some(s => source && source.toLowerCase().includes(s.toLowerCase()));
    const max = isFiveScale ? 5 : 10;

    if (isFiveScale) {
        return (
            <span className="analysis-review-rating-stars" aria-label={`Rating ${rating} su 5`}>
                {[...Array(5)].map((_, i) => (
                    <i
                        key={i}
                        className={`fa-star ${i < Math.floor(rating) ? 'fa-solid' : 'fa-regular'}`}
                        style={{ color: '#f59e0b' }}
                    />
                ))}
                <span className="ms-2 fw-bold">{rating}/5</span>
            </span>
        );
    }

    return (
        <span className="analysis-review-rating-numeric">
            <span className="badge bg-warning text-dark fs-6">{rating} / 10</span>
        </span>
    );
};

const ReviewDetailModal = ({ review, onClose }) => {
    if (!review) return null;

    const isVeratour = review.source__name === 'Veratour';

    return (
        <div className="noir-modal-overlay" onClick={onClose}>
            <div className="noir-modal-content" onClick={e => e.stopPropagation()}>
                <header className="noir-modal-header">
                    <div className="d-flex justify-content-between align-items-start w-100">
                        <div>
                            <h3 className="mb-1">{review.author || 'Autore Anonimo'}</h3>
                            <div className="text-muted-soft small">
                                <i className="fa-regular fa-calendar me-1"></i>
                                {new Date(review.review_date).toLocaleDateString()}
                                <span className="mx-2">•</span>
                                <i className="fa-solid fa-globe me-1"></i>
                                {review.source__name}
                                <span className="mx-2">•</span>
                                <i className="fa-solid fa-location-dot me-1"></i>
                                {review.resort__name}
                            </div>
                        </div>
                        <button className="btn-close-noir" onClick={onClose}>
                            <i className="fa-solid fa-xmark"></i>
                        </button>
                    </div>
                    <div className="mt-3">
                        <RatingDisplay rating={review.rating} source={review.source__name} />
                    </div>
                </header>

                <div className="noir-modal-body">
                    {review.analysis__is_anomaly && (
                        <div className="alert alert-danger d-flex align-items-center mb-4">
                            <i className="fa-solid fa-triangle-exclamation fa-2x me-3"></i>
                            <div>
                                <strong>Attenzione: Discrepanza rilevata tra voto e testo.</strong><br/>
                                L'IA ha identificato un sentiment che non corrisponde alla valutazione numerica fornita.
                            </div>
                        </div>
                    )}

                    <div className="review-text-container mb-4">
                        <h5 className="text-uppercase small fw-bold text-muted mb-2">Testo Integrale</h5>
                        <p className="review-text-full">{review.text}</p>
                    </div>

                    {isVeratour && review.analysis__keywords && review.analysis__keywords.length > 0 && (
                        <div className="veratour-analysis-section p-3 rounded-4 bg-light-soft border border-light">
                            <h5 className="text-uppercase small fw-bold text-muted mb-3">Analisi Veratour</h5>
                            <div className="mb-3">
                                <span className="small text-muted d-block mb-1">Reparti individuati:</span>
                                <div className="d-flex flex-wrap gap-2">
                                    {review.analysis__keywords.map((tag, idx) => (
                                        <span key={idx} className="badge bg-primary-soft text-primary border border-primary-subtle rounded-pill px-3 py-2">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            </div>
                            <div className="d-flex align-items-center">
                                <span className="small text-muted me-2">Sentiment IA:</span>
                                <span className={`fw-bold text-capitalize sentiment-label-${review.analysis__sentiment_label}`}>
                                    {review.analysis__sentiment_label} ({review.analysis__sentiment_score})
                                </span>
                            </div>
                        </div>
                    )}
                </div>

                <footer className="noir-modal-footer">
                    <button className="btn btn-secondary w-100 py-2 rounded-3" onClick={onClose}>Chiudi</button>
                </footer>
            </div>
        </div>
    );
};

const ReviewsDataTableWidget = ({ data, onReviewClick }) => {
    if (!data) {
        return <div className="analysis-loading">Caricamento...</div>;
    }

    return (
        <div className="analysis-reviews">
            <div className="table-responsive analysis-reviews-table">
                <table className="table align-middle table-hover">
                    <thead>
                        <tr>
                            <th scope="col">Autore</th>
                            <th scope="col">Resort</th>
                            <th scope="col">Piattaforma</th>
                            <th scope="col">Data</th>
                            <th scope="col">Rating</th>
                            <th scope="col">Estratto</th>
                            <th scope="col" className="text-end">Azione</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((review) => (
                            <tr
                                key={review.id}
                                className={`cursor-pointer ${review.analysis__is_anomaly ? 'table-danger-soft' : ''}`}
                                onClick={() => onReviewClick(review)}
                            >
                                <td>
                                    {review.author}
                                    {review.analysis__is_anomaly && <span className="badge bg-danger ms-2">Anomalia</span>}
                                </td>
                                <td>{review.resort__name}</td>
                                <td>{review.source__name}</td>
                                <td>{new Date(review.review_date).toLocaleDateString()}</td>
                                <td>
                                    <strong>{review.rating}</strong>
                                    <small className="text-muted ms-1">
                                        {['Google', 'Tripadvisor'].some(s => review.source__name.toLowerCase().includes(s.toLowerCase())) ? '/5' : '/10'}
                                    </small>
                                </td>
                                <td>{review.text.substring(0, 80)}...</td>
                                <td className="text-end">
                                    <button className="btn btn-sm btn-outline-primary rounded-circle p-2" title="Vedi Dettaglio">
                                        <i className="fa-solid fa-eye"></i>
                                    </button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
            <div className="analysis-reviews-cards">
                {data.map((review) => (
                    <article
                        className="analysis-review-card cursor-pointer"
                        key={`card-${review.id}`}
                        onClick={() => onReviewClick(review)}
                    >
                        <header className="analysis-review-card-header">
                            <div>
                                <span className="analysis-review-author">{review.author}</span>
                                <span className="analysis-review-date">{new Date(review.review_date).toLocaleDateString()}</span>
                            </div>
                            <span className="analysis-review-rating">
                                {review.analysis__is_anomaly && <i className="fa-solid fa-triangle-exclamation text-danger me-2" title="Anomalia Sentiment"></i>}
                                <strong>{review.rating}</strong>
                                <small className="ms-1">{['Google', 'Tripadvisor'].some(s => review.source__name.toLowerCase().includes(s.toLowerCase())) ? '/5' : '/10'}</small>
                            </span>
                        </header>
                        <div className="analysis-review-meta">
                            <span className="analysis-review-chip">
                                <i className="fa-solid fa-location-dot" aria-hidden="true" />
                                {review.resort__name}
                            </span>
                            <span className="analysis-review-chip">
                                <i className="fa-solid fa-globe" aria-hidden="true" />
                                {review.source__name}
                            </span>
                        </div>
                        <p className="analysis-review-text">{review.text.substring(0, 150)}...</p>
                        <div className="text-end mt-2">
                             <span className="text-primary small fw-bold">Leggi tutto <i className="fa-solid fa-arrow-right ms-1"></i></span>
                        </div>
                    </article>
                ))}
            </div>
        </div>
    );
};

const SectionCard = ({ id, title, subtitle, actions, children }) => (
    <section className="analysis-section" aria-labelledby={id}>
        <div className="analysis-section-header">
            <div className="analysis-section-titles">
                <h2 id={id}>{title}</h2>
                {subtitle ? <p>{subtitle}</p> : null}
            </div>
            {actions ? <div className="analysis-section-actions">{actions}</div> : null}
        </div>
        <div className="analysis-section-body">{children}</div>
    </section>
);


class AnalysisCenter extends React.Component {
    constructor(props) {
        super(props);
        const filtersData = JSON.parse(document.getElementById('filters-data').textContent);

        // Read initial filters from URL search params
        const urlParams = new URLSearchParams(window.location.search);
        const initialResorts = urlParams.get('resorts') ? urlParams.get('resorts').split(',') : [];
        const initialSources = urlParams.get('sources') ? urlParams.get('sources').split(',') : [];

        this.state = {
            loading: true,
            activeTab: 'web', // 'web' or 'veratour'
            veratourView: 'stats', // 'stats', 'sentiment', 'comparison'
            filters: {
                resorts: initialResorts,
                sources: initialSources,
                start_date: urlParams.get('start_date') || '',
                end_date: urlParams.get('end_date') || '',
                query: urlParams.get('query') || '',
                include_internal: false,
            },
            data: {
                kpiSummary: null,
                trendChart: null,
                platformChart: null,
                thematicAnalysis: null,
                ratingDistribution: null,
                reviewsTable: null,
            },
            availableFilters: filtersData,
            selectedReview: null,
        };

        this.trendChartRef = React.createRef();
        this.platformChartRef = React.createRef();
        this.thematicChartRef = React.createRef();
        this.ratingDistributionChartRef = React.createRef();
    }

    componentDidMount() {
        this.fetchData();
    }

    handleFilterChange = (e) => {
        const { name, value, type, selectedOptions } = e.target;
        let newFilters;

        if (type === 'select-multiple') {
            const values = Array.from(selectedOptions, option => option.value);
            newFilters = { ...this.state.filters, [name]: values };
        } else {
            newFilters = { ...this.state.filters, [name]: value };
        }

        this.setState({ filters: newFilters }, () => {
            // Se è la barra di ricerca, vogliamo una reattività immediata o quantomeno assicurarci che
            // il tasto "Applica" usi lo stato aggiornato.
            if (name === 'query' && value === '') {
                this.fetchData();
            }
        });
    }

    handleExport = (format) => () => {
        const { filters, data } = this.state;
        const params = new URLSearchParams();
        if (filters.resorts.length) params.append('resorts', filters.resorts.join(','));
        if (filters.sources.length) params.append('sources', filters.sources.join(','));
        if (filters.start_date) params.append('start_date', filters.start_date);
        if (filters.end_date) params.append('end_date', filters.end_date);
        if (filters.query) params.append('query', filters.query);

        if (format === 'csv') {
            const url = `/reviews/analysis-center/export/csv/?${params.toString()}`;
            window.open(url, '_blank');
        } else if (format === 'pdf') {
            const trendChartImg = this.trendChartRef.current ? this.trendChartRef.current.toBase64Image() : null;
            const platformChartImg = this.platformChartRef.current ? this.platformChartRef.current.toBase64Image() : null;
            const ratingDistributionChartImg = this.ratingDistributionChartRef.current ? this.ratingDistributionChartRef.current.toBase64Image() : null;
            const thematicChartImg = this.thematicChartRef.current ? this.thematicChartRef.current.toBase64Image() : null;

            axios.post(`/reviews/analysis-center/export/pdf/?${params.toString()}`, {
                trendChartImg,
                platformChartImg,
                ratingDistributionChartImg,
                thematicChartImg,
                kpiSummary: data.kpiSummary,
            }, {
                responseType: 'blob',
            }).then(response => {
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', 'analysis_report.pdf');
                document.body.appendChild(link);
                link.click();
            });
        }
    }

    fetchData = () => {
        this.setState({ loading: true });
        const { filters, activeTab, availableFilters } = this.state;

        const params = new URLSearchParams();
        if (filters.resorts && filters.resorts.length) params.append('resorts', filters.resorts.join(','));

        if (activeTab === 'veratour') {
            const veratourSource = availableFilters.sources.find(s => s.name === 'Veratour');
            if (veratourSource) {
                params.append('sources', veratourSource.id);
            }
        } else {
            if (filters.sources && filters.sources.length) params.append('sources', filters.sources.join(','));
            if (filters.include_internal) params.append('include_internal', 'true');
        }

        if (filters.start_date) params.append('start_date', filters.start_date);
        if (filters.end_date) params.append('end_date', filters.end_date);
        if (filters.query) params.append('query', filters.query);

        const kpiSummaryPromise = axios.get(`/api/reviews/kpi-summary/?${params.toString()}`);
        const trendChartPromise = axios.get(`/api/reviews/trend-chart/?${params.toString()}`);
        const platformChartPromise = axios.get(`/api/reviews/platform-chart/?${params.toString()}`);
        const ratingDistributionPromise = axios.get(`/api/reviews/rating-distribution/?${params.toString()}`);
        const thematicAnalysisPromise = axios.get(`/api/reviews/thematic-analysis/?${params.toString()}`);

        // Ensure the table also receives the include_internal parameter for full synchronization
        const tableParams = new URLSearchParams(params.toString());
        const reviewsTablePromise = axios.get(`/api/reviews/reviews-table/?${tableParams.toString()}`);

        Promise.all([
            kpiSummaryPromise,
            trendChartPromise,
            platformChartPromise,
            ratingDistributionPromise,
            thematicAnalysisPromise,
            reviewsTablePromise,
        ]).then(([kpiSummaryRes, trendChartRes, platformChartRes, ratingDistributionRes, thematicAnalysisRes, reviewsTableRes]) => {
            this.setState({
                data: {
                    kpiSummary: kpiSummaryRes.data.overall,
                    trendChart: trendChartRes.data.overall,
                    ratingDistribution: ratingDistributionRes.data.overall,
                    platformChart: platformChartRes.data,
                    thematicAnalysis: thematicAnalysisRes.data,
                    reviewsTable: reviewsTableRes.data.reviews,
                    byResort: {
                        kpi: kpiSummaryRes.data.by_resort,
                        trend: trendChartRes.data.by_resort,
                        ratingDist: ratingDistributionRes.data.by_resort,
                    },
                },
                loading: false,
            });
        }).catch(error => {
            console.error("Error fetching analysis data:", error);
            this.setState({ loading: false });
        });
    }

    handleTabChange = (tab) => {
        this.setState({ activeTab: tab }, () => {
            this.fetchData();
        });
    }

    handleVeratourViewChange = (view) => {
        this.setState({ veratourView: view });
    }

    handleReviewClick = (review) => {
        this.setState({ selectedReview: review });
    }

    closeReviewModal = () => {
        this.setState({ selectedReview: null });
    }

    render() {
        const { loading, filters, data, availableFilters, activeTab, selectedReview } = this.state;
        const isBenchmarking = filters.resorts && filters.resorts.length > 1;

    const filteredResorts = availableFilters.resorts.filter(r => {
        if (!filters.company) return true;
        return String(r.company_id) === String(filters.company);
    });

        return (
            <div className={`analysis-center-app ${isBenchmarking ? 'is-benchmarking' : ''}`}>
                <div className="analysis-tabs mb-4">
                    <ul className="nav nav-tabs noir-nav-tabs">
                        <li className="nav-item">
                            <button
                                className={`nav-link ${activeTab === 'web' ? 'active' : ''}`}
                                onClick={() => this.handleTabChange('web')}
                            >
                                <i className="fa-solid fa-globe me-2"></i>Reputazione Web
                            </button>
                        </li>
                        <li className="nav-item">
                            <button
                                className={`nav-link ${activeTab === 'veratour' ? 'active' : ''}`}
                                onClick={() => this.handleTabChange('veratour')}
                            >
                                <i className="fa-solid fa-chart-line me-2"></i>Veratour Insights
                            </button>
                        </li>
                    </ul>
                </div>

                <SectionCard
                    id="analysis-filters"
                    title={activeTab === 'web' ? "Filtri Reputazione Web" : "Filtri Veratour Insights"}
                    subtitle={activeTab === 'web'
                        ? "Analizza la percezione pubblica del tuo brand su Google, Booking e TripAdvisor."
                        : "Analisi approfondita dei feedback interni Veratour, Response Rate e Critical Alert."
                    }
                    actions={(
                        <div className="analysis-section-actions-inline">
                            <a href="/reviews/veratour/upload/" className="btn btn-warning me-2">
                                <i className="fas fa-file-excel me-2"></i>Upload Veratour
                            </a>
                            <button className="btn btn-secondary" onClick={this.handleExport('pdf')} disabled={loading}>
                                Esporta PDF
                            </button>
                            <button className="btn btn-secondary" onClick={this.handleExport('csv')} disabled={loading}>
                                Esporta CSV
                            </button>
                        </div>
                    )}
                >
                    <div className="analysis-filter-grid">
                        <label className="analysis-filter-field">
                            <span>Società</span>
                            <select
                                className="form-select"
                                name="company"
                                value={filters.company || ''}
                                onChange={(e) => {
                                    this.handleFilterChange(e);
                                    // Reset resorts when company changes to avoid inconsistent selection
                                    this.setState(prev => ({
                                        filters: { ...prev.filters, resorts: [], company: e.target.value }
                                    }));
                                }}
                            >
                                <option value="">Tutte le società</option>
                                {availableFilters.companies.map((c) => (
                                    <option key={c.id} value={c.id}>
                                        {c.name}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label className="analysis-filter-field">
                            <span>Resort</span>
                            <select
                                multiple
                                className="form-select"
                                name="resorts"
                                value={filters.resorts}
                                onChange={this.handleFilterChange}
                            >
                                {filteredResorts.map((r) => (
                                    <option key={r.id} value={r.id}>
                                        {r.name}
                                    </option>
                                ))}
                            </select>
                        </label>
                        {activeTab === 'web' && (
                            <label className="analysis-filter-field">
                                <span>Piattaforme</span>
                                <select
                                    multiple
                                    className="form-select"
                                    name="sources"
                                    value={filters.sources}
                                    onChange={this.handleFilterChange}
                                >
                                    {availableFilters.sources.filter(s => s.name !== 'Veratour').map((s) => (
                                        <option key={s.id} value={s.id}>
                                            {s.name}
                                        </option>
                                    ))}
                                </select>
                            </label>
                        )}
                        <label className="analysis-filter-field">
                            <span>Data inizio</span>
                            <input
                                type="date"
                                className="form-control"
                                name="start_date"
                                value={filters.start_date}
                                onChange={this.handleFilterChange}
                            />
                        </label>
                        <label className="analysis-filter-field">
                            <span>Data fine</span>
                            <input
                                type="date"
                                className="form-control"
                                name="end_date"
                                value={filters.end_date}
                                onChange={this.handleFilterChange}
                            />
                        </label>
                        <label className="analysis-filter-field">
                            <span>Ricerca Termini</span>
                            <div className="input-group">
                                <input
                                    type="text"
                                    className="form-control"
                                    name="query"
                                    placeholder="Es: piscina, staff..."
                                    value={filters.query}
                                    onChange={this.handleFilterChange}
                                    onKeyPress={(e) => e.key === 'Enter' && this.fetchData()}
                                />
                                {filters.query && (
                                    <button
                                        className="btn btn-outline-secondary"
                                        type="button"
                                        onClick={() => this.setState({ filters: { ...filters, query: '' } }, this.fetchData)}
                                    >
                                        <i className="fa-solid fa-xmark"></i>
                                    </button>
                                )}
                            </div>
                        </label>
                    </div>
                    <div className="analysis-filter-actions d-flex justify-content-between align-items-center">
                        <div>
                            {activeTab === 'web' && (
                                <div className="form-check form-switch noir-switch">
                                    <input
                                        className="form-check-input"
                                        type="checkbox"
                                        id="includeInternalSwitch"
                                        checked={filters.include_internal}
                                        onChange={(e) => this.setState({
                                            filters: { ...filters, include_internal: e.target.checked }
                                        }, this.fetchData)}
                                    />
                                    <label className="form-check-label" htmlFor="includeInternalSwitch">
                                        Includi Analisi Interna (Veratour)
                                    </label>
                                </div>
                            )}
                        </div>
                        <button className="btn btn-primary" onClick={this.fetchData} disabled={loading}>
                            {loading ? 'Caricamento…' : 'Applica filtri'}
                        </button>
                    </div>
                </SectionCard>

                {loading ? (
                    <div className="analysis-loading is-large" role="status" aria-live="polite">
                        <div className="spinner-border" role="presentation" />
                        <span>Sincronizzazione dati recensioni…</span>
                    </div>
                ) : data.kpiSummary ? (
                    <div className={`analysis-panels ${isBenchmarking ? 'is-grid' : 'is-single'}`}>
                        {isBenchmarking ? (
                            filters.resorts.map((resortId) => {
                                const resortName = availableFilters.resorts.find(r => String(r.id) === String(resortId))?.name || `Resort ${resortId}`;
                                const resortKpi = data.byResort?.kpi?.[String(resortId)];
                                const resortTrend = data.byResort?.trend?.[String(resortId)];
                                const resortRatingDist = data.byResort?.ratingDist?.[String(resortId)];

                                return (
                                    <div key={resortId} className="analysis-benchmarking-column">
                                        <header className="analysis-benchmarking-header">
                                            <h3>{resortName}</h3>
                                        </header>
                                        <SectionCard
                                            id={`analysis-kpi-${resortId}`}
                                            title="Riepilogo KPI"
                                        >
                                            <KPISummaryWidget
                                                data={resortKpi}
                                                hasQuery={!!filters.query}
                                                isVeratourOnly={activeTab === 'veratour'}
                                            />
                                        </SectionCard>
                                        <SectionCard
                                            id={`analysis-trend-${resortId}`}
                                            title="Andamento temporale"
                                        >
                                            <div className="analysis-chart-container">
                                                <TrendChartWidget data={resortTrend} hasQuery={!!filters.query} />
                                            </div>
                                        </SectionCard>
                                        <SectionCard
                                            id={`analysis-rating-${resortId}`}
                                            title="Distribuzione valutazioni"
                                        >
                                            <RatingDistributionWidget data={resortRatingDist} />
                                        </SectionCard>
                                    </div>
                                );
                            })
                        ) : (
                            <>
                                <SectionCard
                                    id="analysis-kpi"
                                    title="Riepilogo KPI"
                                    subtitle="Valori sintetici per comprendere subito lo stato della reputazione."
                                >
                                    <KPISummaryWidget
                                        data={data.kpiSummary}
                                        hasQuery={!!filters.query}
                                        isVeratourOnly={activeTab === 'veratour'}
                                    />
                                    {activeTab === 'veratour' && (
                                        <div className="veratour-view-toggle mt-4 d-flex justify-content-center">
                                            <div className="btn-group noir-btn-group" role="group">
                                                <button
                                                    className={`btn ${this.state.veratourView === 'stats' ? 'btn-primary' : 'btn-outline-primary'}`}
                                                    onClick={() => this.handleVeratourViewChange('stats')}
                                                >
                                                    <i className="fas fa-chart-pie me-2"></i>Statistiche Ufficiali
                                                </button>
                                                <button
                                                    className={`btn ${this.state.veratourView === 'sentiment' ? 'btn-primary' : 'btn-outline-primary'}`}
                                                    onClick={() => this.handleVeratourViewChange('sentiment')}
                                                >
                                                    <i className="fas fa-brain me-2"></i>Analisi Sentiment
                                                </button>
                                                <button
                                                    className={`btn ${this.state.veratourView === 'comparison' ? 'btn-primary' : 'btn-outline-primary'}`}
                                                    onClick={() => this.handleVeratourViewChange('comparison')}
                                                >
                                                    <i className="fas fa-balance-scale me-2"></i>Comparazione
                                                </button>
                                            </div>
                                        </div>
                                    )}
                                </SectionCard>

                                {activeTab === 'veratour' && this.state.veratourView === 'comparison' && (
                                    <SectionCard
                                        id="veratour-comparison"
                                        title="Cross-Analysis Reparti"
                                        subtitle="Confronto tra i dati ufficiali del Report e l'analisi IA dei commenti."
                                    >
                                        <VeratourCrossAnalysisWidget data={data.kpiSummary.veratour} />
                                    </SectionCard>
                                )}

                                {(activeTab === 'web' || (activeTab === 'veratour' && this.state.veratourView !== 'comparison')) && (
                                    <>
                                        { (activeTab === 'web' || this.state.veratourView === 'sentiment') && (
                                            <>
                                                <SectionCard
                                                    id="analysis-trend"
                                                    title="Andamento temporale"
                                                    subtitle="Valuta rating, sentiment e volume recensioni mese per mese."
                                                >
                                                    <div className="analysis-chart-container">
                                                        <TrendChartWidget ref={this.trendChartRef} data={data.trendChart} hasQuery={!!filters.query} />
                                                    </div>
                                                </SectionCard>

                                                <SectionCard
                                                    id="analysis-platform"
                                                    title="Confronto piattaforme"
                                                    subtitle="Individua su quali canali concentrare le azioni correttive."
                                                >
                                                    <div className="analysis-chart-container">
                                                        <PlatformComparisonWidget ref={this.platformChartRef} data={data.platformChart} />
                                                    </div>
                                                </SectionCard>

                                                <SectionCard
                                                    id="analysis-rating-distribution"
                                                    title="Distribuzione valutazioni"
                                                    subtitle="Scopri come si distribuiscono i punteggi e confrontali con lo stesso periodo dell'anno precedente."
                                                >
                                                    <RatingDistributionWidget ref={this.ratingDistributionChartRef} data={data.ratingDistribution} />
                                                </SectionCard>

                                                <SectionCard
                                                    id="analysis-thematic"
                                                    title="Analisi tematica"
                                                    subtitle="Scopri i temi che impattano maggiormente la soddisfazione degli ospiti."
                                                >
                                                    <div className="analysis-chart-container">
                                                        <ThematicAnalysisWidget ref={this.thematicChartRef} data={data.thematicAnalysis} />
                                                    </div>
                                                </SectionCard>
                                            </>
                                        )}

                                        { activeTab === 'veratour' && this.state.veratourView === 'stats' && (
                                            <SectionCard
                                                id="veratour-stats-charts"
                                                title="Grafici Statistiche Ufficiali"
                                                subtitle="Dati estratti dal file REPORT (giudizi positivi per reparto)."
                                            >
                                                <div className="analysis-chart-container">
                                                    <Bar
                                                        data={{
                                                            labels: (data.kpiSummary.veratour?.cross_analysis || []).map(i => i.department),
                                                            datasets: [{
                                                                label: 'Giudizio Positivo (%)',
                                                                data: (data.kpiSummary.veratour?.cross_analysis || []).map(i => i.report_pos),
                                                                backgroundColor: 'rgba(34, 197, 94, 0.5)',
                                                                borderColor: 'rgb(34, 197, 94)',
                                                                borderWidth: 1
                                                            }]
                                                        }}
                                                        options={{
                                                            responsive: true,
                                                            maintainAspectRatio: false,
                                                            scales: { y: { beginAtZero: true, max: 100 } }
                                                        }}
                                                    />
                                                </div>
                                            </SectionCard>
                                        )}

                                        <SectionCard
                                            id="analysis-reviews"
                                            title={activeTab === 'veratour' ? "Commenti Estratti" : "Dettaglio recensioni"}
                                            subtitle={activeTab === 'veratour' ? "Testi analizzati dal file VOTA_COMMENTI." : "Consulta gli ultimi feedback e condividili con il team operativo."}
                                        >
                                            <ReviewsDataTableWidget
                                                data={data.reviewsTable}
                                                onReviewClick={this.handleReviewClick}
                                            />
                                        </SectionCard>
                                    </>
                                )}
                            </>
                        )}
                    </div>
                ) : (
                    <div className="analysis-empty">
                        Nessun dato da visualizzare. Prova ad ampliare l&apos;intervallo temporale o includere più piattaforme.
                    </div>
                )}

                <ReviewDetailModal
                    review={selectedReview}
                    onClose={this.closeReviewModal}
                />
            </div>
        );
    }
}

export default AnalysisCenter;
