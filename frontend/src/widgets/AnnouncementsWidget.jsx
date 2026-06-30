import React, { useState, useEffect } from 'react';

const AnnouncementsWidget = () => {
  const [announcements, setAnnouncements] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAnnouncements = async () => {
      try {
        const response = await fetch('/desk/api/widget-data/announcements/');
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const data = await response.json();
        setAnnouncements(data);
      } catch (error) {
        setError(error.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchAnnouncements();
  }, []);

  if (isLoading) return <div className="text-center p-3">Caricamento...</div>;
  if (error) return <div className="alert alert-danger mx-2">Errore: {error}</div>;

  return (
    <div className="list-group list-group-flush">
      {announcements && announcements.length > 0 ? (
        announcements.map(ann => (
          <a key={ann.id} href={ann.url} className="list-group-item list-group-item-action text-decoration-none">
            <div className="d-flex w-100 justify-content-between">
              <h6 className="mb-1 text-primary">{ann.title}</h6>
              <small className="text-muted">{ann.created_at}</small>
            </div>
            <p className="mb-1 small text-body">{ann.content}</p>
          </a>
        ))
      ) : (
        <p className="text-muted p-3">Nessun annuncio recente.</p>
      )}
    </div>
  );
};

export default AnnouncementsWidget;
