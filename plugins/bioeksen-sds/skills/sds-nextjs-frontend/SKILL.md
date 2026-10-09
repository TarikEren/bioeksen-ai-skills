---
name: sds-nextjs-frontend
description: "Frontend conventions for a Next.js App Router project styled with HeroUI v3 and Tailwind CSS v4 over a Fluent-style brand palette. Rules for type-safe, secure and modular UI code: the server/client trust boundary, HeroUI components only, palette and semantic tokens, WCAG 2.1 AA contrast, UI copy from dictionaries, server vs client components, forms, tables and icons. Use when building, changing or reviewing UI code (a page, layout, component, form, table, colour, UI copy or icon) or the global stylesheet."
metadata:
  author: Tarık Eren Tosun
---

# Frontend

Conventions for UI code in a Next.js App Router project that uses HeroUI v3,
Tailwind CSS v4 and a brand palette in its global stylesheet.

UI code must be **type-safe, secure and modular**. These three rank above
speed, brevity and cleverness. When a task cannot be done without giving up one
of them, stop and say so instead of shipping the compromise.

The project's own conventions add the specifics this skill leaves open: where
the dictionaries live, which files to copy from, and any exceptions. This
skill outranks them, as every `sds-*` skill does, and **every other `sds-*`
skill outranks this one**: it is how a Next.js app carries them out, never the
source of their rules.

Paths such as `sds-logging/references/log-record.md` name a file in another
skill of this plugin, relative to the plugin's skills directory: the parent
of `${CLAUDE_SKILL_DIR}`, which is this skill's own directory.

## Read first

1. **The Next.js docs for the installed version**, not memory. Under
   `node_modules/next/dist/docs/01-app/`:
   - `01-getting-started/`: chiefly `03-layouts-and-pages`,
     `04-linking-and-navigating`, `05-server-and-client-components`,
     `07-mutating-data`, `10-error-handling` and `11-css`;
   - `02-guides/`: `data-security` and `server-and-client-boundary`.
2. **The HeroUI v3 docs for every component you use**, before writing it,
   through the `heroui-react` skill's scripts, wherever the project keeps it:

   ```bash
   node .claude/skills/heroui-react/scripts/get_component_docs.mjs Select ListBox
   ```

   `list_components.mjs` in the same folder gives the names. The scripts
   fetch from HeroUI's servers. Where the network refuses them, as the egress
   allowlist in `sds-ci/SKILL.md` does in an AI task sandbox, work from the
   installed package's types and the reference page, and say so in the
   report.
3. **[`references/ui-reference.html`](references/ui-reference.html).** Open it
   in a browser with `?app=` and the URL of the app's root, e.g.
   `ui-reference.html?app=file:///home/me/my-app/`. It reads the app's
   `app/globals.css` and HeroUI's installed CSS from there, and shows:
   - the palette,
   - every semantic token and its utility,
   - a live contrast table for light, dark and a scoped region,
   - each component rendered by HeroUI next to the JSX that produces it,
   - the patterns and traps below as code.

   As an agent, read the file for its snippets: the `<pre>` blocks are the
   JSX, and the `PAIRS` list in its script is the set of pairs to check.

## 1. Type safety

- **No `any`**, explicit or implicit. Use `unknown` and narrow it.
- **No assertions that silence the compiler.** No `as T` on data, never
  `as unknown as T`, and no `!` unless the line above proves the invariant.
  `as const` and `satisfies` are fine.
- **No `@ts-ignore`, `@ts-expect-error` or `eslint-disable`** in application
  code.
- **Every component has explicit prop types.**
  - Use `import type` for type-only imports.
  - Use literal unions instead of enums.
  - Model variants and results as discriminated unions, closed with an
    exhaustive `never` check.
- **Keep props narrow.** A client component's props name the fields it
  renders, not a whole domain type. A narrow type is also the security
  boundary in § 2.
- **Outside data is `unknown` until narrowed:** `params`, `searchParams`, form
  input, `fetch` results, `localStorage`, `postMessage`. Parse it with the
  project's schemas instead of casting it.
