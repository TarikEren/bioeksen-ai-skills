# Working in this repository

This is a BioEksen service. The conventions every BioEksen service shares —
the standard endpoints, error codes, logging, authentication, commits, release
notes and test-first development — live in the `bioeksen-sds` plugin's skills,
not in this file.
They load on their own when a task needs them; `.claude/settings.json`
installs them once this folder is trusted.

Where this repository's own documents and a skill disagree about a shared
convention, the skill wins and this repository gets corrected.

## The software id

This service's software id is in `.bioeksen/software-id`. It names the service
in every log record, in every commit's `Change-Id:` trailer and in every
release note entry. Read it from that file. Never invent one, never derive one
from a repository or directory name, and never change it: when the file is
missing or empty, ask for the id.

## Rules that are easy to break

- Work test-first, per the `sds-testing` skill: no behaviour changes without a
  test that failed before the change and passes after it. A `feat` or `fix`
  commit that changes no test names its exemption in a `Test-Exempt:` trailer,
  and only an exemption that skill lists counts.
- Error codes come verbatim from the closed list in the `sds-logging` skill.
  When none fits, the code is `SYS-5000`. A new code is added to that list by a
  human, never invented in this repository.
- Every commit follows the `sds-commit` skill and carries exactly one
  `Change-Id:` trailer. The hook in `.githooks/` mints one when it is missing;
  enable it once per clone with `git config core.hooksPath .githooks`.
- Every release gets `release-notes/{version}.md`, with one entry per commit,
  and a `v{version}` tag on the commit that adds the note.

## Checks

`.bioeksen-sds/` is a checkout of bioeksen-ai-skills at the release pinned in
`.claude/settings.json`. CI makes one through `.github/workflows/bioeksen.yml`;
to make one locally, clone that release into it:

```bash
git clone --depth 1 --branch <the pinned release> https://github.com/TarikEren/bioeksen-ai-skills .bioeksen-sds
```

Then:

- `python .bioeksen-sds/project-kit/tools/commit_msg.py --range origin/main..HEAD`
  checks this branch's commit messages.
- `python .bioeksen-sds/project-kit/tools/check_tests.py --range origin/main..HEAD`
  checks that each of this branch's `feat` and `fix` commits changes a test or
  names its exemption. What counts as a test is listed in `.bioeksen/test-paths`
  when the project declares it, and is a built-in list otherwise.
- `python .bioeksen-sds/project-kit/tools/check_release_note.py <version>`
  checks a release note, after its commit and before the tag.
- `python .bioeksen-sds/project-kit/conformance/check_service.py --base-url http://localhost:<port>`
  checks a running instance's standard endpoints, after
  `pip install -r .bioeksen-sds/project-kit/requirements.txt`.

## This project

<!-- Notes specific to this service go below. -->
