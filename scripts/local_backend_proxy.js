const express = require("express");
const querystring = require("node:querystring");

const PORT = Number(process.env.PORT || 18788);
const HOST = process.env.HOST || "127.0.0.1";

const app = express();

app.use(
  express.raw({
    type: "*/*",
    limit: "10mb",
  }),
);

function setCors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,PUT,PATCH,DELETE,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "*");
}

function logRequest(req) {
  const bodyBuffer = Buffer.isBuffer(req.body) ? req.body : Buffer.alloc(0);
  const contentType = String(req.headers["content-type"] || "");
  const bodyText = bodyBuffer.toString("utf8");

  console.log(`\n[proxy] ${req.method} ${req.originalUrl}`);
  console.log("[proxy] headers", JSON.stringify(req.headers, null, 2));

  if (!bodyBuffer.length) {
    console.log("[proxy] body <empty>");
    return;
  }

  console.log(`[proxy] body-bytes ${bodyBuffer.length}`);
  if (contentType.includes("application/x-www-form-urlencoded")) {
    console.log("[proxy] form", JSON.stringify(querystring.parse(bodyText), null, 2));
    return;
  }

  if (contentType.includes("application/json")) {
    try {
      console.log("[proxy] json", JSON.stringify(JSON.parse(bodyText), null, 2));
      return;
    } catch (_err) {
      // Fall through to the raw preview if JSON parsing fails.
    }
  }

  console.log("[proxy] body-preview");
  console.log(bodyText.slice(0, 4000));
}

app.options("*", (req, res) => {
  setCors(res);
  res.status(204).end();
});

app.get("/", (req, res) => {
  setCors(res);
  res.json({
    ok: true,
    note: "Use this server as the patched backend host for local request logging.",
  });
});

app.all("*", async (req, res) => {
  setCors(res);
  logRequest(req);
  res.status(200).json({
    ok: true,
    intercepted: true,
    method: req.method,
    path: req.originalUrl,
  });
});

app.listen(PORT, HOST, () => {
  console.log(`[proxy] listening on http://${HOST}:${PORT}`);
  console.log("[proxy] forwarding disabled");
});