- **Derive types from their source** (`z.infer<typeof Schema>`,
  `Awaited<ReturnType<typeof service.fn>>`) instead of re-declaring shapes by
  hand, so a change on the server breaks the build instead of the page.
- **Type pages and layouts** with the generated `PageProps<"/route">` and
  `LayoutProps<"/route">`, and await `params` and `searchParams` (§ 7).

## 2. Security

### The server/client boundary is a trust boundary

- **Everything passed to a client component is serialised into the page**,
  where anyone can read it: its props, and the return values of the server
  actions it calls. Pass only the fields the component renders. Never pass
  whole records, tokens, hashes, or fields this user may not see.
- **Client components run under browser rules**, even when they are
  prerendered on the server. They must not import server-only modules or read
  privileged data. Mark every module that touches secrets, the database or
  `next/headers` with `import "server-only"`, so a client import fails the
  build.
- **Secrets never reach the browser** (`sds-config/SKILL.md`). Only `NEXT_PUBLIC_*` variables do.
  Next.js inlines them into the JavaScript bundle at build time, so nothing
  secret belongs in them.

### Rendering untrusted content

- **No `dangerouslySetInnerHTML`.** If a task seems to need it, stop and
  report.
- **No `eval`, `new Function` or string-built scripts.**
- **Check user-supplied URLs** before putting them in `href` or `src`: allow
  only `http:`, `https:` or relative URLs, never `javascript:` or `data:`.
- **`target="_blank"` gets `rel="noopener noreferrer"`.**

### Authorisation lives on the server

- **Hiding a control is not authorisation.** The server enforces permissions,
  and the UI only reflects them.
- **Page-level checks do not protect actions.** A server action is a public
  POST endpoint, whether or not the page renders its form.
- **Server actions and route handlers are backend code.** They follow
  `sds-nextjs-backend`: authentication, authorisation for the specific record,
  validation and DTO returns. UI code only calls them.
- **No mutation during render.** A page never sets cookies, writes data or
  revalidates while rendering. Mutations go through server actions.

### Data in the browser

- **Keep personal data out of URLs and query strings**, which are logged and
  shared, and out of `console` output. Leave no `console.log` behind.
- **Never store tokens or personal data in `localStorage` or
  `sessionStorage`.** Keep browser storage for preferences.
- **Do not add a package** where the platform, HeroUI or an existing
  dependency does the job. A new dependency is a decision to report, not a
  default.

## 3. Modularity

- **One component, one job.** Split a file that mixes data loading, state and
  presentation.
- **Server components load data; client components hold interaction** (§ 7).
- **Colocate a route's private components** in its `_components/` folder. When
  a second route needs one, move it to the project's shared components folder
  instead of importing it across routes.
- **No business rules in components.** Allowed transitions, validation and
  permissions come from the server; components format and display them.
- **Reuse before you write.** Search for an existing component, formatter or
  hook first, and never duplicate a helper.
- **No module-level mutable state and no `globalThis` properties.** State lives
  in React or on the server.
- **Keep exports small:** export what other modules use, nothing else.

## 4. Colour

### The palette is the only source of colour

The global stylesheet (`app/globals.css`) defines two Fluent-style ramps as CSS
variables and registers them as Tailwind utilities through `@theme`:

- **Brand**, dark → light: `theme-darker`, `theme-dark`, `theme-dark-alt`,
  `theme-primary`, `theme-secondary`, `theme-tertiary`, `theme-light`,
  `theme-lighter`, `theme-lighter-alt` (`bg-theme-primary`, …)
- **Neutral**: `black`, `neutral-dark`, `neutral-primary`, `neutral-primary-alt`,
  `neutral-secondary`, `neutral-tertiary`, `neutral-tertiary-alt`,
  `neutral-quaternary-alt`, `neutral-light`, `neutral-lighter`,
  `neutral-lighter-alt`, `white`. A project may add the other Fluent slots
  (`neutral-secondary-alt`, `neutral-quaternary`); the reference page marks the
  ones that are missing.

**Never introduce a new hex, `oklch()` or named colour.** That covers every
route a colour can take into the code:

- a literal anywhere: `#…`, `rgb()`, `hsl()` or `oklch()` in CSS, in
  `style={{…}}`, in an SVG `fill` or `stroke`, or in an arbitrary value
  (`bg-[#3a7f62]`);
