import PropTypes from 'prop-types';

/** Indicatore di caricamento coerente con i token. */
export default function Spinner({ size = 'md', label = 'Caricamento…', className = '' }) {
  const classes = [
    'nv-spinner',
    size === 'lg' ? 'nv-spinner--lg' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return <span className={classes} role="status" aria-label={label} />;
}

Spinner.propTypes = {
  size: PropTypes.oneOf(['md', 'lg']),
  label: PropTypes.string,
  className: PropTypes.string,
};
