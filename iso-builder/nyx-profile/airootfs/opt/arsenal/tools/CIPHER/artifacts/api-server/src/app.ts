import express, { type Express } from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";
import { ensureWorkspace } from "./lib/workspace-paths";
import { markStaleJobsInterrupted } from "./lib/cracker";
import { isAuthConfigured } from "./lib/auth";

const app: Express = express();

// One-time startup: create the app-owned working dir and reset any jobs that
// were mid-run when the server last stopped (their real processes are gone).
ensureWorkspace();
void markStaleJobsInterrupted();
if (!isAuthConfigured()) {
  logger.warn(
    "CIPHER_PASSWORD / CIPHER_PASSWORD_HASH is not set — tool-running endpoints are locked until an owner password is configured.",
  );
}

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);
app.use(cors());
app.use(cookieParser());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use("/api", router);

export default app;
