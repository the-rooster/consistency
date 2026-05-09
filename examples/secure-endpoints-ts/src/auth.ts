import type { Request, Response, NextFunction } from "express";

declare module "express-serve-static-core" {
  interface Request {
    user?: string;
  }
}

const TOKENS: Record<string, string> = { "tok-abc": "andrew" };

export function requireAuth(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const auth = req.headers.authorization ?? "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  const user = TOKENS[token];
  if (!user) {
    res.status(401).end();
    return;
  }
  req.user = user;
  next();
}
