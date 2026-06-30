import React from "react";
import { createRoot } from "react-dom/client";
import MaintenanceApp from "./modules/maintenance/MaintenanceApp";
import "./pwa/registration";

const container = document.getElementById("maintenance-root");
if (container) {
  const root = createRoot(container);
  root.render(<MaintenanceApp />);
}
