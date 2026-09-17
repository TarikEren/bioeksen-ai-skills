# Service Calls

This document is the calling side. `standard-api-endpoints.md` says what an app
must serve; this says what it must do when it calls another app and that call
goes wrong.

The error codes `UP-5500`, `UP-5501` and `UP-5000` name the ways an outbound
call fails. Everything here is about what a caller does next.

The keywords MUST, SHOULD and MAY are used as in RFC 2119. Method semantics
follow RFC 9110.

## Call classes

A call with a person waiting and a call from a background job want opposite
policies, so the rules below are stated per class. Every outbound call belongs
to exactly one.

| Class | Meaning |
|-------|---------|
| **Request path** | Made while handling an inbound request. Someone is waiting |
| **Background** | Made by a job, a scheduler or a startup routine. Nobody is waiting |
| **Log emission** | Submission to the log aggregator. Governed by the emission rules in `sds-logging/references/log-record.md`, which override this document — logging MUST NOT block or fail the operation being logged |

## Deadlines

Every request carries the budget remaining for it, in whole milliseconds:

```
X-Request-Deadline-Ms: 2400
```

- A caller MUST send it on every outbound call, carrying what is left of its
  own budget after what it has already spent.
- A receiver MUST take the lesser of the received value and its own default,
  and MUST pass the remainder onward.
- When too little remains to finish the work, a receiver MUST fail immediately
  with `UP-5501` rather than begin work that cannot complete.
- A missing or malformed value means the caller has no budget to declare: the
  receiver uses its own default. Like `X-Request-Id`, the value is never
  trusted for anything but this.

The value is a **duration, not a timestamp**. An absolute deadline would need
clocks synchronised across the estate, which makes clock skew an availability
dependency. A duration needs no agreement about what time it is.

Without this, each hop times out independently: the caller gives up at its own
limit while services below it are still working, holding connections and
producing a result nobody will read — during exactly the incident when that
capacity is needed.

## Timeouts

| | Request path | Background |
|---|---|---|
| Connect | 500 ms | 500 ms |
| Per attempt | 1.2 s | 8 s |
| Attempts | 2 — one try, one retry | 3 |
| Total budget | 3 s | 30 s |

These compose rather than being chosen independently:

```
total budget  ≥  (attempts × per-attempt timeout) + (sum of backoff) + slack
3 s           ≥  2 × 1.2 s + 0.2 s + slack
```

Change one and the others move. A connect timeout MUST be shorter than the
per-attempt timeout it sits inside; on an internal network a connect slower
than 500 ms is a routing fault, not a slow server.

A caller's total budget MUST exceed its callee's. Otherwise the caller abandons
a request the callee is still serving, and the work is completed but
unattributable.

## What may be retried

The existing code numbering already answers this. The `5500` split separates
*a dependency is unavailable* from *something is broken*, which is the retry
question:

| Code range | HTTP | Retry |
|------------|------|-------|
| `5500-5999` | 503 | Yes |
| `5000-5499` | 500 | No |

- A connection failure or a timeout with no response is retryable, on the same
  terms as a 503.
- `RATE-4400` (429) is retryable, but only after the interval in `Retry-After`,
  which overrides the backoff below. The callee knows more about its own
  recovery than the caller does.
- Every other 4xx MUST NOT be retried. It is the caller's fault and will fail
  identically every time.

A `5000-5499` response means an unhandled path or a broken invariant. Retrying
buys a slower failure and three times the load.

### The exception that matters

`UP-5501` — the call timed out — means the outcome is **unknown**, not that
nothing happened. The request may have been received and completed, with only
the response lost.

So a timed-out call is retryable only when repeating it is safe: a method RFC
9110 defines as idempotent, or a request carrying an `Idempotency-Key`. A
timed-out `POST` without a key MUST NOT be retried. That single rule is why the
idempotency section below exists.

## How to retry

