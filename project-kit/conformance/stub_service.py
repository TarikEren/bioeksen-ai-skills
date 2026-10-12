#!/usr/bin/env python3
"""A minimal service serving the five standard endpoints conformingly.

    python stub_service.py [--port 8080] [--operator-token TOKEN]

It exists so check_service.py can be exercised end to end, and doubles as
the shortest readable statement of what those endpoints require of a
response: the error envelope, the X-Request-Id echo, Cache-Control, and the
order in which the selection procedure picks a code. It stores nothing, its
numbers are placeholders, it accepts one fixed operator token in place
of the JWT validation sds-auth requires, it serves one page, /, and it does
not rate limit.
"""
from __future__ import annotations

import argparse
import json
import re
import secrets
import shutil
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
SOFTWARE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CODE_FORMAT = re.compile(r"^[A-Z][A-Z0-9]{1,7}-[45][0-9]{3}$")
SEVERITIES = ("DEBUG", "INFO", "WARNING", "ERROR", "FATAL")
LOG_TYPES = ("APP", "SECURITY", "AUDIT", "ACCESS", "JOB")
RETENTION = timedelta(days=7)
DEFAULT_TOKEN = "stub-operator-token"
# The route templates of the stub's own pages, which a client error report names.
CLIENT_ROUTES = {"/"}
REPORT_LIMIT = 16 * 1024
REPORT_FIELDS = {"route", "error", "cause"}
STARTED = time.monotonic()
GB = 1_000_000_000

# Status and Meaning text, from sds-logging/references/code-prefixes.md.
CODES = {
    "AUTH-4100": (401, "Credential missing"),
    "AUTH-4101": (401, "Credential invalid"),
    "PERM-4153": (403, "Origin not allowed"),
    "VAL-4000": (400, "Request body malformed"),
    "VAL-4001": (400, "Required field missing"),
    "VAL-4002": (400, "Unknown value for an enumerated field"),
    "VAL-4003": (400, "Query parameter malformed"),
    "VAL-4004": (400, "endDate earlier than startDate"),
    "VAL-4005": (400, "Pagination out of range"),
    "VAL-4006": (400, "Field value invalid"),
    "VAL-4007": (400, "Unknown field"),
    "VAL-4550": (413, "Request body too large"),
    "VAL-4600": (415, "Unsupported media type"),
    "RES-4200": (404, "Resource does not exist"),
    "RES-4500": (405, "Method not allowed"),
}


class Fault(Exception):
    """A failure answered with the error envelope."""

    def __init__(self, code: str, field: str | None = None, issue: str | None = None):
        super().__init__(code)
        self.code = code
        self.details = [{"field": field, "issue": issue}] if field else None


