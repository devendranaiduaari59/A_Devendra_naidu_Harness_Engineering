# Plan mode vs. direct execution — team decision guide

Choosing between plan mode (investigate and propose before changing anything) and direct execution (change code immediately) depends on the scope and uncertainty of the task.

Plan mode is useful for changes involving multiple files, architectural decisions, or multiple valid implementation approaches. Direct execution is appropriate when the change is small, well-scoped, and the expected diff is already clear.

## 1. Plan-mode example

A good plan-mode example is extracting a shared useCart(userId) hook from three components that currently duplicate cart-fetching logic.

The affected files are:

- `src/components/Cart/Cart.tsx`
- `src/components/Checkout/Checkout.tsx`
- `src/components/MiniCart/MiniCart.tsx`

This is a plan-mode task because it involves a multi-file refactor and an architectural decision about how shared cart state and API calls should be organized. There are multiple valid approaches, such as a shared hook, a context provider, or keeping the logic local.

Before making changes, Claude should inspect the three components and the related cart API and type definitions, propose the extraction approach, and identify behavior that must remain unchanged.

Planning before implementation helps prevent costly rework when a change spans multiple files and has several valid implementation approaches.

## 2. Direct-execution example

A direct-execution example is adding min: 0 validation to the quantity field in the orders schema.

The change should be limited to:

src/api/orders/handler.ts

This is a simple, well-scoped change affecting one function. The intended behavior is already clear: quantities below zero should be rejected.

Direct execution is appropriate when the author already knows what the diff should look like before invoking Claude. If the change can be described in one sentence and the resulting patch can be predicted, there is little value in spending additional context on planning.

## 3. Explore-subagent example

An Explore subagent can be used to find every place where processRefund is called.

The discovery should inspect:

- src/api/orders/refund.ts
- src/api/billing/issue.ts
- src/services/payment.ts

The purpose of using an Explore subagent is to isolate verbose discovery output from the main conversation and return a concise summary. This preserves the main conversation context while still producing a complete call-site inventory.

The Explore subagent should use the scratchpad pattern and write its working notes to:

tmp/refund-callsites.md

The scratchpad pattern allows the inventory and intermediate findings to survive the main session's context window. The main session can then consume the summarized findings instead of carrying all exploratory output.

## 4. Combined workflow — plan mode for investigation, then direct execution

Consider renaming ordersRepo.findById to ordersRepo.getById in:

src/db/orders.ts

The team convention is get* for single-row reads and find* for multi-row reads.

The investigation should happen before editing because the important question is where findById is called and whether any call sites use dynamic or constructed string lookups that a simple grep could miss.

This demonstrates combining plan mode for investigation with direct execution for implementation.

The workflow is:

1. Plan mode investigates the repository, identifies every findById call site, checks for dynamic references, and proposes the rename.
2. You approve the plan after reviewing the discovered call sites and proposed changes.
3. Direct execution applies the mechanical rename and runs the relevant tests.

Once the complete call-site list is known, the rename itself is a predictable mechanical change, so direct execution is appropriate.

## Knight-Webb principle

The curriculum's anchor-talks material includes Knight-Webb's “SWE Is Becoming Plan and Review.” The principle is relevant to this guide because planning before implementation can prevent costly rework on changes where the correct implementation is not yet clear.

## Quick reference

| Situation | Mode |
|-----------|------|
| Single function, fix is obvious, you can predict the diff | Direct execution |
| Multi-file refactor, API shape is debatable | Plan mode |
| Discovery or inventory across the codebase | Explore subagent |
| Investigation followed by a mechanical change | Plan mode → direct execution |
| Architectural decision | Plan mode, possibly with a fork to compare options |

When uncertain, use plan mode when the cost of discovering the correct approach after editing would be significant.