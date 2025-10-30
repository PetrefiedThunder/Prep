import type { JwtPayload } from 'jsonwebtoken';

declare global {
  namespace Express {
    interface UserClaims {
      id: string;
      roles: string[];
      token: string;
      claims: JwtPayload & {
        sub: string;
      };
    }

    interface Request {
      user?: UserClaims;
    }
  }
}

export {};
