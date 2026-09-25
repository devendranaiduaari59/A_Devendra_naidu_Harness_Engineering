---
description: Review a PR, diff, or file for bugs, security, conventions, and breaking changes.
argument-hint: PR ref, diff range, or file path to review
allowed-tools:
  - Read
  - Glob
  - Grep
  - "Bash(git diff:*)"
  - "Bash(git log:*)"
  - "Bash(git show:*)"
  - "Bash(git status:*)"
  - "Bash(gh pr view:*)"
  - "Bash(gh pr diff:*)"
  - "Bash(gh pr checks:*)"
---

# /review — team PR review

You are reviewing the diff identified by `$ARGUMENTS` against this repository's conventions. Apply the path-scoped rules in `.claude/rules/` (they auto-load based on the files touched) and the shared standards in `.claude/standards/`.

## Phase 1 — Interview pattern

Before reporting findings, ask clarifying questions whenever the author's intent or expected behavior is ambiguous.

Interview the author before reporting findings when any of these conditions apply:

* Dependency changes are present in `package.json`, `package-lock.json`, `pyproject.toml`, `requirements.txt`, or another dependency manifest and the reason for the dependency change is unclear.
* A public API response shape, request contract, database column, schema, or migration behavior changes and compatibility expectations are unclear.
* A refactor changes implementation code without corresponding test changes and it is unclear whether existing tests already cover the affected behavior.
* The change touches multiple surfaces such as API, UI components, database models, and migrations at the same time and the intended end-to-end behavior is unclear.
* Authentication, authorization, payment, refund, or other sensitive behavior changes without a clearly documented intended behavior.

Do not ask unnecessary questions when the problem is unambiguous. If the code clearly violates a repository rule or contains an obvious defect, report the finding directly.

## Phase 2 — Review criteria

Report concrete and actionable findings supported by the diff, repository rules, or shared standards.

### Must report

Report these categories when present:

* **Logic errors:** incorrect conditions, incorrect return values, off-by-one errors, invalid state transitions, incorrect business logic, and incorrect error handling.
* **Async and concurrency bugs:** missing `await`, unhandled promises, race conditions, unsafe shared state, and incorrect transaction ordering.
* **Security issues:** raw SQL containing user-controlled input, missing authentication or authorization, secrets in source code, unsafe deserialization, unsafe HTML such as `dangerouslySetInnerHTML`, and equivalent injection risks.
* **Convention violations:** behavior explicitly prohibited or required by `.claude/rules/` or `.claude/standards/`.
* **Breaking changes:** incompatible API contracts, changed response shapes, removed fields, incompatible database changes, or behavior that breaks existing callers.
* **Migration safety:** destructive schema changes without a safe migration path, incompatible column changes, data-loss risks, and migrations that cannot safely run against existing data.
* **Important test gaps:** missing tests for newly introduced behavior, important failure paths, public contracts, security-sensitive behavior, or regression-prone logic.

### Skip

Do not block a review on:

* Minor formatting that Prettier or another configured formatter handles automatically.
* Naming preferences when the chosen name is clear and technically appropriate.
* Personal stylistic preferences that are not encoded in `.claude/rules/` or `.claude/standards/`.
* TODOs that already have tracked tickets or documented follow-up work.
* Purely theoretical concerns without a concrete failure mode.
* Suggestions that do not materially improve correctness, security, compatibility, or repository compliance.

The goal is to report actionable defects rather than maximize the number of review comments.

## Phase 3 — Bundling: interacting vs. independent findings

Bundle findings when they overlap or require the same fix.

For example, a missing `await` and a missing transaction wrapper in the same `refundOrder` function should be reported as one detailed finding when correcting the function requires changing both issues together.

Report independent findings as separate sequential items when they occur in separate functions or files and do not share a fix.

Use this heuristic:

> If fixing finding A changes the code that finding B depends on, the findings are interacting and should be bundled. Otherwise, keep them independent.

For interacting findings, use one detailed finding that explains all related problems and the combined fix.

For independent findings, give each finding its own severity, location, description, and recommendation.

## Phase 4 — Output format

For each finding, use exactly this structure:

```text
[severity] path/to/file.ts:line
finding: <one-sentence description>
fix: <one-sentence recommendation>
```

Severity must be one of:

* `bug`
* `security`
* `convention`
* `breaking`

For bundled findings, use one primary severity and location, then mention the related locations when necessary.

Do not report a finding without a concrete location unless the issue is repository-wide and cannot reasonably be assigned to one file.

End the review with exactly one verdict:

```text
verdict: approve
```

or:

```text
verdict: comment
```

or:

```text
verdict: request-changes
```

Use `approve` when there are no actionable findings.

Use `comment` when findings are non-blocking.

Use `request-changes` when at least one finding requires correction before acceptance.

## Examples

### Example 1 — Independent findings

**Input:**

```diff
diff --git a/src/api/orders/handler.ts b/src/api/orders/handler.ts
@@
 export async function getOrder(req, res) {
   const order = await orderRepository.find(req.params.id);

   if (!order) {
-    throw new ApiError(404, "Order not found");
+    return res.status(404).json({ status: 404 });
   }

-  return order;
+  const rows = await db.query(
+    `SELECT * FROM orders WHERE id = '${req.params.id}'`
+  );

+  return rows[0];
 }
```

**Output:**

```text
[convention] src/api/orders/handler.ts:5
finding: The missing-order path returns a `{ status: 404 }` response instead of throwing the ApiError type required by the project convention.
fix: Throw `ApiError(404, "Order not found")` so the shared error handler preserves the standard error response.

[security] src/api/orders/handler.ts:10
finding: The SQL query interpolates the request parameter directly into the query and can allow SQL injection.
fix: Use the repository layer or a parameterized query instead of interpolating `req.params.id`.

verdict: request-changes
```

These findings are independent because each requires a separate fix.

### Example 2 — Interacting findings

**Input:**

```diff
diff --git a/src/api/refunds/refundOrder.ts b/src/api/refunds/refundOrder.ts
@@
 export async function refundOrder(orderId, amount) {
-  await paymentService.refund(orderId, amount);
-  await db.transaction(async (tx) => {
-    await tx.refunds.insert({ orderId, amount });
-    await tx.orders.markRefunded(orderId);
-  });
+  paymentService.refund(orderId, amount);
+  db.refunds.insert({ orderId, amount });
+  db.orders.markRefunded(orderId);
 }
```

**Output:**

```text
[bug] src/api/refunds/refundOrder.ts:4
finding: The refund workflow has three interacting problems: `paymentService.refund` is not awaited, the refund and order writes are no longer transactional, and the database can be marked refunded before the payment operation succeeds.
fix: Await the payment refund and perform the related database writes inside the transaction with ordering that prevents the database from reporting a refund before the payment operation succeeds.

verdict: request-changes
```

These findings are bundled because the missing `await`, missing transaction wrapper, and incorrect operation ordering all affect the same refund workflow.

## Notes

* This command is proje
