## Task Overview

A multi-tenant SaaS platform lets enterprise customers manage how their users receive notifications — by email, SMS, or push, and how often. Each tenant is a separate organisation; within a tenant, people manage their own preferences while administrators help manage others', and the service is built on FastAPI and PostgreSQL and is already live. It has been serving customers for a while, and several teams have now reported behaviour on the preferences endpoints that they cannot rely on — their reports are listed under Objectives. Because this is real customer data spread across many tenants, the problems need production-grade fixes, not quick patches.

## Objectives

- Make sure each person can reach only the preferences they are entitled to, and no others.
- Keep every tenant's data isolated from every other tenant's, whatever role the requester holds.
- Protect simultaneous edits to the same record so that no one's change is silently lost.
- Respond to a refused request in a way that tells the client why it was refused.
- Keep the access and concurrency rules cleanly separated from the request-handling code.

## Helpful Tips

- Get the stack running and watch a normal read-then-update of a user's preferences go through end to end before you change anything.
- Reproduce what the teams reported for yourself — try reaching preferences as different kinds of users before deciding what to change.
- Think about where a decision like "is this caller allowed to touch this record" most naturally belongs in the path a request takes.
- Think about what should happen when two people edit the same record at the same time, and what "correct" means for data people depend on.

## How to Verify

- A user asking for someone else's preferences should be turned away, whatever tenant that other person belongs to.
- An administrator should be able to act across their own tenant, but should not be able to reach into a different tenant.
- Two edits to the same record, both made from the same starting point, should end with one applied and one refused — never both silently merged or lost.
- A refused request should make clear whether it was refused because the caller was not allowed, or because the record had already changed since it was read.
- The checks under `tests/` exercise these behaviours once the stack reports it is ready.

## Changes made (security & concurrency hardening)

**Findings:** routes ignored the caller's identity; queries filtered only by `user_id` (cross-tenant reach); `PUT` ignored `version` (lost updates); errors had no machine-readable reason.

**Fixes**
- `app/services/authorization.py`: pure rules. `user` -> own record only; `admin` -> any user in own tenant; no role crosses tenants.
- Tenant comes only from the signed JWT; every SQL query filters `tenant_id`; request bodies reject unknown fields (`tenant_id`, `version`).
- Optimistic locking: `GET` returns `ETag`; `PUT` requires `If-Match`. A single atomic `UPDATE ... WHERE version = N` bumps the version, so of two simultaneous edits exactly one succeeds.
- One error envelope `{error: {code, message, hint, details}}`: 401 `AUTHENTICATION_REQUIRED`, 403 `SELF_ONLY` / `CROSS_TENANT_ACCESS`, 412 `VERSION_CONFLICT` (with `current_version`), 428 `VERSION_REQUIRED`, 422 `VALIDATION_ERROR`.
- Cross-tenant and non-existent users return the same 403, so ids in other tenants cannot be probed.

**Next steps:** token expiry (`exp`), roles from the DB instead of the token, Postgres RLS and a composite FK `(tenant_id, user_id)`, audit log.
