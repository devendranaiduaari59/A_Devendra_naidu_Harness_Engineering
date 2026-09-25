---
description: API handler conventions for request validation, errors, and repository boundaries
paths:
  - "src/api/**/*"
---

# API handler rules

- API handlers must validate request input before calling a repository or service function.
- API handlers must use the project's standard API error type for validation and domain failures.
- API handlers must return the appropriate HTTP status code for success and error responses.
- API handlers must not access the database directly; database operations must go through the repository or service layer.
- API handlers should remain focused on HTTP concerns: parse the request, call the service, and map the result to the HTTP response.

## Concrete conventions

- Return `400 Bad Request` when request validation fails.
- Return `404 Not Found` when a requested resource does not exist.
- Return `500 Internal Server Error` only for unexpected failures.
- A successful `POST` that creates a resource must return `201 Created`.
- API handlers must call a service or repository function instead of importing a database client or executing SQL directly.