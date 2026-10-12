#!/usr/bin/env python3
"""Check a running service against the five standard endpoints.

    python check_service.py --base-url http://localhost:8080 [--operator-token TOKEN]
                            [--origin https://app.example] [--client-route /]

Every response is checked against the response
sds-api-design/references/openapi.yaml declares for its path and status —
body schema and declared headers — so the schema stays the only definition
and this script restates none of it. On top of that it checks what a schema
cannot express: that X-Request-Id is echoed, or replaced when malformed; that
a request without a credential gets 401 AUTH-4100; and, given an operator
token (or BIOEKSEN_OPERATOR_TOKEN), that each bad query parameter gets the
code the selection procedure gives it. For POST /api/client-errors it checks
that a report from another site gets 403 PERM-4153, that a report needs no
credential, that a route the app does not serve gets 400 VAL-4006, and that a
report from the app's own origin and page, --origin and --client-route, is
logged.

It ships with the plugin, beside the schemas it reads, so it runs wherever
the skills are installed. It needs the packages in requirements.txt beside
it. It exits 0 when every check passed, 1 when one failed, and 2 when a check
was not run: the packages are missing, the service cannot be reached, no
operator token was given for the operator checks, or the client error
endpoint's rate limit refused a check. A check not run is never a pass, per
**Keeping the suite honest** in sds-testing/SKILL.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

try:
    import yaml
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except ImportError as error:
    MISSING: str | None = error.name or str(error)
else:
    MISSING = None

HERE = Path(__file__).resolve().parent
REQUIREMENTS = HERE / "requirements.txt"
SKILLS = HERE.parent.parent
SCHEMA_FILES = {
    "openapi.yaml": SKILLS / "sds-api-design" / "references" / "openapi.yaml",
    "aggregator-api.yaml": SKILLS / "sds-logging" / "references" / "aggregator-api.yaml",
    "employees-api.yaml": SKILLS / "sds-auth" / "references" / "employees-api.yaml",
}
OPENAPI = SCHEMA_FILES["openapi.yaml"]
REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
CLIENT_ERRORS = "/api/client-errors"
# An origin no app serves, per RFC 2606.
FOREIGN_ORIGIN = "https://conformance.invalid"


class NotRun(str):
    """A check that could not run, carrying why: reported, counted, and never a pass."""


class Unreachable(Exception):
    """The service under test could not be reached at all."""


def escape(token: str) -> str:
    """One JSON pointer token."""
    return token.replace("~", "~0").replace("/", "~1")


class Schemas:
    """The skills' OpenAPI files, loaded once and resolvable across files."""

    def __init__(self) -> None:
        self.registry = Registry()
        self.docs: dict[Path, dict] = {}
        for path in SCHEMA_FILES.values():
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.docs[path] = doc
            self.registry = self.registry.with_resource(
                path.as_uri(), Resource.from_contents(doc, default_specification=DRAFT202012))
        self.openapi = self.docs[OPENAPI]

    def errors(self, pointer: str, instance, source: Path = OPENAPI) -> list[str]:
        """Why instance fails the schema at pointer in source; empty when it passes."""
        validator = Draft202012Validator({"$ref": f"{source.as_uri()}#{pointer}"},
                                         registry=self.registry,
                                         format_checker=Draft202012Validator.FORMAT_CHECKER)
        return [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
                for e in validator.iter_errors(instance)]

    def deref(self, node, pointer: str) -> tuple[dict, str]:
        """Follow an OpenAPI object's $ref within openapi.yaml, tracking its pointer."""
        while isinstance(node, dict) and "$ref" in node:
            pointer = node["$ref"].lstrip("#")
            node = self.openapi
            for part in pointer.strip("/").split("/"):
                node = node[part.replace("~1", "/").replace("~0", "~")]
        return node, pointer

    def check_response(self, path: str, status: int, headers, body: bytes,
                       method: str = "get") -> list[str]:
        """Problems with a response to method path, judged by what the schema declares."""
        declared = self.openapi["paths"][path][method]["responses"]
        if str(status) not in declared:
            return [f"{status} is not a status the schema declares for "
                    f"{method.upper()} {path}"]
        response, pointer = self.deref(
            declared[str(status)], f"/paths/{escape(path)}/{method}/responses/{status}")
        problems = []
        for name, header in response.get("headers", {}).items():
            header, header_pointer = self.deref(header, f"{pointer}/headers/{escape(name)}")
            value = headers.get(name)
            if value is None:
                if header.get("required"):
                    problems.append(f"no {name} header")
                continue
            if header.get("schema", {}).get("type") == "integer":
                value = int(value) if value.isdigit() else value
            problems += [f"{name} header {e}" for e in self.errors(f"{header_pointer}/schema",
                                                                   value)]
        if "application/json" in response.get("content", {}):
            try:
                parsed = json.loads(body)
            except ValueError:
                return problems + ["the body is not JSON"]
            problems += [f"body {e}" for e in self.errors(
                f"{pointer}/content/application~1json/schema", parsed)]
        return problems


