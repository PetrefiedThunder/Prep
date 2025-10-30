import type { NextFunction, Request, Response } from 'express';
import jwt, { JwtHeader, JwtPayload } from 'jsonwebtoken';

import { getAuthPublicKey } from '../config/auth';

const SUPPORTED_ALGORITHMS = ['RS256'] as const;

type SupportedAlgorithm = (typeof SUPPORTED_ALGORITHMS)[number];

type VerifiedPayload = JwtPayload & {
  sub: string;
  roles?: string[];
};

function isSupportedAlgorithm(header: JwtHeader): header is JwtHeader & { alg: SupportedAlgorithm } {
  return typeof header.alg === 'string' && SUPPORTED_ALGORITHMS.includes(header.alg as SupportedAlgorithm);
}

function verifyToken(token: string): VerifiedPayload {
  let header: JwtHeader;
  try {
    header = jwt.decode(token, { complete: true })?.header ?? {};
  } catch (error) {
    throw new Error('Invalid token header');
  }

  if (!isSupportedAlgorithm(header)) {
    throw new Error('Unsupported token algorithm');
  }

  const publicKey = getAuthPublicKey();
  const payload = jwt.verify(token, publicKey, {
    algorithms: SUPPORTED_ALGORITHMS,
  });

  if (!payload || typeof payload !== 'object') {
    throw new Error('Token payload missing');
  }

  if (!('sub' in payload) || typeof payload.sub !== 'string') {
    throw new Error('Subject claim missing');
  }

  return payload as VerifiedPayload;
}

export function authenticateRequest(req: Request, res: Response, next: NextFunction): void {
  const header = req.header('authorization');
  if (!header?.toLowerCase().startsWith('bearer ')) {
    res.status(401).json({ detail: 'Missing bearer token' });
    return;
  }

  const token = header.slice(7);

  try {
    const payload = verifyToken(token);
    req.user = {
      id: payload.sub,
      roles: Array.isArray(payload.roles) ? payload.roles : [],
      token,
      claims: payload,
    };
    next();
  } catch (error) {
    res.status(401).json({ detail: (error as Error).message });
  }
}
