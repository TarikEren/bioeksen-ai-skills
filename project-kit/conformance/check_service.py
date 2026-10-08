#!/usr/bin/env python3
"""Check a running service against the four standard endpoints, or check the check.

    python check_service.py --base-url http://localhost:8080 [--operator-token TOKEN]
    python check_service.py --self-test

The check itself is the sds-testing skill's own script,
plugins/bioeksen-sds/skills/sds-testing/scripts/check_service.py, which an
installed plugin carries so an assistant can run it beside the schemas it
reads. --base-url runs it as it is. --self-test is the kit's own: it validates
the fixtures beside this file against the schemas, then runs every check
against stub_service.py. Run it after changing a schema.

Requires the packages in project-kit/requirements.txt.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = (HERE.parent.parent / "plugins" / "bioeksen-sds" / "skills" / "sds-testing"
          / "scripts" / "check_service.py")

_spec = importlib.util.spec_from_file_location("sds_check_service", SCRIPT)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)


def self_test() -> int:
    """Fixtures against the schemas, then every check against the stub."""
    if check.MISSING:
        return check.main(["--base-url", "http://127.0.0.1:9"])
    schemas = check.Schemas()
    results: list[tuple[str, list[str] | None]] = []
    for fixture in sorted((HERE / "fixtures").glob("*.json")):
        for case in json.loads(fixture.read_text(encoding="utf-8")):
            file, _, pointer = case["schema"].partition("#")
            errors = schemas.errors(pointer, case["instance"], check.SCHEMA_FILES[file])
            verdict = "valid" if case["valid"] else "invalid"
            problems = [] if (not errors) == case["valid"] else (
                errors or [f"accepted, though the fixture says it is {verdict}"])
            results.append((f"{fixture.stem}: {case['name']} is {verdict}", problems))

    sys.path.insert(0, str(HERE))
    from stub_service import DEFAULT_TOKEN, serve
    server = serve(port=0)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        results += [(f"stub: {name}", problems) for name, problems
                    in check.run_checks(base_url, DEFAULT_TOKEN, schemas)]
    finally:
        server.shutdown()
    return check.report(results)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a service against the standard "
                                                 "endpoints, or check the check.")
    parser.add_argument("--self-test", action="store_true",
                        help="check the fixtures and the stub service instead")
    args, rest = parser.parse_known_args(argv)
    return self_test() if args.self_test else check.main(rest)


if __name__ == "__main__":
    sys.exit(main())