def request(base_url: str, path: str, request_id: str | None = None,
            token: str | None = None, method: str = "GET", body: bytes | None = None,
            headers: dict[str, str] | None = None):
    """Send method to base_url + path, returning (status, headers, body) whatever the
    status."""
    req = urllib.request.Request(base_url.rstrip("/") + path, data=body, method=method)
    for name, value in (headers or {}).items():
        req.add_header(name, value)
    if request_id is not None:
        req.add_header("X-Request-Id", request_id)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        with error:
            return error.code, error.headers, error.read()
    except (urllib.error.URLError, OSError) as error:
        raise Unreachable(f"{base_url}: {getattr(error, 'reason', error)}") from error


def code_of(body: bytes) -> str | None:
    try:
        return json.loads(body).get("code")
    except (ValueError, AttributeError):
        return None


def origin_of(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.netloc}"


def run_checks(base_url: str, token: str | None, schemas: Schemas,
               origin: str | None = None,
               client_route: str = "/") -> list[tuple[str, list[str] | NotRun]]:
    """Every check, as (name, problems) pairs: an empty list is a pass, a NotRun a check
    that could not run."""
    results: list[tuple[str, list[str] | NotRun]] = []
    sent = "conformance" + secrets.token_hex(8)

    def endpoint(path: str, query: str = "", with_token: bool = False,
                 expect: tuple[int, ...] = (), expect_code: str | None = None,
                 report: dict | None = None, from_origin: str | None = None
                 ) -> list[str] | NotRun:
        method = "GET" if report is None else "POST"
        sent_headers = {} if report is None else {"Content-Type": "application/json",
                                                  "Origin": from_origin or ""}
        status, headers, body = request(
            base_url, path + query, sent, token if with_token else None, method,
            None if report is None else json.dumps(report).encode("utf-8"), sent_headers)
        if report is not None and status == 429:
            return NotRun("the endpoint's rate limit refused it; run the check again "
                          "once Retry-After has passed")
        problems = schemas.check_response(path, status, headers, body, method.lower())
        if headers.get("X-Request-Id") != sent:
            problems.append(f"X-Request-Id was not echoed: sent {sent!r}, "
                            f"got {headers.get('X-Request-Id')!r}")
        if expect and status not in expect:
            problems.append(f"answered {status}, expected {' or '.join(map(str, expect))}")
        elif expect_code and code_of(body) != expect_code:
            problems.append(f"code {code_of(body)!r}, expected {expect_code}")
        return problems

    for path in ("/api/health/live", "/api/health/ready"):
        results.append((f"GET {path}", endpoint(path, expect=(200, 503))))
    for path in ("/api/health", "/api/admin/logs"):
        results.append((f"GET {path} without a credential answers 401 AUTH-4100",
                        endpoint(path, expect=(401,), expect_code="AUTH-4100")))

    _, headers, _ = request(base_url, "/api/health/live", "not a valid id!")
    replaced = headers.get("X-Request-Id")
    results.append(("a malformed X-Request-Id is replaced, not echoed", [] if (
        replaced and replaced != "not a valid id!" and REQUEST_ID.match(replaced)) else [
        f"answered X-Request-Id {replaced!r}"]))
    _, headers, _ = request(base_url, "/api/health/live")
    generated = headers.get("X-Request-Id")
    results.append(("an absent X-Request-Id is generated", [] if (
        generated and REQUEST_ID.match(generated)) else [f"answered {generated!r}"]))

    operator_checks = [
        ("GET /api/health with an operator token",
         lambda: endpoint("/api/health", with_token=True, expect=(200, 503))),
        ("GET /api/admin/logs with an operator token",
         lambda: endpoint("/api/admin/logs", with_token=True, expect=(200,))),
    ]
    for query, code in (("?severity=NOPE", "VAL-4002"),
                        ("?startDate=yesterday", "VAL-4003"),
                        ("?startDate=2026-09-02T00:00:00Z&endDate=2026-09-01T00:00:00Z",
                         "VAL-4004"),
                        ("?page=0", "VAL-4005"),
                        ("?limit=0", "VAL-4005"),
                        ("?limit=201", "VAL-4005")):
        operator_checks.append((
            f"GET /api/admin/logs{query} answers 400 {code}",
            lambda q=query, c=code: endpoint("/api/admin/logs", q, with_token=True,
                                             expect=(400,), expect_code=c)))
    for name, check in operator_checks:
        results.append((name, check() if token else NotRun(
            "it needs --operator-token, or BIOEKSEN_OPERATOR_TOKEN")))

    # Four reports, well under the default of 10 a minute from one source.
    own = origin or origin_of(base_url)
    error = "Error: sent by the conformance check"
    for name, report, from_origin, status, code in (
            ("from another site answers 403 PERM-4153",
             {"route": client_route, "error": error}, FOREIGN_ORIGIN, 403, "PERM-4153"),
            ("without a credential, and without a route, answers 400 VAL-4001",
             {"error": error}, own, 400, "VAL-4001"),
            ("naming a route the app does not serve answers 400 VAL-4006",
             {"route": "/conformance-check/[no-such-route]", "error": error}, own, 400,
             "VAL-4006"),
            (f"from the app's own origin and page {client_route} answers 200",
             {"route": client_route, "error": error}, own, 200, None)):
        results.append((f"POST {CLIENT_ERRORS} {name}", endpoint(
            CLIENT_ERRORS, report=report, from_origin=from_origin, expect=(status,),
            expect_code=code)))
    return results


