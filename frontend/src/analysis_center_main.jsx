import React from 'react';
import ReactDOM from 'react-dom/client';
import AnalysisCenter from './components/analysis_center/AnalysisCenter';
import './pwa/registration';

const analysisCenterRootElement = document.getElementById('analysis-center-root');

if (analysisCenterRootElement) {
    const root = ReactDOM.createRoot(analysisCenterRootElement);
    root.render(
        <React.StrictMode>
            <AnalysisCenter />
        </React.StrictMode>
    );
}
