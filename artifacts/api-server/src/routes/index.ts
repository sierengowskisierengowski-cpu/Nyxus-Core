import { Router, type IRouter } from "express";
import healthRouter from "./health";
import downloadRouter from "./download";
import nyxusAccountRouter from "./nyxus-account";
import securityRouter from "./security";
import crashReportsRouter from "./crash-reports";

const router: IRouter = Router();

router.use(healthRouter);
router.use(downloadRouter);
router.use(nyxusAccountRouter);
router.use(securityRouter);
router.use(crashReportsRouter);

export default router;
