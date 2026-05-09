import express from "express";
import { requireAuth } from "../auth.js";

export const app = express();

// @design: secure-endpoints#auth-required
app.get("/orders/:id", requireAuth, (req, res) => {
  res.json({ id: req.params.id, viewer: req.user });
});
