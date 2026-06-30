import React, { useState } from 'react';

const NuviaTour = ({ isOpen, onComplete }) => {
    const [step, setStep] = useState(0);

    const tourSteps = [
        {
            title: "Benvenuto in Nuvia OS",
            content: "La tua nuova scrivania operativa digitale. Progettata per darti il pieno controllo sul resort.",
            target: "body"
        },
        {
            title: "La Tua Scrivania (Desktop)",
            content: "Qui trovi le icone per lanciare le app. Puoi trascinarle e organizzarle come preferisci.",
            target: ".desktop-icons"
        },
        {
            title: "Multitasking Avanzato",
            content: "Apri più app contemporaneamente. Trascina le finestre per affiancarle e lavora su più fronti.",
            target: ".desktop-workspace"
        },
        {
            title: "Taskbar (Il Dock)",
            content: "Passa rapidamente da un'app aperta all'altra e tieni d'occhio le notifiche di sistema.",
            target: ".taskbar-dock"
        },
        {
            title: "Ricerca Spotlight",
            content: "Usa CMD+K per trovare istantaneamente ospiti, ticket o colleghi. La potenza è nelle tue dita.",
            target: "body"
        }
    ];

    if (!isOpen) return null;

    const current = tourSteps[step];

    return (
        <div className="tour-overlay">
            <div className={`tour-card glass step-${step}`}>
                <div className="tour-progress">
                    {tourSteps.map((_, i) => (
                        <div key={i} className={`progress-dot ${i <= step ? 'active' : ''}`}></div>
                    ))}
                </div>
                <h3>{current.title}</h3>
                <p>{current.content}</p>
                <div className="tour-footer">
                    <button className="btn btn-link btn-skip" onClick={onComplete}>Salta Tour</button>
                    <button
                        className="btn btn-primary"
                        onClick={() => step < tourSteps.length - 1 ? setStep(step + 1) : onComplete()}
                    >
                        {step === tourSteps.length - 1 ? 'Inizia a Lavorare' : 'Prossimo'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default NuviaTour;
