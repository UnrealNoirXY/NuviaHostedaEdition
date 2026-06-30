const listeners = new Set();

export const addPwaListener = (listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
};

export const emitPwaEvent = (event) => {
    listeners.forEach((listener) => {
        try {
            listener(event);
        } catch (error) {
            console.error("Errore durante la gestione dell'evento PWA", error);
        }
    });
};
