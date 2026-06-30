import React, { useEffect, useState } from 'react';

const BootScreen = ({ onComplete }) => {
    const [phase, setPhase] = useState('dark'); // dark, logo, glow, fade

    useEffect(() => {
        const timers = [
            setTimeout(() => setPhase('logo'), 500),
            setTimeout(() => setPhase('glow'), 2000),
            setTimeout(() => setPhase('fade'), 3500),
            setTimeout(() => onComplete(), 4500)
        ];
        return () => timers.forEach(clearTimeout);
    }, [onComplete]);

    return (
        <div className={`nuvia-boot-screen phase-${phase}`}>
            <div className="boot-content">
                <div className="logo-container">
                    <img src="/static/img/logo.png" alt="Nuvia Logo" className="boot-logo" />
                    <div className="logo-glow"></div>
                </div>
                <div className="boot-loader">
                    <div className="loader-bar"></div>
                </div>
                <div className="boot-text">Nuvia OS v1.0 // Operational Kernel Loaded</div>
            </div>
            <div className="scanline"></div>
        </div>
    );
};

export default BootScreen;