- CSS named colours (`red`, `gray`);
- **Tailwind's built-in palette** (`text-red-600`, `bg-gray-100`). It still
  compiles, which is what makes it a trap.

**The `neutral` trap.** Tailwind's own `neutral-50` … `neutral-950` share the
prefix and compile without complaint. The palette's neutrals are *named*
(`neutral-light`, `neutral-secondary`). `bg-neutral-100` is a new colour;
`bg-neutral-lighter` is the palette.

### Style against semantic tokens first

HeroUI colours its components through semantic tokens, and the global
stylesheet maps each token onto a palette slot. Your own markup should use the
same tokens:

| Token | Utility | For |
|---|---|---|
| `--background` / `--foreground` | `bg-background`, `text-foreground` | The page |
| `--surface` (`-secondary`, `-tertiary`) + `-foreground` | `bg-surface`, `text-surface-foreground` | Cards, panels, tables |
| `--overlay` | `bg-overlay` | Popovers, menus, modals |
| `--muted` | `text-muted` | Secondary text: hints, metadata |
| `--default` / `--default-foreground` | `bg-default` | Neutral control fill |
| `--accent` / `--accent-foreground` | `bg-accent`, `text-accent-foreground` | Primary action, selection. Prefer `variant="primary"` / `color="accent"` |
| `--focus` | `ring-focus` | Focus rings. Never remove an outline |
| `--link` | `text-link` | Links |
| `--field-background`, `--field-foreground`, `--field-placeholder`, `--field-border` (drawn at `--field-border-width`, `0px` by default) | `bg-field`, `text-field-foreground`, `border-field-border` | Form fields and field-like containers |
| `--border`, `--separator` | `border-border`, `border-separator` | Lines |
| `--success`, `--warning`, `--danger` | through `color` / `status` props | Status |

**The utility name comes from HeroUI's registration, not from the token.** A
token has a utility only if HeroUI registers it as `--color-*` in
`node_modules/@heroui/styles/dist/themes/shared/theme.css`. A class that names
anything else generates no CSS and gives no warning. `bg-field-background` is
such a class; the utility is `bg-field`.

Use a ramp utility (`bg-theme-lighter`) only when no token names the role.
Tokens are re-pointed by scoped classes and by the dark theme; a ramp utility is
not, so it is the colour that breaks when the region around it is re-themed.

### Status colours

| Meaning | `color` / `status` |
|---|---|
| Overdue, due soon, demo data | `warning` |
| Rejected, failed, invalid | `danger` |
| Done, approved, complete | `success` |
| In progress, informational, selected | `accent` |
| No state | `default` |

When the brand palette has no amber or red, `warning` and `danger` keep
**HeroUI's own** hues. Do not re-point them to the brand colour.

### Re-theming a region

Redefine tokens in a scoped class in the global stylesheet (a dark sidebar,
say) and put the class on the region's root. Never override component internals
class by class. The dark theme is the same idea on `[data-theme="dark"]`.

**A scoped class must also redeclare the derived tokens it relies on.** HeroUI
derives `--accent-hover`, the `-soft` fills and the `-soft-foreground` text with
`color-mix()` on `:root`. A custom property resolves `var()` where it is
declared, and descendants inherit the result, so inside the region those tokens
still hold the *root's* colours. A region that sets a light `--accent` with dark
text but leaves `--accent-hover` alone gets a hover state computed from the
page's accent. The reference page's contrast table measures the region the way
the browser draws it.

### Contrast: WCAG 2.1 AA

AA requires **4.5:1** for text, and **3:1** for large text (24px, or 18.66px
bold) and for what identifies a control (1.4.11): a focus ring, or a field's
edge against its surroundings. WCAG does not round, so 4.49 fails.

- **Measure with the reference page.** It covers text on the page and on a
  surface, links, accent text, primary buttons and their hover, solid and soft
  status chips, error text, field text, placeholder, focus rings and field
  edges, in light, dark and the scoped region.
- **Check what HeroUI derives, not only what you set.** The hover, soft and
  soft-foreground tokens are mixes. They can fail when every palette pair you
  chose passes.
