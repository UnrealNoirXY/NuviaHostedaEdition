import React from "react";
import PropTypes from "prop-types";

export default function SkeletonPlaceholder({ lines, width, className }) {
  return (
    <div className={`maintenance-skeleton ${className}`.trim()} aria-hidden="true">
      {Array.from({ length: lines }).map((_, index) => (
        <div key={`skeleton-line-${index}`} className="maintenance-skeleton__line" style={{ width: index === 0 && width ? width : undefined }} />
      ))}
    </div>
  );
}

SkeletonPlaceholder.propTypes = {
  lines: PropTypes.number,
  width: PropTypes.string,
  className: PropTypes.string,
};

SkeletonPlaceholder.defaultProps = {
  lines: 3,
  width: "",
  className: "",
};
