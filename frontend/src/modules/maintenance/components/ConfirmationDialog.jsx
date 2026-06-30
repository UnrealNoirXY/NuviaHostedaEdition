import React from "react";
import PropTypes from "prop-types";
import { createPortal } from "react-dom";

function ConfirmationDialog({
  open,
  title,
  message,
  confirmLabel,
  cancelLabel,
  onConfirm,
  onCancel,
  processing,
}) {
  if (!open) return null;

  return createPortal(
    <div className="maintenance-dialog" role="alertdialog" aria-modal="true" aria-labelledby="maintenance-dialog-title">
      <div className="maintenance-dialog__backdrop" aria-hidden="true" />
      <div className="maintenance-dialog__content">
        <div className="maintenance-dialog__header">
          <h3 id="maintenance-dialog-title">{title}</h3>
        </div>
        <div className="maintenance-dialog__body">
          {message.split("\n").map((line, index) => (
            <p key={`${index}-${line}`}>{line}</p>
          ))}
        </div>
        <div className="maintenance-dialog__footer">
          <button type="button" className="maintenance-btn maintenance-btn--ghost" onClick={onCancel} disabled={processing}>
            {cancelLabel}
          </button>
          <button type="button" className="maintenance-btn" onClick={onConfirm} disabled={processing}>
            {processing ? "Attendi..." : confirmLabel}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

ConfirmationDialog.propTypes = {
  open: PropTypes.bool.isRequired,
  title: PropTypes.string.isRequired,
  message: PropTypes.string.isRequired,
  confirmLabel: PropTypes.string,
  cancelLabel: PropTypes.string,
  onConfirm: PropTypes.func.isRequired,
  onCancel: PropTypes.func.isRequired,
  processing: PropTypes.bool,
};

ConfirmationDialog.defaultProps = {
  confirmLabel: "Conferma",
  cancelLabel: "Annulla",
  processing: false,
};

export default ConfirmationDialog;

