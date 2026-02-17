const path = require("path");

const { startServer } = require("next/dist/server/lib/start-server");

const projectDir = path.resolve(__dirname, "..");
const port = Number.parseInt(process.env.PORT || "3000", 10);
const hostname = process.env.HOSTNAME || "localhost";

process.env.NODE_ENV = "development";

startServer({
  dir: projectDir,
  isDev: true,
  hostname,
  port,
  allowRetry: false,
}).catch((error) => {
  // Keep logging simple for Windows consoles
  console.error("dev-no-fork failed:", error?.message || error);
  process.exit(1);
});
