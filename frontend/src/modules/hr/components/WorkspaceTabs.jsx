import React from "react";

const WorkspaceTabs = ({ value, onChange, canViewMonitoring }) => (
  <div className="hr-portal__actions hr-portal__actions--wrap" role="tablist" aria-label="Workspace HR Portal">
    <button
      role="tab"
      aria-selected={value === "operations"}
      className={`hr-portal__button ${value === "operations" ? "" : "hr-portal__button--ghost"}`}
      onClick={() => onChange("operations")}
      type="button"
    >
      Operatività
    </button>
    {canViewMonitoring && (
      <button
        role="tab"
        aria-selected={value === "monitoring"}
        className={`hr-portal__button ${value === "monitoring" ? "" : "hr-portal__button--ghost"}`}
        onClick={() => onChange("monitoring")}
        type="button"
      >
        Monitoraggio
      </button>
    )}
  </div>
);

export default WorkspaceTabs;