def rfc3339(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z")


def parse_time(value: str) -> datetime | None:
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return moment if moment.tzinfo else None  # RFC 3339 requires an offset


class Handler(BaseHTTPRequestHandler):
    operator_token = DEFAULT_TOKEN
    request_id = ""
    body = b""

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - base signature
        pass  # a conformance run wants its own output, not an access log

    def do_GET(self) -> None:
        self.route("GET")

    def do_POST(self) -> None:
        self.route("POST")

    def do_PUT(self) -> None:
        self.route("PUT")

    def do_PATCH(self) -> None:
        self.route("PATCH")

    def do_DELETE(self) -> None:
        self.route("DELETE")

    def route(self, method: str) -> None:
        # Adopt a well-formed X-Request-Id; replace an absent or malformed one.
        offered = self.headers.get("X-Request-Id", "")
        self.request_id = offered if REQUEST_ID.match(offered) else secrets.token_hex(8)
        url = urlsplit(self.path)
        query = parse_qs(url.query, keep_blank_values=True)
        # Read the whole body, whatever the answer: one left unread resets the
        # connection before the answer reaches the caller.
        self.body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        routes = {
            "/api/health/live": ("GET", False, self.live),
            "/api/health/ready": ("GET", False, self.ready),
            "/api/health": ("GET", True, self.health),
            "/api/admin/logs": ("GET", True, self.logs),
            "/api/client-errors": ("POST", False, self.client_error),
        }
        try:
            if url.path not in routes:
                raise Fault("RES-4200")
            served, needs_operator, handler = routes[url.path]
            if needs_operator:
                self.authenticate()  # steps 2-6 and 8-10, before the method (step 11)
            if handler == self.client_error and self.headers.get("Origin") != self.origin():
                raise Fault("PERM-4153")  # step 7, before the method too
            if method != served:
                raise Fault("RES-4500")
            status, body = handler(query)
        except Fault as fault:
            status, meaning = CODES[fault.code]
            body = {"status": "fail", "code": fault.code, "message": meaning,
                    "details": fault.details}
        self.send(status, body)

    def origin(self) -> str:
        """The stub's own origin: the scheme and host the request reached it at."""
        return f"http://{self.headers.get('Host', '')}"

    def authenticate(self) -> None:
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise Fault("AUTH-4100")
        if header[len("Bearer "):] != self.operator_token:
            raise Fault("AUTH-4101")

    def send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Request-Id", self.request_id)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def live(self, query) -> tuple[int, dict]:
        return 200, {"status": "ok"}

    def ready(self, query) -> tuple[int, dict]:
        return 200, {"status": "ok", "uptime": int(time.monotonic() - STARTED),
                     "checks": {"db": "na", "cache": "na", "dependencies": {}}}

    def health(self, query) -> tuple[int, dict]:
        disk = shutil.disk_usage(".")
        return 200, {
            "status": "ok",
            "uptime": int(time.monotonic() - STARTED),
            "checks": {
                "db": {"status": "na", "openConnections": 0, "inUseConnections": 0,
                       "idleConnections": 0},
                "cache": "na",
                "dependencies": {},
                # No managed heap to report, so resident memory in both fields.
                "memory": {"totalHeap": 0.05, "usedHeap": 0.05, "totalMemory": 1.0,
                           "usedMemory": 0.5},
                "disk": {"total": disk.total / GB, "used": disk.used / GB,
                         "free": disk.free / GB},
            },
        }

    def client_error(self, query) -> tuple[int, dict]:
        # In selection procedure order: 12, 13, 14, 15, 20, then 21.
        if len(self.body) > REPORT_LIMIT:
            raise Fault("VAL-4550")
        if self.headers.get_content_type() != "application/json":
            raise Fault("VAL-4600")
        try:
            report = json.loads(self.body)
        except ValueError:
            raise Fault("VAL-4000")
        if not isinstance(report, dict):
            raise Fault("VAL-4000")
        for field in ("route", "error"):
            if field not in report:
                raise Fault("VAL-4001", field, "missing")
        for field in sorted(REPORT_FIELDS & report.keys()):
            if not isinstance(report[field], str) or not report[field]:
                raise Fault("VAL-4006", field, "not a string")
        if report["route"] not in CLIENT_ROUTES:
            raise Fault("VAL-4006", "route", "not a route this app serves")
        unknown = sorted(report.keys() - REPORT_FIELDS)
        if unknown:
            raise Fault("VAL-4007", unknown[0], "not a field of a report")
        # A real app logs the report here, per standard-api-endpoints.md.
        return 200, {"status": "ok"}

    def logs(self, query) -> tuple[int, dict]:
        def one(name: str) -> str | None:
            values = query.get(name)
            return values[-1] if values else None

        severity, log_type, code, app = one("severity"), one("type"), one("code"), one("id")
        now = datetime.now(timezone.utc)

        # In selection procedure order: 15, 16, 17, 18, then 19.
        if severity is not None and severity not in SEVERITIES:
            raise Fault("VAL-4002", "severity", "not a severity")
        if log_type is not None and log_type not in LOG_TYPES:
            raise Fault("VAL-4002", "type", "not a log type")
        if code is not None and not CODE_FORMAT.match(code):
            # A real app checks the closed list; the stub checks the format.
            raise Fault("VAL-4002", "code", "not an error code")
        start_raw, end_raw = one("startDate"), one("endDate")
        start = parse_time(start_raw) if start_raw is not None else now - RETENTION
        if start is None:
            raise Fault("VAL-4003", "startDate", "not an RFC 3339 date-time")
        end = parse_time(end_raw) if end_raw is not None else now
        if end is None:
            raise Fault("VAL-4003", "endDate", "not an RFC 3339 date-time")
        numbers = {}
        for name, default in (("page", 1), ("limit", 50)):
            raw = one(name)
            try:
                numbers[name] = int(raw) if raw is not None else default
            except ValueError:
                raise Fault("VAL-4003", name, "not an integer")
        page, limit = numbers["page"], numbers["limit"]
        if end < start:
            raise Fault("VAL-4004", "endDate", "must be at or after startDate")
        if page < 1 or not 1 <= limit <= 200:
            raise Fault("VAL-4005", "limit" if page >= 1 else "page", "out of range")
        if app is not None and not SOFTWARE_ID.match(app):
            raise Fault("VAL-4006", "id", "not a software id")

        start = max(start, now - RETENTION)  # clamped, never rejected
        record = {"id": "conformance-stub", "timestamp": rfc3339(now), "severity": "INFO",
                  "type": "APP", "code": None, "message": "stub answered a query"}
        matches = [record] if all(
            want is None or record[field] == want
            for field, want in (("severity", severity), ("type", log_type),
                                ("code", code), ("id", app))) else []
        shown = matches[(page - 1) * limit:page * limit]
        return 200, {
            "status": "ok", "page": page, "count": len(shown), "totalCount": len(matches),
            "logs": shown,
            "filterParams": {"id": app, "severity": severity, "type": log_type,
                             "code": code, "startDate": rfc3339(start),
                             "endDate": rfc3339(end), "page": page, "limit": limit},
        }


def serve(port: int = 8080, token: str = DEFAULT_TOKEN) -> ThreadingHTTPServer:
    """A server bound to 127.0.0.1:port, not yet serving. Port 0 picks a free one."""
    handler = type("ConfiguredHandler", (Handler,), {"operator_token": token})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Serve the standard endpoints conformingly.")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--operator-token", default=DEFAULT_TOKEN)
    args = parser.parse_args(argv)
    server = serve(args.port, args.operator_token)
    print(f"serving on http://127.0.0.1:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
