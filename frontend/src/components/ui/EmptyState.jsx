import PropTypes from 'prop-types';

/**
 * Stato vuoto coerente: icona (Font Awesome), titolo, testo e azione opzionale.
 */
export default function EmptyState({ icon = 'fa-inbox', title, text, action, className = '' }) {
  const classes = ['nv-empty', className].filter(Boolean).join(' ');
  return (
    <div className={classes}>
      <i className={`fas ${icon} nv-empty__icon`} aria-hidden="true" />
      {title && <p className="nv-empty__title">{title}</p>}
      {text && <p className="nv-empty__text">{text}</p>}
      {action}
    </div>
  );
}

EmptyState.propTypes = {
  icon: PropTypes.string,
  title: PropTypes.node,
  text: PropTypes.node,
  action: PropTypes.node,
  className: PropTypes.string,
};
