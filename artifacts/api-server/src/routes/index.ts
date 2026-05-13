import { Router, type IRouter } from "express";
import healthRouter from "./health";
import downloadRouter from "./download";
import nyxusAccountRouter from "./nyxus-account";

const router: IRouter = Router();

router.use(healthRouter);
router.use(downloadRouter);
router.use(nyxusAccountRouter);

export default router;