- **Common failures with a Fluent-style ramp:**
  - accent-coloured text on a tinted page background, when it passes on white;
  - `neutral-tertiary` as placeholder or muted text;
  - white text on the mid-ramp slots;
  - a hover that mixes the accent towards white;
  - a white field on a white surface, which leaves the field with no visible
    edge (1:1).
- **A field's border needs a width as well as a colour.** HeroUI makes
  `--field-border` transparent and sets `--field-border-width: 0px`, so a
  border colour alone draws nothing. To give fields a visible edge, set both
  (for example `--field-border: var(--neutral-secondary)` and
  `--field-border-width: 1px`), or give the field a fill that stands out from
  the surface. The reference page counts a border only when it is drawn.
- **Put accent-coloured text on a surface**, not directly on the page
  background, unless the page's pair passes.
- **A placeholder is not a label.** Anything the user needs goes in `<Label>`
  or `<Description>`.
- **Before shipping a pairing the table does not cover,** compute
  `(L1 + 0.05) / (L2 + 0.05)` from relative luminance, and add the pair to the
  page's `PAIRS` list.

### Radius

HeroUI scales every radius step from `--radius`. Set the policy once in the
global stylesheet, never with `rounded-*` on one component. `rounded-full` is
outside the scale, so Avatar and Badge stay round.

## 5. Components: HeroUI v3 only

- **Use `@heroui/react`**, adjusted with `className`, Tailwind and the tokens.
- **Do not write custom UI components** unless HeroUI has no equivalent, and
  then say why in the file's header comment.
  - *Composing* HeroUI parts into a domain piece is fine: an `Alert` with fixed
    text, or a `Table` wrapper a server component can call. Say in the header
    that it is a composition.
  - *Re-implementing* a primitive is not: a clickable `<div>`, a hand-made
    dropdown, modal or tab strip, or a styled bare `<button>`, `<input>` or
    `<table>`. A tree view, which HeroUI lacks, is the kind of exception that
    needs the header comment.
- **v3 is compound**: `<Card><Card.Header><Card.Title>`, not flat props. There
  is no `HeroUIProvider` and no `framer-motion`. The only provider is the
  project's own locale provider, such as an `I18nProvider`, set once at the
  root with the request's locale: it gives client components their dictionary
  and HeroUI's own `I18nProvider` the same locale, so server and client format
  numbers and dates alike and hydrate without a mismatch.
- **`onPress`, not `onClick`.**
- **Every interactive component needs an accessible name.**
  - Pass `aria-label` where there is no visible `<Label>`: `SearchField`,
    `Meter`, `ProgressBar`, an icon-only `Button`, `Table.Content`, `ListBox`,
    `ToggleButtonGroup`.
  - The name is copy, so it comes from the dictionary.
  - When a control repeats per row, put the record in its name.
  - React Aria warns in the browser console when a name is missing.
- **`Button` has no `href`**: it is React Aria's button. To navigate:
  - in a server component, use a GET `<form>` around a `type="submit"` Button;
  - in a client component, call `router.push` in `onPress`;
  - for a whole table row, set `href` on `Table.Row`.

  Never copy button classes onto an `<a>` by hand.
- **Icons are inline SVG** unless the project names an icon package. Give the
  SVG `aria-hidden="true"`, colour it with `currentColor` so the token decides,
  and put the accessible name on the control around it.

## 6. Copy and language

- **No inline copy.** Everything a user reads comes from the project's
  dictionaries (the project says where): headings, labels, buttons,
  placeholders, `aria-label`s, empty states, error text and the page title. When
  the dictionaries are typed against a source language, a missing key fails the
  build, so add every key to every language in the same change.
- **Read copy on the side it renders.** A server component reads the request's
  dictionary on the server. A client component reads it from context. Never
  pick a language in the browser, and never import a server-only module (one
  that reads `next/headers`) into a client component.
- **Placeholders and plurals** go through the project's formatter. Do not
  concatenate strings.
- **Values from a code-defined set** (statuses, types) get a dictionary map keyed
  by the code. **Errors are translated by their code**, and the code is shown
  next to the sentence.
