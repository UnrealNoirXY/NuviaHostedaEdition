import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { getPermissions } from './api';

const PermissionsContext = createContext({ loading: true, permissions: null });

export const PermissionsProvider = ({ children }) => {
    const [permissions, setPermissions] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchPermissions = async () => {
            try {
                const { data } = await getPermissions();
                setPermissions(data);
            } catch (err) {
                console.error('Impossibile caricare i permessi', err);
                setPermissions(null);
            } finally {
                setLoading(false);
            }
        };

        fetchPermissions();
    }, []);

    const value = useMemo(() => ({ permissions, loading }), [permissions, loading]);

    return (
        <PermissionsContext.Provider value={value}>
            {children}
        </PermissionsContext.Provider>
    );
};

export const usePermissions = () => useContext(PermissionsContext);

