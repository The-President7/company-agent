// secretary-monitor JavaScript SDK

class SecretaryMonitor {
  constructor({ dsn, projectKey, endpoint, environment = "production", release = "" }) {
    this.projectKey = projectKey || dsn;
    this.endpoint = (endpoint || "http://localhost:8000").replace(/\/$/, "");
    this.environment = environment;
    this.release = release;
    if (!this.projectKey) throw new Error("SecretaryMonitor requires projectKey");
  }
// asynchronous function to capture an exception and send it to the Secretary Monitor server
  async captureException(error, context = {}) {
    const value = error instanceof Error ? error : new Error(String(error));
    return this._send({
      type: "error", title: `${value.name}: ${value.message}`.slice(0, 500),
      message: value.message, stacktrace: value.stack || "", url: context.url || globalThis.location?.href || "",
      environment: this.environment, release: this.release, fingerprint: context.fingerprint,
    });
  }

  async captureTransaction({ name, durationMs, url = "", environment, release }) {
    return this._send({ type: "transaction", title: name, duration_ms: durationMs, url,
      environment: environment || this.environment, release: release || this.release });
  }

  installGlobalHandlers() {
    if (typeof window === "undefined") return;
    window.addEventListener("error", event => { void this.captureException(event.error || event.message); });
    window.addEventListener("unhandledrejection", event => { void this.captureException(event.reason); });
  }

  async _send(event) {
    const response = await fetch(`${this.endpoint}/monitor/events`, {
      method: "POST", headers: { "Content-Type": "application/json", "X-Project-Key": this.projectKey },
      body: JSON.stringify(event), keepalive: true,
    });
    if (!response.ok) throw new Error(`Secretary Monitor rejected event (${response.status})`);
    return response.json();
  }
}

module.exports = { SecretaryMonitor };