- Wait before each retry: **200 ms base, doubling, with full jitter, capped at
  5 s.** Full jitter means the actual wait is a random value between zero and
  the computed delay.
- Jitter is not a refinement. Without it, every client of a dependency that has
  just recovered retries in the same instant and knocks it over again.
- A retry MUST fit in the remaining deadline. If it does not, do not attempt it.

### Retry budget

Attempts MUST be capped as a **ratio**, not only as a count: at most **10% of
the successful requests** a caller has made to that target over the last 60
seconds, plus a free allowance of **3 retries** so a low-traffic caller can
retry at all.

A per-request count multiplies down a call tree. If A retries three times and
each attempt makes B retry three times, C sees nine requests — a struggling
dependency receives an order of magnitude more load precisely when it is
failing. A ratio is effectively unlimited while things are healthy and near
zero during an outage, which is the behaviour wanted in both cases.

The free allowance matters in practice: 10% of five requests a minute is no
retries at all, which would make the policy strictest for the callers least
able to cause harm.

## Circuit breaker

Retries alone make an outage worse. A caller MUST keep a breaker per target
service.

| State | Behaviour |
|-------|-----------|
| **Closed** | Calls proceed. Consecutive retryable failures are counted |
| **Open** | Calls fail immediately with `UP-5500`, without a network attempt. After the cooldown, move to half-open |
| **Half-open** | One trial call is allowed at a time. Success closes the breaker and resets the count; failure re-opens it |

Starting values:

| Parameter | Value |
|-----------|-------|
| Trip threshold | 5 consecutive retryable failures |
| Cooldown | 30 s, doubling on each re-open, capped at 5 minutes |
| Half-open trials | 1 concurrent |

Only the retryable conditions above count toward the threshold. A 4xx MUST NOT
trip a breaker: a caller sending malformed requests would otherwise cut itself
off from a service that is working perfectly.

Every state transition MUST be logged. `sds-logging/SKILL.md` already requires
dependency status transitions to be logged, and this is one — the record
carries `UP-5500` on opening, and no code on closing.

Failing fast while a dependency is down is not a degradation. It returns the
caller's budget immediately instead of spending it on a call already known to
fail, and it removes the retry load that would otherwise keep the dependency
down.

## Idempotency

RFC 9110 defines `GET`, `HEAD`, `OPTIONS`, `TRACE`, `PUT` and `DELETE` as
idempotent: repeating one has the same effect on server state as making it
once. Those may be retried on the terms above without anything further.

`POST` is not idempotent, and RFC 9110 says a client must not automatically
retry a non-idempotent request unless it has some way to know the semantics are
idempotent anyway, or to detect that the original was never applied. The
`Idempotency-Key` header is how a caller obtains that knowledge here.

```
Idempotency-Key: 8f14e45fceea167a5a36dedd4bea2543
```

Note that the header is **not** part of RFC 9110. It is a widely implemented
convention, currently an IETF draft. RFC 9110 supplies the method semantics and
the rule about retrying; the header is this document's addition on top.

### Rules

- A caller that may retry a state-changing `POST` MUST send the key, and MUST
  send the **same** value on every attempt of one logical request. A fresh key
  per attempt defeats the entire mechanism.
- An app serving a state-changing `POST` MUST honour the key.
- The value is opaque: `[A-Za-z0-9_-]`, 1 to 128 characters, caller-generated,
  and SHOULD carry at least 64 bits of entropy — the same format as
  `X-Request-Id`, and for the same reason.
- A key is scoped to the authenticated principal, the method and the path. Two
  apps sending the same key MUST NOT see each other's results, which is a
  security property, not a tidiness one.
- Keys are retained for **24 hours**. The retention MUST exceed the longest
  retry budget; 24 hours also covers a retry a person makes by hand.

### Server behaviour

