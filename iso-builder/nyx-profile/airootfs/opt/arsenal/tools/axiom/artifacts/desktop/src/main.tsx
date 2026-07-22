import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";
import { setBaseUrl, setAuthTokenGetter } from "@workspace/api-client-react";
import { electron } from "@/lib/electron-api";

// In packaged Electron the renderer loads via file://, so relative /api
// requests don't resolve. Point the API client at the spawned local server
// and attach the per-session auth token to every request.
if (window.location.protocol === "file:") {
  setBaseUrl("http://127.0.0.1:8080");
  setAuthTokenGetter(() => electron.getLocalToken());
}

createRoot(document.getElementById("root")!).render(<App />);
