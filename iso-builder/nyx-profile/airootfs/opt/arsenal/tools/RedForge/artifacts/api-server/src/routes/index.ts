import { Router, type IRouter } from "express";
import healthRouter from "./health";
import authRouter from "./auth";
import disclaimerRouter from "./disclaimer";
import dashboardRouter from "./dashboard";
import scenariosRouter from "./scenarios";
import missionsRouter from "./missions";
import notesRouter from "./notes";
import kbRouter from "./kb";
import scoreboardRouter from "./scoreboard";
import networkRouter from "./network";
import settingsRouter from "./settings";
import tutorRouter from "./tutor";

const router: IRouter = Router();

router.use(healthRouter);
router.use(authRouter);
router.use(disclaimerRouter);
router.use(dashboardRouter);
router.use(scenariosRouter);
router.use(missionsRouter);
router.use(notesRouter);
router.use(kbRouter);
router.use(scoreboardRouter);
router.use(networkRouter);
router.use(settingsRouter);
router.use(tutorRouter);

export default router;
