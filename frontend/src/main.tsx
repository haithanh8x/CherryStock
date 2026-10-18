import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { applyTheme, resolveTheme } from "./theme/theme";
import "./index.css";
import App from "./App";

let stored: string | null = null;
try { stored = localStorage.getItem("cherrystock-theme"); } catch { /* storage unavailable */ }
applyTheme(resolveTheme(stored));
createRoot(document.getElementById("root")!).render(<StrictMode><App/></StrictMode>);