def report(results: list[tuple[str, list[str] | NotRun]]) -> int:
    """Print each result; 1 when a check failed, else 2 when one was not run, else 0."""
    failed = not_run = 0
    for name, problems in results:
        if isinstance(problems, NotRun):
            not_run += 1
            print(f"NOT RUN  {name}: {problems}")
            continue
        print(f"{'FAIL   ' if problems else 'PASS   '}  {name}")
        for problem in problems:
            print(f"           {problem}")
        failed += bool(problems)
    if not_run:
        print(f"{not_run} checks not run, each for the reason beside it")
    passed = len(results) - failed - not_run
    print(f"{passed} of {len(results)} checks passed, {failed} failed, {not_run} not run")
    return 1 if failed else 2 if not_run else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a service against the standard "
                                                 "endpoints.")
    parser.add_argument("--base-url", required=True,
                        help="where the service under test is listening")
    parser.add_argument("--operator-token", default=os.environ.get("BIOEKSEN_OPERATOR_TOKEN"),
                        help="an operator token, enabling the authenticated checks")
    parser.add_argument("--origin",
                        help="the origin the app's pages are served from, when it is not "
                             "the base URL's, as behind a proxy")
    parser.add_argument("--client-route", default="/",
                        help="a route template the app serves a page at (default: /)")
    args = parser.parse_args(argv)
    if MISSING:
        print(f"not run: the conformance check needs {MISSING!r}, which is not installed. "
              f"Install what it needs with\n    pip install -r {REQUIREMENTS}")
        return 2
    try:
        return report(run_checks(args.base_url, args.operator_token, Schemas(),
                                 args.origin, args.client_route))
    except Unreachable as error:
        print(f"not run: the service could not be reached at {error}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
