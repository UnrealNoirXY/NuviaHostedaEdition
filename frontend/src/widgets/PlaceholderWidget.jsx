import React from 'react';
import PropTypes from 'prop-types';

const PlaceholderWidget = ({ widgetId }) => {
  // A simple way to make the placeholder name more readable
  const widgetName = widgetId
    .replace(/-/g, ' ')
    .replace('widget', '')
    .replace(/(^\w{1})|(\s+\w{1})/g, letter => letter.toUpperCase())
    .trim();

  return (
    <div className="d-flex flex-column align-items-center justify-content-center h-100 text-muted">
      <i className="fas fa-tools fa-2x mb-2"></i>
      <h6 className="fw-bold text-center mb-1">{widgetName}</h6>
      <p className="small text-center">Widget in fase di sviluppo</p>
    </div>
  );
};

PlaceholderWidget.propTypes = {
  widgetId: PropTypes.string.isRequired,
};

export default PlaceholderWidget;
