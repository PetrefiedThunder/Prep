import { Router } from 'express';

import { integrations } from './repository';
import type { IntegrationInput } from './types';

export const router = Router();

router.get('/', (req, res) => {
  if (!req.user) {
    res.status(401).json({ detail: 'Unauthorized' });
    return;
  }

  const results = integrations.listByUser(req.user.id);
  res.json({ data: results });
});

router.post('/', (req, res) => {
  if (!req.user) {
    res.status(401).json({ detail: 'Unauthorized' });
    return;
  }

  const payload = req.body as IntegrationInput | undefined;
  if (!payload) {
    res.status(400).json({ detail: 'Request body is required' });
    return;
  }

  const requiredFields: (keyof IntegrationInput)[] = [
    'serviceType',
    'vendorName',
    'authMethod',
    'syncFrequency',
  ];
  for (const field of requiredFields) {
    if (!payload[field]) {
      res.status(400).json({ detail: `Field ${String(field)} is required` });
      return;
    }
  }

  const created = integrations.create(req.user.id, payload);
  res.status(201).json(created);
});

router.patch('/:integrationId', (req, res) => {
  if (!req.user) {
    res.status(401).json({ detail: 'Unauthorized' });
    return;
  }

  const { integrationId } = req.params;
  const payload = req.body as IntegrationInput | undefined;

  if (!payload) {
    res.status(400).json({ detail: 'Request body is required' });
    return;
  }

  const existing = integrations.get(integrationId);
  if (!existing || existing.userId !== req.user.id) {
    res.status(404).json({ detail: 'Integration not found' });
    return;
  }

  const updated = integrations.update(integrationId, payload);
  if (!updated) {
    res.status(404).json({ detail: 'Integration not found' });
    return;
  }

  res.json(updated);
});

router.delete('/:integrationId', (req, res) => {
  if (!req.user) {
    res.status(401).json({ detail: 'Unauthorized' });
    return;
  }

  const { integrationId } = req.params;
  const existing = integrations.get(integrationId);
  if (!existing || existing.userId !== req.user.id) {
    res.status(404).json({ detail: 'Integration not found' });
    return;
  }

  integrations.delete(integrationId);
  res.status(204).send();
});
