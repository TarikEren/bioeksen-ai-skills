# CI in a Next.js app

This reference describes apps scaffolded from the nextjs template of
bioeksen-app-setup: a Next.js App Router project in TypeScript, built with
pnpm, tested with Jest and Playwright, with Prisma for its databases. It is how
that template carries out `SKILL.md`, which outranks it, and the project's
`/AGENTS.md`. Another Next.js app maps the names below to its own.

## Read first

1. **`/AGENTS.md` § Delivery**, and the scripts in `package.json`: which checks
   exist and what each one runs. It names where this app implements
   `SKILL.md`.
2. **`.forgejo/workflows/ci.yml`, the Dockerfile and any local-development
   compose file.**

## The jobs

- **Installs follow the lockfile**: `pnpm install --frozen-lockfile`.
- **The toolchain**: a job checks that Node
  matches `.nvmrc` and pnpm matches `packageManager`.
- **End-to-end tests use the image's Chromium.** Upgrading `@playwright/test`
  needs an image carrying its browser: say so when you propose one.
- **Generated code is generated in the job** (the Prisma client by
  `postinstall`, the route types by `typecheck`).
- **Databases**: `TEST_DATABASE_HOSTS` lists the service names a suite may
  empty a database on.

## Branches

- **Feature branches** (`feature/<slug>`) are the template's units: they run
  every suite on every push and pull request.
- **Role branches** (`role/<agent>`) live in local worktrees and never reach
  CI. AI tasks' branches (`ai/task-{n}`) reach it through their pull requests
  into a feature branch.

## The container image

- **A pinned base image**, by digest, with the Node version `.nvmrc` names.
- **Next.js standalone output**, so the image carries only the files the
  server needs.
- **The `.dockerignore`** keeps out `node_modules` among the installed
  dependencies.
- **No migrations in the image.** `db:deploy` runs from the release's tagged
  commit, as a step of the deployment `/AGENTS.md` § Delivery describes.
- **Compose files are for local development only**, named `compose.dev.yaml`.
