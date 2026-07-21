import { createRoot } from "react-dom/client";
import { setAuthTokenGetter } from "@workspace/api-client-react";
import App from "./App";
import { getToken } from "./lib/auth";
import "./index.css";

// Attach the stored owner token (if any) as a bearer header on every API call.
setAuthTokenGetter(() => getToken());

createRoot(document.getElementById("root")!).render(<App />);