- **Dates, times, numbers and sizes** go through the project's formatters, with
  the locale. Never call `toLocaleDateString` in a component. Numeric table
  columns get `tabular-nums`.
- **Record content is data, not copy.** Names stored in the database, seed and
  mock records, and record codes stay out of the dictionaries.
- **Tests read labels from the dictionaries** (`sds-testing/SKILL.md`, **Writing tests**), never from string literals, so a
  copy change touches only the dictionary.

## 7. Server and client components

- **Server components by default.** Add `"use client"` only for state,
  effects, event handlers, browser APIs or `useActionState`, and push it down
  to the smallest component that needs it.
- **Pages call the service layer directly.** A server component never fetches
  the app's own API routes.
- **`params` and `searchParams` are Promises**, so await them. Type pages and
  layouts with the generated globals `PageProps<"/route">` and
  `LayoutProps<"/route">`, which need no import.
- **Validate URL input.** Every `[param]` folder and every query string is user
  input. Narrow `searchParams` values (`typeof q === "string"`). An id that does
  not parse, or a record that does not exist, calls `notFound()` rather than
  throwing into the error boundary.
- **Keep filters and selection in the URL** (a GET form, `?folder=`), not in
  client state, so a link opens the same view.
- **Functions cannot cross the server/client boundary.** That rules out render
  props, `renderEmptyState` and handlers passed from a server component.
  HeroUI's `Table` builds its collection from its children, so a table rendered
  from a server component goes through a small client wrapper that takes column
  and row *data*. The pattern is in the reference page.
- **Mutations are server actions**, each a thin shell over a service, written
  to `sds-nextjs-backend`. The UI receives the envelope `sds-api-design`
  requires of every API (`{ status: "ok", … } | { status: "fail", code,
  message, details }`) and renders it.

### Forms

The full snippet is in the reference page. Each rule below prevents a specific
bug:

1. Hold the result in `useActionState`, with a reducer that wraps the action.
2. **Use HeroUI's `<Form validationBehavior="aria">`, not a bare `<form>`.**
   The default, `native`, hands validation to the browser, and the browser
   then blocks submits on its own:
   - `isRequired` becomes the `required` attribute, so an empty field is
     refused and no error is shown.
   - A field marked invalid gets a custom validity, so once the server rejects
     it, the form cannot be submitted again until the page is reloaded.

   With `aria`, `isRequired` still marks the field (`aria-required`, the
   asterisk), and every submit reaches the server.
3. **Submit through `onSubmit`**: `preventDefault()`, take the `FormData`,
   then `startTransition(() => submit(formData))`. Do not use
   `<form action={fn}>`: React 19 resets uncontrolled fields *before* the
   action runs, so a rejected submission wipes what the user typed. Outside a
   transition, `pending` never turns true.
4. **Show server errors through `validationErrors`.**
   - Key the result's `details` entries by `field`, and pass them to
     `<Form validationErrors={…}>`, and give each field an empty
     `<FieldError />`. Each error appears under its field and clears when the
     user edits that field.
   - Do not drive `isInvalid` from server errors. A controlled `isInvalid`
     stays set until the next result arrives, and under native validation it
     blocks that result.
   - A value React Aria does not own, such as a hidden input a custom picker
     fills, reads its error from the result itself.
5. **Do not re-validate on the client.** No `validate` functions and no
   client-side schema: the server validates, and two sets of rules drift apart.
6. **Reset after success by changing a `key`** that comes from the action
   state (a success counter). `form.reset()` misses state held inside child
   components.
7. **Files never pass through a server action**, which has a 1 MiB body limit.
   Upload them to a route handler first, and put only the handle in the form.
8. Disable the submit `Button` while `pending` and show a "saving" label.
   Cancel is navigation, not a submit.
9. **Tests click the submit `Button`**, per **Writing tests** in
   `sds-testing/SKILL.md`.
10. **Announce the result.** HeroUI's `Alert` renders a plain `div` with no
    role, so a screen reader hears nothing (WCAG 2.1, 4.1.3).
    - **A rejection:** `<Alert status="danger" role="alert">`, which is read
      at once.
    - **A success that stays on the page:** `role="status"`, which waits its
      turn. Render its container always and change only its content: some
      screen readers announce a status region only if it exists before its
      text does.
