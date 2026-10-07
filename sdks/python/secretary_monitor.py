"""Small standard-library client for Secretary's monitoring event API."""

import json
import os
import traceback
import urllib.error
import urllib.request


class SecretaryMonitor:
    def __init__(self, project_key=None, endpoint=None, environment="production", release=""):
        self.project_key = project_key or os.getenv("SECRETARY_PROJECT_KEY", "")
        if not self.project_key:
            raise ValueError("Provide project_key or set SECRETARY_PROJECT_KEY")
        self.endpoint = (endpoint or os.getenv("SECRETARY_ENDPOINT", "http://localhost:8000")).rstrip("/")
        self.environment = environment
        self.release = release

    def capture_exception(self, error, *, fingerprint=None, url=""):
        return self._send({
            "type": "error", "title": f"{type(error).__name__}: {error}"[:500],
            "message": str(error)[:12000], "stacktrace": "".join(traceback.format_exception(error))[-100000:],
            "fingerprint": fingerprint, "url": url, "environment": self.environment,
            "release": self.release,
        })

    def capture_transaction(self, name, duration_ms, *, url=""):
        return self._send({"type": "transaction", "title": name[:500], "duration_ms": duration_ms,
                           "url": url, "environment": self.environment, "release": self.release})

    def _send(self, event):
        request = urllib.request.Request(
            f"{self.endpoint}/monitor/events", data=json.dumps(event).encode(), method="POST",
            headers={"Content-Type": "application/json", "X-Project-Key": self.project_key},
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return json.loads(response.read())
        except (urllib.error.URLError, TimeoutError) as exc:
            raise RuntimeError("Could not send event to Secretary Monitor") from exc
