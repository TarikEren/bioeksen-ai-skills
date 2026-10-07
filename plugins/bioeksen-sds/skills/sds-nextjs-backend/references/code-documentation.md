# Code Documentation Reference

> **Load when:** writing or reviewing comments, module headers or doc comments
> in server code.

Comments exist for the reader who has the code but not the context: a
reviewer, an auditor, or you in six months. They say what the code cannot
say about itself.

## Contents

- [Module header](#module-header)
- [Doc comments on exported functions](#doc-comments-on-exported-functions)
- [Inline comments](#inline-comments)
- [What not to write](#what-not-to-write)

---

## Module header

Every module starts with a block comment that answers three questions:

1. **What is this module?** One sentence.
2. **What does it implement?** The requirement, spec section or decision, cited
   the way the project cites them (an ID such as `REQ-2.1.3`, a document and
   section, an ADR). This is how a change is traced back to why it exists.
3. **Which choices would a reviewer question?** The non-obvious ones, with the
   reason.

```typescript
/**
 * Document lifecycle transitions (REQ-2.1.2).
 *
 * The transition table lives here, not in the route handler or the form, so
 * that every entry point (API, server action, job) applies the same rules.
 *
 * The status is read inside the transaction that writes the new one. Reading
 * it first and writing later lets two approvals race past the check.
 */
import "server-only";
```

Keep the header true. When the code changes, the header changes in the same
commit.

---

## Doc comments on exported functions

The exported functions of a service or repository are the module's contract.
Document what a caller cannot see from the signature:

- what the function guarantees (atomicity, idempotency, ordering);
- **which errors it throws**, by code, and when;
- the authorisation it performs, or expects the caller to have performed;
- units, time zones and ranges that the types do not carry.

```typescript
/**
 * Publishes a revision and opens its read assignments, in one transaction.
 *
 * Authorises `actor` against the document's ACL before reading anything.
 *
 * @throws AppError `PERM-4150` when the actor may not publish this document.
 * @throws AppError `RES-4200` when the document or revision does not exist.
 * @throws AppError `RES-4301` when another publish won the race.
 * (The codes are the registry's, in sds-logging's code-prefixes.md.)
 */
export async function publish(
  actor: Actor,
  documentId: bigint,
  revisionNo: number,
): Promise<PublishedRevisionDto> {
  // …
}
```

Do not repeat the parameter types in prose. `@param` is worth writing only
when the name and type leave something out (a unit, a format, a range).

---

## Inline comments

Write one where the code is correct but looks wrong, or where the obvious
alternative was tried and failed:

```typescript
// Count in the database, not with findMany().length: a folder can hold tens of
// thousands of rows, and the count query uses the (folder_id, status) index.
const total = await db.document.count({ where: { folderId, status } });
```

- **Explain why, not what.** The code already says what.
- **Name the constraint:** the bug it prevents, the limit it respects, the
  standard it follows.
- **Match the language of the file.** Do not mix languages within one module.

---

## What not to write

| Don't | Because |
|---|---|
| `// increment i` | Restates the code |
| `// TODO: fix later` without an owner or ticket | Never gets fixed |
| Commented-out code | Version control keeps history |
| A comment that disagrees with the code | Worse than none; fix one of them |
| Change history (`// changed by X on …`) | That is the commit log |
| Secrets, internal hostnames or personal data in examples | Comments ship with the code |
