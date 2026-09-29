#!/usr/bin/env python3
"""Check a running service against the four standard endpoints.

    python check_service.py --base-url http://localhost:8080 [--operator-token TOKEN]
    python check_service.py --self-test

Every response is checked against the response
sds-api-design/references/openapi.yaml declares for its path and status —
body schema and declared headers — so the schema stays the only definition
and this script restates none of it. On top of that it checks what a schema
cannot express: that X-Request-Id is echoed, or replaced when malformed; that
a request without a credential gets 401 AUTH-4100; and, given an operator
token (or BIOEKSEN_OPERATOR_TOKEN), that each bad query parameter gets the
code the selection procedure gives it.

--self-test validates the fixtures beside this file, then runs every check
against stub_service.py. Run it after changing a schema.

Requires the packages in project-kit/requirements.txt.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent / "plugins" / "bioeksen-sds" / "skills"
SCHEMA_FILES = {
    "openapi.yaml": SKILLS / "sds-api-design" / "references" / "openapi.yaml",
    "aggregator-api.yaml": SKILLS / "sds-logging" / "references" / "aggregator-api.yaml",
}
OPENAPI = SCHEMA_FILES["openapi.yaml"]
REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


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

    def check_response(self, path: str, status: int, headers, body: bytes) -> list[str]:
        """Problems with a response to GET path, judged by what the schema declares."""
        declared = self.openapi["paths"][path]["get"]["responses"]
        if str(status) not in declared:
            return [f"{status} is not a status the schema declares for GET {path}"]
        response, pointer = self.deref(
            declared[str(status)], f"/paths/{escape(path)}/get/responses/{status}")
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
            token: str | None = None):
    """GET base_url + path, returning (status, headers, body) whatever the status."""
    req = urllib.request.Request(base_url.rstrip("/") + path, method="GET")
    if request_id is not None:
        req.add_header("X-Request-Id", request_id)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def code_of(body: bytes) -> str | None:
    try:
        return json.loads(body).get("code")
    except (ValueError, AttributeError):
        return None


def run_checks(base_url: str, token: str | None, schemas: Schemas) -> list[tuple[str, list[str]]]:
    """Every check, as (name, problems) pairs; an empty list of problems is a pass."""
    results: list[tuple[str, list[str]]] = []
    sent = "conformance" + secrets.token_hex(8)

    def endpoint(path: str, query: str = "", with_token: bool = False,
                 expect: tuple[int, ...] = (), expect_code: str | None = None) -> list[str]:
        status, headers, body = request(base_url, path + query, sent,
                                        token if with_token else None)
        problems = schemas.check_response(path, status, headers, body)
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

    if not token:
        results.append(("operator checks skipped: no --operator-token or "
                        "BIOEKSEN_OPERATOR_TOKEN", []))
        return results
    results.append(("GET /api/health with an operator token",
                    endpoint("/api/health", with_token=True, expect=(200, 503))))
    results.append(("GET /api/admin/logs with an operator token",
                    endpoint("/api/admin/logs", with_token=True, expect=(200,))))
    for query, code in (("?severity=NOPE", "VAL-4002"),
                        ("?startDate=yesterday", "VAL-4003"),
                        ("?startDate=2026-09-02T00:00:00Z&endDate=2026-09-01T00:00:00Z",
                         "VAL-4004"),
                        ("?page=0", "VAL-4005"),
                        ("?limit=0", "VAL-4005"),
                        ("?limit=201", "VAL-4005")):
        results.append((f"GET /api/admin/logs{query} answers 400 {code}",
                        endpoint("/api/admin/logs", query, with_token=True,
                                 expect=(400,), expect_code=code)))
    return results


def report(results: list[tuple[str, list[str]]]) -> int:
    failed = 0
    for name, problems in results:
        print(f"{'FAIL' if problems else 'PASS'}  {name}")
        for problem in problems:
            print(f"        {problem}")
        failed += bool(problems)
    print(f"{len(results) - failed} of {len(results)} checks passed")
    return 1 if failed else 0


def self_test(schemas: Schemas) -> int:
    """Fixtures against the schemas, then every check against the stub."""
    results: list[tuple[str, list[str]]] = []
    for fixture in sorted((HERE / "fixtures").glob("*.json")):
        for case in json.loads(fixture.read_text(encoding="utf-8")):
            file, _, pointer = case["schema"].partition("#")
            errors = schemas.errors(pointer, case["instance"], SCHEMA_FILES[file])
            verdict = "valid" if case["valid"] else "invalid"
            problems = [] if (not errors) == case["valid"] else (
                errors or [f"accepted, though the fixture says it is {verdict}"])
            results.append((f"{fixture.stem}: {case['name']} is {verdict}", problems))

    from stub_service import DEFAULT_TOKEN, serve
    server = serve(port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        results += [(f"stub: {name}", problems)
                    for name, problems in run_checks(base_url, DEFAULT_TOKEN, schemas)]
    finally:
        server.shutdown()
    return report(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a service against the standard "
                                                 "endpoints.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--base-url", help="where the service under test is listening")
    mode.add_argument("--self-test", action="store_true",
                      help="check the fixtures and the stub service instead")
    parser.add_argument("--operator-token", default=os.environ.get("BIOEKSEN_OPERATOR_TOKEN"),
                        help="an operator token, enabling the authenticated checks")
    args = parser.parse_args(argv)
    schemas = Schemas()
    if args.self_test:
        return self_test(schemas)
    return report(run_checks(args.base_url, args.operator_token, schemas))


if __name__ == "__main__":
    sys.exit(main())
