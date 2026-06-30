import React, { useState, useEffect } from 'react';
import apiClient from '../apiClient';
import './RecentReviewsWidget.css';

// A simple component to render star ratings
const StarRating = ({ rating, maxRating = 5, sourceMaxRating = 10 }) => {
    const normalizedRating = (rating / sourceMaxRating) * maxRating;
    const fullStars = Math.floor(normalizedRating);
    const halfStar = normalizedRating % 1 >= 0.5;
    const emptyStars = maxRating - fullStars - (halfStar ? 1 : 0);

    return (
        <div className="star-rating">
            {[...Array(fullStars)].map((_, i) => <i key={`full-${i}`} className="fas fa-star"></i>)}
            {halfStar && <i key="half" className="fas fa-star-half-alt"></i>}
            {[...Array(emptyStars)].map((_, i) => <i key={`empty-${i}`} className="far fa-star"></i>)}
        </div>
    );
};

const SentimentIndicator = ({ sentiment }) => {
    const sentimentClasses = {
        positive: 'sentiment-indicator positive',
        neutral: 'sentiment-indicator neutral',
        negative: 'sentiment-indicator negative',
    };
    return <span className={sentimentClasses[sentiment] || sentimentClasses.neutral} title={`Sentiment: ${sentiment}`}></span>;
};

const RecentReviewsWidget = () => {
    const [reviews, setReviews] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [expandedReviewId, setExpandedReviewId] = useState(null);

    useEffect(() => {
        apiClient.get('/api/desk/widget-data/recent-reviews/')
            .then(response => {
                setReviews(response.data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching recent reviews:", err);
                setError("Impossibile caricare le recensioni recenti.");
                setLoading(false);
            });
    }, []);

    const handleToggleExpand = (id) => {
        setExpandedReviewId(expandedReviewId === id ? null : id);
    };

    if (loading) return <div className="widget-loading">Caricamento...</div>;
    if (error) return <div className="widget-error">{error}</div>;
    if (reviews.length === 0) return <div className="widget-empty">Nessuna recensione recente trovata.</div>;

    return (
        <div className="recent-reviews-widget">
            {reviews.map(review => (
                <div key={review.id} className="review-item" onClick={() => handleToggleExpand(review.id)}>
                    <div className="review-header">
                        <SentimentIndicator sentiment={review.sentiment_label} />
                        <h6 className="review-title">{review.title || 'Senza titolo'}</h6>
                        <div className="review-meta">
                            <StarRating rating={review.rating} sourceMaxRating={review.source_name === 'Booking.com' ? 10 : 5} />
                            <span className="review-source">{review.source_name}</span>
                        </div>
                    </div>
                    {expandedReviewId === review.id && (
                        <div className="review-body">
                            <p className="review-text">{review.text}</p>
                            <div className="review-footer">
                                <span>di {review.author}</span>
                                <span>{new Date(review.review_date).toLocaleDateString()}</span>
                                {review.original_url && (
                                    <a href={review.original_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()} title="Vedi recensione originale">
                                        <i className="fas fa-external-link-alt"></i>
                                    </a>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            ))}
        </div>
    );
};

export default RecentReviewsWidget;
