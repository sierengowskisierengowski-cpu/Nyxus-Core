import { Router, type IRouter } from "express";
import healthRouter from "./health";
import chatRouter from "./chat";
import schedulerRouter from "./scheduler";
import knowledgeRouter from "./knowledge";
import activityRouter from "./activity";
import quickActionsRouter from "./quickactions";
import settingsRouter from "./settings";
import aiRouter from "./ai";
import filesRouter from "./files";
import statsRouter from "./stats";

const router: IRouter = Router();

router.use(healthRouter);
router.use(chatRouter);
router.use(schedulerRouter);
router.use(knowledgeRouter);
router.use(activityRouter);
router.use(quickActionsRouter);
router.use(settingsRouter);
router.use(aiRouter);
router.use(filesRouter);
router.use(statsRouter);

export default router;
