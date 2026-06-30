import PropTypes from 'prop-types';

/** Badge/pill della libreria Nuvia. */
export default function Badge({ tone = 'neutral', className = '', children, ...rest }) {
  const classes = [
    'nv-badge',
    tone !== 'neutral' ? `nv-badge--${tone}` : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <span className={classes} {...rest}>
      {children}
    </span>
  );
}

Badge.propTypes = {
  tone: PropTypes.oneOf(['neutral', 'success', 'warning', 'danger', 'info']),
  className: PropTypes.string,
  children: PropTypes.node,
};
