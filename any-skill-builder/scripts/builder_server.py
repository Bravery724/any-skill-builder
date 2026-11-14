"""Loopback-only questionnaire bridge; completion returns to the waiting host."""
from __future__ import annotations

import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
import threading
from urllib.parse import parse_qs, unquote, urlsplit

from builder_core import BuilderError, require, render_html, request_ai, reset_answers, safe_asset, status, submission, update_answers


class QuestionnaireServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, workspace, port=0):
        self.workspace = Path(workspace).resolve()
        self.token = secrets.token_urlsafe(32)
        self.operation_lock = threading.Lock()
        self.final_event = None
        self.run_id = status(self.workspace, True)["questionnaire"]["run_id"]
        super().__init__(("127.0.0.1", port), QuestionnaireHandler)
        self.origin = f"http://127.0.0.1:{self.server_port}"

    @property
    def url(self):
        return self.origin + "/?token=" + self.token

    def finish(self, event):
        if self.final_event is None:
            self.final_event = event
            timer = threading.Timer(0.25, self.shutdown)
            timer.daemon = True
            timer.start()


class QuestionnaireHandler(BaseHTTPRequestHandler):
    server_version = "SkillBuilder/1"

    def log_message(self, *_):
        pass

    def _authorize(self, write=False):
        expected = f"127.0.0.1:{self.server.server_port}"
        require(self.headers.get("Host") == expected, "Unexpected Host header.", "forbidden_host", 403)
        values = parse_qs(urlsplit(self.path).query)
        supplied = values.get("token", [""])[0]
        require(hmac.compare_digest(supplied, self.server.token), "Missing or invalid questionnaire token.", "unauthorized", 401)
        origin = self.headers.get("Origin")
        if origin is not None:
            require(origin == self.server.origin, "Cross-origin request rejected.", "forbidden_origin", 403)
        if write:
            require(self.headers.get("Sec-Fetch-Site", "same-origin") in {"same-origin", "none"},
                    "Cross-site request rejected.", "forbidden_origin", 403)

    def _send(self, code, payload, mime="application/json; charset=utf-8"):
        if not isinstance(payload, bytes):
            payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        if mime.startswith("text/html"):
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        elif mime.startswith("image/svg"):
            self.send_header("Content-Security-Policy", "default-src 'none'; sandbox")
        self.end_headers()
        self.wfile.write(payload)
        self.wfile.flush()

    def _error(self, error):
        self._send(error.status, {"error": error.code, "message": error.message})

    def do_GET(self):
        try:
            self._authorize()
            route = unquote(urlsplit(self.path).path)
            if route == "/":
                html = render_html(self.server.workspace, "live", self.server.token)
                self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            elif route == "/api/state":
                self._send(200, status(self.server.workspace, True))
            elif route.startswith("/assets/"):
                relative = route.lstrip("/")
                view = status(self.server.workspace, True)
                registered = {option["image"] for q in view["questionnaire"]["questions"] if q["type"] == "image" for option in q["options"]}
                require(relative in registered, "Image is not registered in this questionnaire.", "not_found", 404)
                path = safe_asset(self.server.workspace, relative)
                mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                self._send(200, path.read_bytes(), mime)
            else:
                raise BuilderError("Resource not found.", "not_found", 404)
        except BuilderError as exc:
            self._error(exc)
        except (OSError, UnicodeError) as exc:
            self._error(BuilderError(f"Cannot read workspace resource: {exc}", "io_error", 500))

    def do_POST(self):
        try:
            self._authorize(write=True)
            require(self.headers.get("Content-Type", "").split(";", 1)[0].strip() == "application/json",
                    "Use application/json.", "unsupported_media_type", 415)
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise BuilderError("Invalid Content-Length.", "invalid_input", 400)
            require(0 < length <= 2 * 1024 * 1024, "Request size must be between 1 byte and 2 MiB.", "request_too_large", 413)
            self.connection.settimeout(10)
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise BuilderError(f"Invalid JSON: {exc}", "invalid_json", 400)
            route = urlsplit(self.path).path
            with self.server.operation_lock:
                require(self.server.final_event is None, "This submission is already complete.", "already_submitted", 409)
                if route == "/api/answers":
                    self._send(200, update_answers(self.server.workspace, payload, "user"))
                elif route == "/api/reset":
                    self._send(200, reset_answers(self.server.workspace, payload))
                elif route == "/api/delegate":
                    result = request_ai(self.server.workspace, payload)
                    record = result["request"]
                    event = {"event": "ai_requested", "scope": "unanswered", "workspace": str(self.server.workspace),
                             "project_id": record["project_id"], "run_id": record["run_id"],
                             "revision": record["revision"], "answer_revision": record["answer_revision"],
                             "request_id": record["request_id"], "protected_question_ids": record["protected_question_ids"],
                             "unanswered_question_ids": record["unanswered_question_ids"], "waiting_question_ids": record["waiting_question_ids"],
                             "counts": result["view"]["counts"]}
                    try:
                        self._send(200, result)
                    finally:
                        self.server.finish(event)
                elif route == "/api/submit":
                    result = submission(self.server.workspace, payload)
                    event = {"event": result["event"], "workspace": str(self.server.workspace),
                             "request_id": result["request"]["request_id"],
                             "project_id": result["view"]["questionnaire"]["project_id"],
                             "run_id": result["view"]["questionnaire"]["run_id"],
                             "revision": result["view"]["questionnaire"]["revision"],
                             "answer_revision": result["view"]["answers"]["answer_revision"],
                             "counts": result["view"]["counts"]}
                    try:
                        self._send(200, result)
                    finally:
                        self.server.finish(event)
                else:
                    raise BuilderError("Resource not found.", "not_found", 404)
        except BuilderError as exc:
            self._error(exc)
        except (BrokenPipeError, ConnectionResetError):
            pass  # Durable terminal events still reach the waiting host.
        except (OSError, UnicodeError) as exc:
            self._error(BuilderError(f"Cannot save response: {exc}", "io_error", 500))

    def do_OPTIONS(self):
        self._send(403, {"error": "forbidden_origin", "message": "Cross-origin access is disabled."})


def serve(workspace, timeout=3600, port=0):
    require(isinstance(timeout, (int, float)) and timeout > 0, "timeout must be positive.")
    require(type(port) is int and 0 <= port <= 65535, "port must be 0 to 65535.")
    with QuestionnaireServer(workspace, port) as server:
        print(json.dumps({"event": "ready", "url": server.url, "workspace": str(server.workspace),
                          "run_id": server.run_id,
                          "timeout_seconds": timeout}, ensure_ascii=False), flush=True)
        def expire():
            with server.operation_lock:
                server.finish({"event": "timeout", "workspace": str(server.workspace),
                               "message": "Answers remain saved. Restart serve or resume the workspace."})
        timer = threading.Timer(timeout, expire)
        timer.daemon = True
        timer.start()
        try:
            server.serve_forever(poll_interval=0.1)
        except KeyboardInterrupt:
            server.final_event = {"event": "interrupted", "workspace": str(server.workspace), "message": "Saved answers retained."}
        finally:
            timer.cancel()
        final = server.final_event or {"event": "stopped", "workspace": str(server.workspace)}
        print(json.dumps(final, ensure_ascii=False), flush=True)
        return final
