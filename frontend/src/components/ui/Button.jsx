import PropTypes from 'prop-types';

/**
 * Bottone della libreria Nuvia. Renderizza <button> o <a> (se `href`).
 * Stile guidato dai design token via classi `.nv-btn` (vedi styles/ui-components.css).
 */
export default function Button({
  variant = 'primary',
  size = 'md',
  block = false,
  href,
  className = '',
  children,
  ...rest
}) {
  const classes = [
    'nv-btn',
    `nv-btn--${variant}`,
    size !== 'md' ? `nv-btn--${size}` : '',
    block ? 'nv-btn--block' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  if (href) {
    return (
      <a href={href} className={classes} {...rest}>
        {children}
      </a>
    );
  }

  return (
    <button className={classes} {...rest}>
      {children}
    </button>
  );
}

Button.propTypes = {
  variant: PropTypes.oneOf(['primary', 'secondary', 'ghost', 'danger']),
  size: PropTypes.oneOf(['sm', 'md', 'lg']),
  block: PropTypes.bool,
  href: PropTypes.string,
  className: PropTypes.string,
  children: PropTypes.node,
};
