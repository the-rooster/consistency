import { Given, When, Then } from "@cucumber/cucumber";
import assert from "node:assert/strict";
import http from "node:http";
import { app } from "../../src/routes/users.js";

interface World {
  server?: http.Server;
  baseUrl?: string;
  response?: { status: number; body: string };
  observedUser?: string;
}

Given("the application is running", async function (this: World) {
  this.server = await new Promise((resolve) => {
    const s = app.listen(0, () => resolve(s));
  });
  const port = (this.server!.address() as { port: number }).port;
  this.baseUrl = `http://127.0.0.1:${port}`;
});

Given(
  "a user {string} has a valid session token {string}",
  function (_user: string, _token: string) {
    // Token mapping is hard-coded in src/auth.ts for this example.
  }
);

When(
  "a client makes a GET request to {string} without a session token",
  async function (this: World, path: string) {
    this.response = await fetchPath(`${this.baseUrl}${path}`);
  }
);

When(
  "a client makes a GET request to {string} with token {string}",
  async function (this: World, path: string, token: string) {
    this.response = await fetchPath(`${this.baseUrl}${path}`, token);
  }
);

Then("the response status is {int}", function (this: World, code: number) {
  assert.equal(this.response!.status, code);
});

Then(
  "the handler observed req.user equal to {string}",
  function (this: World, expected: string) {
    const body = JSON.parse(this.response!.body);
    assert.equal(body.viewer, expected);
  }
);

async function fetchPath(url: string, token?: string) {
  return new Promise<{ status: number; body: string }>((resolve, reject) => {
    const headers: Record<string, string> = token
      ? { Authorization: `Bearer ${token}` }
      : {};
    const req = http.get(url, { headers }, (res) => {
      let body = "";
      res.on("data", (c) => (body += c));
      res.on("end", () =>
        resolve({ status: res.statusCode ?? 0, body })
      );
    });
    req.on("error", reject);
  });
}
