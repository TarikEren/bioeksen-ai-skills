# Typescript Reference

Build enterprise-grade, type-safe applications with TypeScript 5.9+.

> **Compatibility:** TypeScript 5.9+, Zod 4, Node.js 22 LTS or later

## When to Use This Skill

Use when:
- Designing and creating an enterprise-grade backend using Typescript
- Implementing advanced type patterns (generics, mapped types, conditional types)
- Configuring modern TypeScript toolchains
- Designing type-safe API contracts with Zod validation
- Comparing TypeScript approaches with Java or Python

## Type System Quick Reference

### Primitive Types

```typescript
const name: string = "Alice";
const age: number = 30;
const active: boolean = true;
const id: bigint = 9007199254740991n;
const key: symbol = Symbol("unique");
```

### Union and Intersection Types

```typescript
// Union: value can be one of several types
type Status = "pending" | "approved" | "rejected";

// Intersection: value must satisfy all types
type Employee = Person & { employeeId: string };

// Discriminated union for type-safe handling
type Result<T> =
  | { success: true; data: T }
  | { success: false; error: string };

function handleResult<T>(result: Result<T>): T | null {
  if (result.success) {
    return result.data; // TypeScript knows data exists here
  }
  console.error(result.error);
  return null;
}
```

### Type Guards

```typescript
// typeof guard
function process(value: string | number): string {
  if (typeof value === "string") {
    return value.toUpperCase();
  }
  return value.toFixed(2);
}

// Custom type guard
interface User { type: "user"; name: string }
interface Admin { type: "admin"; permissions: string[] }

function isAdmin(person: User | Admin): person is Admin {
  return person.type === "admin";
}
```

### The `satisfies` Operator (TS 5.0+)

Validate type conformance while preserving inference:

```typescript
// Problem: Type assertion loses specific type info
const colors1 = {
  red: "#ff0000",
  green: "#00ff00"
} as Record<string, string>;

colors1.red.toUpperCase(); // OK, but red could be undefined

// Solution: satisfies preserves literal types
const colors2 = {
  red: "#ff0000",
  green: "#00ff00"
} satisfies Record<string, string>;

colors2.red.toUpperCase(); // OK, and TypeScript knows red exists
```

## Generics Patterns

### Basic Generic Function

```typescript
function first<T>(items: T[]): T | undefined {
  return items[0];
}

const num = first([1, 2, 3]);     // number | undefined
const str = first(["a", "b"]);   // string | undefined
```

### Constrained Generics

```typescript
interface HasLength {
  length: number;
}

function logLength<T extends HasLength>(item: T): T {
  console.log(item.length);
  return item;
}

logLength("hello");     // OK: string has length
logLength([1, 2, 3]);   // OK: array has length
logLength(42);          // Error: number has no length
```

### Generic API Response Wrapper

```typescript
import { z } from "zod";

interface ApiResponse<T> {
  data: T;
  status: number;
  timestamp: Date;
}

// `response.json()` is untyped. Parse it with the schema of what you expect,
// so a changed or hostile upstream fails here instead of deep in the caller.
async function fetchJson<S extends z.ZodType>(
  url: string,
  schema: S,
): Promise<ApiResponse<z.infer<S>>> {
  const response = await fetch(url, { signal: AbortSignal.timeout(5_000) });
  const data = schema.parse(await response.json());
  return { data, status: response.status, timestamp: new Date() };
}

const user = await fetchJson(`https://users.internal/api/users/${id}`, UserSchema);
```

## Utility Types Reference

| Type | Purpose | Example |
|------|---------|---------|
| `Partial<T>` | All properties optional | `Partial<User>` |
| `Required<T>` | All properties required | `Required<Config>` |
| `Pick<T, K>` | Select specific properties | `Pick<User, "id" \| "name">` |
| `Omit<T, K>` | Exclude specific properties | `Omit<User, "password">` |
| `Record<K, V>` | Object with typed keys/values | `Record<string, number>` |
| `ReturnType<F>` | Extract function return type | `ReturnType<typeof fn>` |
| `Parameters<F>` | Extract function parameters | `Parameters<typeof fn>` |
| `Awaited<T>` | Unwrap Promise type | `Awaited<Promise<User>>` |

## Conditional Types

```typescript
// Basic conditional type
type IsString<T> = T extends string ? true : false;

// Extract array element type
type ArrayElement<T> = T extends (infer E)[] ? E : never;

type Numbers = ArrayElement<number[]>; // number
type Strings = ArrayElement<string[]>; // string

// Practical: Extract Promise result type
type UnwrapPromise<T> = T extends Promise<infer R> ? R : T;
```

## Mapped Types

```typescript
// Make all properties readonly
type Immutable<T> = {
  readonly [K in keyof T]: T[K];
};

// Make all properties nullable
type Nullable<T> = {
  [K in keyof T]: T[K] | null;
};

// Create getter functions for each property
type Getters<T> = {
  [K in keyof T as `get${Capitalize<string & K>}`]: () => T[K];
};

interface Person { name: string; age: number }
type PersonGetters = Getters<Person>;
// { getName: () => string; getAge: () => number }
```

## Validation with Zod (v4)

```typescript
import { z } from "zod";

// Define the schema once; the type is derived from it, never written by hand.
// strictObject rejects unknown keys, which blocks mass assignment.
const CreateUserSchema = z.strictObject({
  name: z.string().trim().min(1).max(100),
  email: z.email(),                      // Zod 4: top-level format, not z.string().email()
  role: z.enum(["user", "admin", "moderator"]),
  startsOn: z.iso.date(),                // "2026-09-28"
});

type CreateUser = z.infer<typeof CreateUserSchema>;

// Values that arrive as strings (route params, FormData, query strings) are coerced
// explicitly. Use the key type the database defines; do not assume UUIDs.
const IdParam = z.coerce.bigint().positive();

// At a boundary: safeParse, then turn issues into field errors for the caller.
const result = CreateUserSchema.safeParse(input);
if (!result.success) {
  const { fieldErrors } = z.flattenError(result.error);
  // → { email?: string[]; role?: string[]; … }
  return { ok: false, code: "VALIDATION", fields: fieldErrors } as const;
}
const user: CreateUser = result.data; // typed from here on

// Inside trusted code, parse() throws a ZodError instead.
function parseCreateUser(data: unknown): CreateUser {
  return CreateUserSchema.parse(data);
}
```

Zod 4 notes: `z.string().email()`, `.uuid()` and `.url()` still work but are
deprecated in favour of `z.email()`, `z.uuid()` and `z.url()`. The error
methods `.format()` and `.flatten()` are deprecated in favour of
`z.treeifyError()` and `z.flattenError()`.

## Common Mistakes

| Mistake | Problem | Fix |
|---------|---------|-----|
| Using `any` liberally | Defeats type safety | Use `unknown` and narrow |
| Ignoring strict mode | Misses null/undefined bugs | Enable all strict options |
| Type assertions (`as`) | Can hide type errors | Use `satisfies` or guards |
| Enum for simple unions | Generates runtime code | Use literal unions instead |
| Not validating API data | Runtime type mismatches | Use Zod at boundaries |

## Cross-Language Comparison

| Feature | TypeScript | Java | Python |
|---------|------------|------|--------|
| Type System | Structural | Nominal | Gradual (duck typing) |
| Nullability | Explicit (`T \| null`) | `@Nullable` annotations | Optional via typing |
| Generics | Type-level, erased | Type-level, erased | Runtime via typing |
| Interfaces | Structural matching | Must implement | Protocol (3.8+) |
| Enums | Avoid (use unions) | First-class | Enum class |