| Situation | Response |
|-----------|----------|
| Key not seen before | Process normally. Store the status and body before responding |
| Same key, same request, original completed | Return the stored status and body |
| Same key, same request, original still in flight | Wait, bounded by the remaining deadline, then return the stored response. If the deadline expires first, 409 `RES-4301` |
| **Same key, different request** | **409 `RES-4301`**, immediately |

**A key replayed with a different body yields `RES-4301`.** Stated flatly here
because it is the case most likely to be got wrong, and because the temptation
is to invent a code for it. The registry is closed: a key already spent on a
different change is a conflict with current state, which is what `RES-4301`
means. `RES-4300` is for a resource that already exists, which is a different
statement about a different thing.

Both 409 conditions carry `RES-4301` and are not distinguishable by a caller
from the response alone. Neither is usefully retryable — one is a caller bug,
the other means the budget is already gone — so nothing depends on telling them
apart in code. An operator can, from the log record.

A replayed response MUST echo the **current** request's `X-Request-Id`, not the
one stored with the original. Replaying the stored value would file the retry
under the trace of the first attempt, hiding the retry from the very tooling
meant to show it.

A `SHOULD`-strength marker on a replay is useful when reading traffic:

```
Idempotency-Replayed: true
```

## Interaction with credentials

An app MUST refresh its own credential at **75% of the token's lifetime**, read
from `exp` — never from an assumed duration, per
`sds-auth/references/credentials.md`.

75% is chosen so that the remaining quarter comfortably exceeds the background
retry budget above. A refresh that begins at expiry has no room to retry, and
`sds-auth` requires refreshing before expiry rather than discovering it through
a 401.

## Where these numbers come from

No BioEksen service is in production, so nothing here was measured. That is
worth stating rather than disguising, because it determines which of these
values a reader may change.

### Three kinds of rule

| Kind | Changeable? | Examples |
|------|-------------|----------|
| **Structural** | No. They follow from arithmetic or from protocol semantics, and hold at any traffic level | A caller's budget exceeds its callee's; retry budget is a ratio; backoff carries jitter; a timed-out `POST` without a key is not retried |
| **Agreed** | Only here, for the whole estate at once. The value is arbitrary; the agreement is the point | Header names, key format, key retention |
| **Empirical** | Yes, per app, with the rule below | Every timeout, attempt count, threshold and cooldown |

The distinction is the anchor. Without it, someone tuning a timeout eventually
tunes the jitter away, because both look like numbers.

### Overriding an empirical value

- An app MAY override any empirical value.
- It MUST record the override and the reason where its configuration lives.
- A **silent** override is the failure mode this rule exists to prevent. A
  timeout that differs from the estate's without explanation is
  indistinguishable from a mistake, and the next person to read it will restore
  the default and cause an incident.
- Changing a default for everyone is a change to this document, in one commit.

### Replacing the guesses with measurements

Once a service has 30 days of production data, set its per-attempt timeout
from the observed latency of the call rather than from this table:

```
per-attempt timeout  ≈  p99.9 latency × 1.5      (minimum: p99 × 2)
```

Then recompute the total budget from the composition formula above; do not
change one without the other.

### What would show these numbers are wrong

Each value has an observable that contradicts it, and every one of them is
already visible through the error codes and the aggregator — no new
instrumentation is needed to find out.

| Symptom | Likely cause |
|---------|--------------|
| `UP-5501` rate rises while the callee logs no errors | Per-attempt timeout too low |
| Request latency piles up at the total budget | Timeout too high; calls that should fail fast do not |
| `UP-5500` spikes without a real outage | Breaker threshold too low, or a 4xx is wrongly counted as a failure |
| Transient failures reach users | Retry budget too tight, or the free allowance too small |
| Retries arrive in bursts after a recovery | Jitter is missing or partial |
| `RES-4301` from a caller's own retries | The caller is minting a new key per attempt |

Treat a number that survives contact with one of these as confirmed, and record
that it was confirmed. The reason these are guesses today is that nothing has
run; the reason they would still be guesses in a year is nobody looking.
