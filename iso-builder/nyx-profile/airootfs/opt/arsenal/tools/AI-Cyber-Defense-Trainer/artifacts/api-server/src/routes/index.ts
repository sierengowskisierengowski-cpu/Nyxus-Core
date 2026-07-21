import { Router, type IRouter } from "express";
import healthRouter from "./health";
import authRouter from "./auth";
import missionsRouter from "./missions";
import notesRouter from "./notes";
import networkRouter from "./network";
import statsRouter from "./stats";
import dashboardRouter from "./dashboard";
import knowledgeBaseRouter from "./knowledge-base";

const router: IRouter = Router();

router.use(healthRouter);
router.use(authRouter);
router.use(missionsRouter);
router.use(notesRouter);
router.use(networkRouter);
router.use(statsRouter);
router.use(dashboardRouter);
router.use(knowledgeBaseRouter);

export default router;
