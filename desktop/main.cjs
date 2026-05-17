const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("node:child_process");
const http = require("node:http");
const path = require("node:path");

const BACKEND_PORT = 8000;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const HEALTH_URL = `${BACKEND_URL}/api/health`;

let backendProcess = null;

function appRoot() {
  return app.isPackaged ? process.resourcesPath : path.resolve(__dirname, "..");
}

function backendRoot() {
  return path.join(appRoot(), "backend");
}

function frontendIndex() {
  return path.join(appRoot(), "frontend", "dist", "index.html");
}

function pythonCandidates() {
  const backendPath = backendRoot();
  if (process.platform === "win32") {
    return [
      path.join(backendPath, ".venv", "Scripts", "python.exe"),
      "py",
      "python"
    ];
  }

  return [
    path.join(backendPath, ".venv", "bin", "python3"),
    path.join(backendPath, ".venv", "bin", "python"),
    "python3",
    "python"
  ];
}

function startBackend() {
  const args = ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(BACKEND_PORT)];
  const candidates = pythonCandidates();
  const command = candidates[0];

  backendProcess = spawn(command, args, {
    cwd: backendRoot(),
    env: {
      ...process.env,
      PYTHONUNBUFFERED: "1"
    },
    stdio: app.isPackaged ? "ignore" : "inherit",
    windowsHide: true
  });

  backendProcess.on("error", async (error) => {
    const fallbackCommand = candidates.find((candidate) => candidate !== command);
    if (!fallbackCommand) {
      await showBackendError(error);
      return;
    }

    backendProcess = spawn(fallbackCommand, args, {
      cwd: backendRoot(),
      env: {
        ...process.env,
        PYTHONUNBUFFERED: "1"
      },
      stdio: app.isPackaged ? "ignore" : "inherit",
      windowsHide: true
    });
  });
}

function waitForBackend(timeoutMs = 20000) {
  const startedAt = Date.now();

  return new Promise((resolve, reject) => {
    function attempt() {
      const request = http.get(HEALTH_URL, (response) => {
        response.resume();
        if (response.statusCode === 200) {
          resolve();
          return;
        }
        retry();
      });

      request.on("error", retry);
      request.setTimeout(1000, () => {
        request.destroy();
        retry();
      });
    }

    function retry() {
      if (Date.now() - startedAt >= timeoutMs) {
        reject(new Error(`Backend did not start at ${HEALTH_URL}`));
        return;
      }

      setTimeout(attempt, 500);
    }

    attempt();
  });
}

async function showBackendError(error) {
  await dialog.showMessageBox({
    type: "error",
    title: "Backend could not start",
    message: "Prasad FX Billing could not start the local backend.",
    detail: `${error.message}\n\nInstall Python, create backend/.venv, install backend/requirements.txt, and confirm MySQL is running.`
  });
}

async function createWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 1100,
    minHeight: 700,
    title: "Prasad FX Billing",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  });

  await window.loadFile(frontendIndex());
}

app.whenReady().then(async () => {
  startBackend();

  try {
    await waitForBackend();
  } catch (error) {
    await showBackendError(error);
  }

  await createWindow();

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on("before-quit", () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
