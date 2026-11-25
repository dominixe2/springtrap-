# Micro Helper web/app feature parity and remote-hosting plan

## Product requirement
The browser version and native/mobile/desktop clients are two interfaces to one Micro Helper product. Feature parity is the default requirement: shared APIs, domain logic, data contracts, provider adapters, permission rules, and test coverage. Platform-specific capabilities must have equivalent fallback behavior where possible and clearly disclose unavoidable limitations.

## Hosting readiness: NOT SAFE TO PUBLISH YET
The current repository describes a local-first development service. The API currently binds to localhost in the launch guidance and the persistence layer uses a local SQLite database. Render free web services have an ephemeral filesystem and publicly expose the service. A remote deployment without authentication, account isolation, secure session handling, and durable storage could expose or lose private chat/profile/memory data. Do not deploy this API publicly until these blockers are addressed.

## Required remote-readiness gates
- Authentication and account/device isolation; reject unauthenticated access to all private endpoints.
- CSRF/origin protections for browser writes and secure session/token handling.
- No provider secrets in browser, logs, or database; provider configuration scoped securely.
- Remote persistence plan (database/storage), migration and backup/restore validation; do not rely on ephemeral SQLite filesystem.
- Rate limits, abuse controls, secure headers, and privacy-conscious logs.
- CI tests for auth, isolation, sync conflicts, restore, and destructive actions.
- Explicit deploy review and verify free-tier limits; avoid paid resources without user approval.

## Parity implementation strategy
1. Shared API and data model: chat, history, profile, memories, tasks, provider selection, files/tool permissions.
2. Local-first clients: browser/PWA and native clients keep local state, queue offline operations and synchronize idempotently.
3. Capability adapters: platform-specific functions (e.g., Windows automation or Android permissions) expose matching UI, permission prompts and fallback behavior on other platforms.
4. CI parity suite: each shared feature has API contract and browser/client tests, with offline and sync scenarios.

## Free hosting candidate
Render free web services can host a Python/FastAPI service for a preview, but sleep after inactivity and use ephemeral storage. This makes them unsuitable for the current private-data service without security and durable storage changes. A static host such as Cloudflare Pages only applies if the client can be separated from its API; it does not solve the backend/auth/data requirements.


## Local privacy regression coverage

- The mobile-browser suite now fetches the private conversation endpoint online, switches the browser context offline, and asserts the response cannot be recovered from the PWA cache.
- This is a local cache-boundary regression only. It does not establish API authentication, account isolation, or safe public hosting.
