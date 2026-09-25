---
description: Conventions for co-located TypeScript and TSX test files
paths:
  - "**/*.test.ts"
  - "**/*.test.tsx"
---

# Test file rules

- Co-located tests must verify the public behavior of the component or API rather than private implementation details.
- Use the project's existing test-data builders and shared fixtures when available instead of duplicating large inline test objects.
- Do not add snapshot tests for new functionality.
- Do not use `setTimeout` to make asynchronous tests pass; use the testing library's async utilities and explicit assertions instead.

## Concrete conventions

- Every test must include at least one explicit assertion using `expect(...)`.
- Asynchronous tests must use `await` with the project's testing-library async utilities instead of fixed delays.
- API tests must assert both the HTTP response status code and the relevant response body.
- Component tests should query elements by accessible role or label when available.
- Test files must use the `.test.ts` or `.test.tsx` naming convention.