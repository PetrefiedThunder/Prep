import express from 'express';
import cors from 'cors';
import helmet from 'helmet';

import { authenticateRequest } from './middleware/authentication';
import { router as integrationRouter } from './modules/integrations/routes';

const app = express();

app.use(helmet());
app.use(cors());
app.use(express.json());

app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'prep-connect' });
});

app.use('/integrations', authenticateRequest, integrationRouter);

export default app;