11. **Put focus where the user acts next**, once per result. The reference
    page's form pattern has the effect that does it.
    - **The server rejects fields:** focus the first invalid field. Its error
      is its description, so the label and the error are read together.
    - **The server rejects the whole submit:** focus the submit `Button`
      again, since disabling it while pending can drop focus. Scroll the
      `Alert` into view.
    - **A success that resets the form** (rule 6): focus the first field of
      the fresh form. The remount would otherwise drop focus to the page.
    - **A success that navigates:** leave focus to the new page. Next.js
      announces the new page's title.

## 8. Page structure

- **Skeleton:** `Breadcrumbs`, then a `Typography type="h2"` title with a
  muted `body-sm` summary, actions on the right
  (`flex flex-wrap items-end justify-between gap-4`), then the content. Space
  sections with `flex flex-col gap-6`.
- **Empty state:** `Card variant="transparent"` holding muted `Typography`.
- **Wide content never scrolls the page sideways.** Give the flex or grid
  column `min-w-0`, and give `Table.Content` a `min-w-[…]` inside
  `Table.ScrollContainer`. Check every screen at phone width.
- **A screen on mock or sample data says so**, with a `warning` Alert.
- **Separate surfaces get separate layouts.** An admin surface does not
  inherit the user application's menu, notifications or search. Use route
  groups for this.

## 9. Comments and naming

- **Every page and component gets a header comment:** what it is, what it
  implements (the requirement, spec section or decision, cited the way the
  project cites them), and the reason for any choice a reviewer would question.
- **Identifiers and codes come from the backend.** Display a record code as the
  service returns it; never build one in the UI.
- **Comments follow the language of the file you are editing.**

## Skeleton

In the stage loop of `sds-planning/SKILL.md`, the stage plan's skeleton task
builds the contract's surface before any behaviour, so that the tester can
write tests that compile and fail for the right reason. A UI skeleton holds:

- **the pages** at their final paths, rendering a stub;
- **the components** the contract names, at their final module paths and
  export names, with their final prop types, rendering a stub: `null`, or a
  placeholder with none of the contract's accessible names, so that a test
  looking for one fails with "element not found";
- **the dictionary keys** the contract names, in every language, with their
  final copy, because the tests take their labels from the dictionaries.

No behaviour, and no guessing: every name, prop and key is the contract's. A
difference is a change to the contract, and goes back to whoever runs the loop.

## 10. Before handing back

Run the checks the project lists. At least:

```bash
pnpm run typecheck
```

```bash
pnpm run lint
```

```bash
pnpm run build
```

Also run the component tests that cover the change, through the project's
results-only interface.
Add tests for new client behaviour, reading labels from the dictionaries: in
the test-first loop these are your own tests, beside the code
(e.g. `app/**/*.test.tsx`), while the acceptance tests are the tester's and hidden
from you. How to write them is in [`../sds-testing/SKILL.md`](../sds-testing/SKILL.md).

Then review the diff against § 2:

- **`"use client"` files:** do their props accept more than they render, or
  anything private?
- **Server-only modules:** does every module that reads secrets, the database
  or `next/headers` import `"server-only"`?
- **Untrusted content:** are there any `dangerouslySetInnerHTML`, unchecked
  URLs, or new `NEXT_PUBLIC_*` variables?

Then check the change in the running app:

- It renders in **every language** the app supports.
- The browser console shows **no React Aria accessible-name warnings** and no
  hydration mismatch.
- The layout holds at **phone width** and on desktop.
- **A new colour pairing is measured**, in the reference page's contrast table.

Last, check the diff for colours that bypass the palette and for `onClick`:

```bash
git diff -U0 HEAD | grep -nE '^\+.*(#[0-9a-fA-F]{3,8}\b|oklch\(|rgba?\(|hsla?\(|-(red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|zinc|neutral|stone|mauve|olive|mist|taupe)-[0-9]{2,3}\b|onClick)'
```

Also check for any quoted sentence inside JSX, which belongs in the dictionary.
