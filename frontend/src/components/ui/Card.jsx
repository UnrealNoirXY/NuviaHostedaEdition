import PropTypes from 'prop-types';

/**
 * Card della libreria Nuvia. Header opzionale (title/subtitle/actions).
 */
export default function Card({ title, subtitle, actions, className = '', children, ...rest }) {
  const classes = ['nv-card', className].filter(Boolean).join(' ');
  const hasHeader = title || subtitle || actions;

  return (
    <div className={classes} {...rest}>
      {hasHeader && (
        <div className="nv-card__header">
          <div>
            {title && <h3 className="nv-card__title">{title}</h3>}
            {subtitle && <p className="nv-card__subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="nv-card__actions">{actions}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

Card.propTypes = {
  title: PropTypes.node,
  subtitle: PropTypes.node,
  actions: PropTypes.node,
  className: PropTypes.string,
  children: PropTypes.node,
};
