import { Router, type IRouter } from "express";
import healthRouter from "./health";
import dashboardRouter from "./dashboard";
import inputsRouter from "./inputs";
import threatsRouter from "./threats";
import detectionRulesRouter from "./detection-rules";
import notesRouter from "./notes";
import knowledgeRouter from "./knowledge";
import integrationsRouter from "./integrations";
import settingsRouter from "./settings";
import anthropicRouter from "./anthropic";

const router: IRouter = Router();

router.use(healthRouter);
router.use(dashboardRouter);
router.use(inputsRouter);
router.use(threatsRouter);
router.use(detectionRulesRouter);
router.use(notesRouter);
router.use(knowledgeRouter);
router.use(integrationsRouter);
router.use(settingsRouter);
router.use(anthropicRouter);

export default router;
