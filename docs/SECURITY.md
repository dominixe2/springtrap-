# Micro Helper security notes

## Hosted account data

- User-facing API routes in the hosted backend require an authenticated AppDeploy user.
- State is stored in per-user tables derived from the authenticated user ID; route handlers use the authenticated identity rather than accepting a caller-supplied owner ID.
- Realtime subscriptions are checked against the authenticated user's own `user_state` entity.
- The service worker caches only the public app shell and static assets. It deliberately skips API paths and does not cache private API responses.
- Do not put passwords, API keys or other secrets into notes or preferences.

## Web and image tools

- Web search builds a fixed DuckDuckGo HTML search URL from the query. It does not accept an arbitrary URL from the browser, reducing SSRF exposure.
- Extracted result links are restricted to HTTP(S), deduplicated and rendered as links with `noopener noreferrer`.
- Image upload routes require authentication, accept JPEG/PNG/WebP, cap each image at 6 MiB and cap generation to five references.
- AI failures are returned as visible service errors rather than fabricated successful results.

## Windows Companion

- Binds only to `127.0.0.1:8765`.
- Accepts browser POST requests only from the exact hosted app origin.
- Uses a random one-time pairing code and a random session bearer token; restarting the process invalidates both.
- Limits pairing attempts and accepts only a fixed allowlist: lock Windows, Explorer, Notepad and Calculator.
- Does not invoke a shell or accept arbitrary executable paths/arguments.
- The local bridge is not a general remote desktop. Keep the executable from a trusted build artifact and close it when it is not needed.

## Deterministic permission policy

The feature branch includes `src/micro_helper/trust_policy.py` and unit tests for exact grants, explicit-deny precedence, sensitive-data confirmation, financial/destructive confirmation and narrow optional-cookie rejection. This is a policy primitive, not proof that every hosted or desktop tool already calls it. Do not treat the policy as enforced end to end until each action adapter is wired to it and integration tests cover the full request path.

## Residual risks and limits

- The Android wrapper loads the hosted origin, so cloud data and AI depend on network and the AppDeploy account.
- The current APK is debug-signed. Do not publish it as a Play Store release. A production signing key and a protected release-signing workflow are still required for store distribution.
- The Windows EXE is not code-signed; Windows SmartScreen may display a warning.
- The browser-local fallback uses browser storage and is not encrypted by this app. Treat device access and browser profile security accordingly.
- A successful CI build proves packaging and static checks, not behavior on the user's physical phone or notebook.
