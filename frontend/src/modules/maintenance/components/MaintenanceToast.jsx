import React, { useEffect } from "react";
import PropTypes from "prop-types";

export default function MaintenanceToast({ message, tone, onClose }) {
  useEffect(() => {
    if (!message) return undefined;
    const timeout = setTimeout(() => onClose?.(), 4200);
    return () => clearTimeout(timeout);
  }, [message, onClose]);

  if (!message) return null;

  const icon = tone === "error" ? "fa-triangle-exclamation" : tone === "success" ? "fa-circle-check" : "fa-circle-info";

  return (
    <div className={`maintenance-toast maintenance-toast--${tone}`} role="status" aria-live="polite">
      <span className="maintenance-toast__icon" aria-hidden="true">
        <i className={`fa-solid ${icon}`} />
      </span>
      <p className="maintenance-toast__body">{message}</p>
      <button type="button" className="maintenance-toast__close" onClick={onClose} aria-label="Chiudi notifica">
        <i className="fa-solid fa-xmark" aria-hidden="true" />
      </button>
    </div>
  );
}

MaintenanceToast.propTypes = {
  message: PropTypes.string,
  tone: PropTypes.oneOf(["info", "success", "error"]),
  onClose: PropTypes.func,
};

MaintenanceToast.defaultProps = {
  message: "",
  tone: "info",
  onClose: () => {},
};
